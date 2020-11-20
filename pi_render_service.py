#!/usr/bin python
from config import *
from flask import *

import optparse
from threading import Thread
from Queue import Queue

from draw import *
import utils as ut
import os

import tornado.httpserver
import tornado.ioloop
import tornado.wsgi

logger = ut.get_logger("pi_render_service")

CAM_URL_TEMPLATES = [
    'rtsp://admin:abcd1234@{}{}:554/Streaming/Channels/2',
    'rtsp://admin:abcd1234@{}{}:554/cam/realmonitor?channel=1&subtype=1',
]

app = Flask(__name__)
q = Queue(1)
hnd = DisplayRequestHandle()

def start_tornado(app, port):
    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    logging.info("Starting Tornado server on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()
    logging.info("Tornado server started on port {}".format(port))


@app.route('/display', methods=['POST', 'GET'])
def display():
    global hnd
    try:
        id=request.values['id']
        lane_id=request.values['lane_id']
        is_landscape=request.values.get('is_landscape', None)

        try:
            is_landscape = int(is_landscape)
        except:
            is_landscape = 1

        logging.info('request={}, laneid={}, id={}, is_landscape={}'.format(request, lane_id, id, is_landscape))
        if (id != 'Unknown'):
            title=request.values.get('title', '')
            encoded_img_filestream=request.files['profile_image']
            hnd.add(Profile(encoded_img_filestream, lane_id, id, title, is_landscape))
    except Exception as ex:
        ut.handle_exception(ex)

    return jsonify(success = True)


def runCamGrabberThread():
    global q, finished
    cap = cv2.VideoCapture(cam_service_url)
    cnt=0
    while finished is False:
        t0 = time.time()
        try:
            ret, cv_img = cap.read()
            if cv_img is not None:
                if not q.full():
                    q.put(cv_img.copy())
            else:
                cnt, cap = ut.handle_cam_disconnected(cam_service_url, cap, cnt)
        except Exception as ex:
            ut.handle_exception(ex)

        ut.limit_fps_by_sleep(25, t0)

    cap.release()
        

def runScreenRendererThread():
    global q, finished
    cv2.namedWindow(' ', cv2.WINDOW_AUTOSIZE)
    while finished is False:
        t0 = time.time()
        try:
            if not q.empty():
                img = q.get()
                img = cv2.resize(img, (SCREEN_W, SCREEN_H))
                hnd.render(img)
                cv2.imshow(' ', img)
            else:
                time.sleep(0.01)
            key = cv2.waitKey(1)
            if key % 256 == 27: # press esc
                finished = True
        except Exception as ex:
            ut.handle_exception(ex)

        ut.limit_fps_by_sleep(MAX_FPS, t0)

    cv2.destroyAllWindows()


def make_screen_img(left_img, right_img):
    rgba = np.zeros((SCREEN_H, SCREEN_W, 4), np.uint8)
    tl, br = ut.get_default_roi('R', rgba.shape[1], rgba.shape[0], roi_translation, roi_l_w_ratio)
    if ut.not_null_roi(tl, br):
        cv2.rectangle(rgba, tl, br, (0, 255, 0, OPACITY), 3)
    tl, br = ut.get_default_roi('L', rgba.shape[1], rgba.shape[0], roi_translation, roi_l_w_ratio)
    if ut.not_null_roi(tl, br):
        cv2.rectangle(rgba, tl, br, (0, 255, 0, OPACITY), 3)

    if left_img is not None:
        rgba[:, 0:SCREEN_W / 2, 0:3] = left_img
        rgba[:, 0:SCREEN_W / 2, 3] = OPACITY

    if right_img is not None:
        rgba[:, SCREEN_W / 2:SCREEN_W, 0:3] = right_img
        rgba[:, SCREEN_W / 2:SCREEN_W, 3] = OPACITY

    return rgba


def runImageRendererThread():
    first_run = True
    write_error = False
    cnt = 0
    while True:
        t0 = time.time()
        try:
            if hnd.check_update() or first_run or write_error:
                first_run = False
                img = np.zeros((SCREEN_H, SCREEN_W, 3), dtype=np.uint8)
                l, r = hnd.render_left_right(img)

                logger.info('time: {}: update screen image'.format(t0))

                try:
                    bgra = make_screen_img(l, r)
                    if bgra is not None:
                        cv2.imwrite(screen_file, bgra)
                        cnt = cnt + 1
                        write_error = False

                except Exception as ex:
                    ut.handle_exception(ex)
                    logger.info('notify file Not OK')
                    write_error = True

                if not write_error:
                    # notify the png display service
                    with open(screen_file + '.screen.log', 'w') as f:
                        f.write('OK\n')
                        logger.info('notify screen OK, cnt %d' % cnt)

            if flg_debug:
                if (os.path.exists(screen_file)):
                    screen = cv2.imread(screen_file)
                    cv2.imshow('', screen)
                    cv2.waitKey(1)

        except Exception as ex:
            ut.handle_exception(ex)

        ut.limit_fps_by_sleep(MAX_FPS, t0)


def runMessageThread():
    startup_screen = make_screen_img(None, None)
    has_error = False
    has_error_old = has_error
    no_door = False
    no_server = False
    while True:
        t0 = time.time()
        screen_update = False
        try:
            if ut.get_config('door') is not None:
                no_door = not ut.ping(door_ip)

            if ut.get_config('server') is not None:
                no_server = not ut.ping(server_ip)

            no_cam = not ut.ping(cam_ip)
            screen = None

            if no_door or no_cam or no_server or len(NOTICE_LINES) > 0:
                screen = np.zeros((SCREEN_H, SCREEN_W, 4), dtype=np.uint8)
                screen[:, :, 3] = 127  # make error screen semi-visible

            if no_door or no_cam or no_server:
                has_error = True
                draw_unicode(screen, COMMON_ERROR_HANDLING, (10, 10), max_w=1200)
                draw_unicode(screen, COMMON_ERROR, (10, 100), max_w=1200)
                if no_cam:
                    draw_unicode(screen, CONNECTION_LOSS_CAM, (10, 160), max_w=1200)
                    screen_update = True

                if no_door:
                    draw_unicode(screen, CONNECTION_LOSS_DOOR, (10, 220), max_w=1200)
                    screen_update = True

                if no_server:
                    draw_unicode(screen, CONNECTION_LOSS_SERVER, (10, 280), max_w=1200)
                    screen_update = True
            else:
                has_error = False
                # Detect first back from error then show startup screen
                if has_error_old and not has_error:
                    screen = startup_screen
                    screen_update = True

                for i in range(len(NOTICE_LINES)):
                    if NOTICE_LINES[i]:
                        draw_unicode(screen, NOTICE_LINES[i], (10, 360 + i * 40), max_w=1200, small_font=True)
                        screen_update = True

            if screen_update:
                try:
                    cv2.imwrite(screen_file, screen)
                    write_error = False
                except Exception as ex:
                    ut.handle_exception(ex)
                    write_error = True

                if not write_error:
                    # notify the png display service
                    try:
                        with open(screen_file + '.hk.log', 'w') as f:
                            f.write('OK\n')
                            logger.info('notify file health check OK')
                    except Exception as ex:
                        ut.handle_exception(ex)

            has_error_old = has_error

        except Exception as ex:
            ut.handle_exception(ex)

        ut.limit_fps_by_sleep(0.1, t0)


if __name__ == '__main__':

    parser = optparse.OptionParser()

    parser.add_option('--debug', type='int', default=0)
    parser.add_option('--render_image', help='render to image file not screen', type='int', default=0)
    parser.add_option('--render_image_file', help='abs path to rendered image', type='string',
                      default="/home/pi/Desktop/App/images/screen.png")

    opts, args = parser.parse_args()

    flg_debug = bool(opts.debug)
    render_image = bool(opts.render_image)
    render_dir = os.path.dirname(opts.render_image_file)
    screen_file = opts.render_image_file

    cam_type = ut.get_config('cam_type', CAM_HK)
    cam_service_url = CAM_URL_TEMPLATES[cam_type].format(BASE_IP, ut.get_config('cam_ip'))

    roi_translation = ut.get_config('roi_translation', (0, 0))
    roi_l_w_ratio = ut.get_config('roi_l_w_ratio', 0.5)

    cam_ip = '{}{}'.format(BASE_IP, ut.get_config('cam_ip'))
    door_ip = '{}{}'.format(BASE_IP, ut.get_config('door'))
    server_ip = '{}{}'.format(BASE_IP, ut.get_config('server'))

    if flg_debug:
        cam_service_url = 0

    finished = False

    if render_image:
        Thread(target=runImageRendererThread).start()
    else:
        Thread(target=runCamGrabberThread).start()
        Thread(target=runScreenRendererThread).start()

    Thread(target=runMessageThread).start()

    start_tornado(app, 5000)
