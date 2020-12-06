#!/usr/bin python
from config import *
from flask import *

import optparse
from threading import Thread
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
hnd = DisplayRequestHandle()
logo = cv2.imread("/home/pi/Desktop/App/images/Logo_Viettel.svg.png", cv2.IMREAD_COLOR)

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
        message=request.values['message']
        lane_id=request.values['lane_id']
        is_landscape=request.values.get('is_landscape', None)
        status=request.values.get('status', None)


        try:
            is_landscape = int(is_landscape)
        except:
            is_landscape = 1

        logging.info('request={}, laneid={}, is_landscape={}'.format(request, lane_id, is_landscape))
        if (message != 'Unknown'):
            title=request.values.get('title', '')
            encoded_profile_image=request.values['profile_image']
            encoded_license_plate_image=request.values['license_plate_image']

            hnd.add(Profile(encoded_profile_image, encoded_license_plate_image, status, lane_id, message, title, is_landscape))
    except Exception as ex:
        ut.handle_exception(ex)

    return jsonify(success = True)


def make_screen_img(left_img, right_img):
    rgba = np.zeros((SCREEN_H, SCREEN_W, 4), np.uint8)
    tl, br = ut.get_default_roi('R', rgba.shape[1], rgba.shape[0], roi_translation, roi_l_w_ratio)
    if ut.not_null_roi(tl, br):
        cv2.rectangle(rgba, tl, br, (255, 255, 0, OPACITY), 3)
    tl, br = ut.get_default_roi('L', rgba.shape[1], rgba.shape[0], roi_translation, roi_l_w_ratio)
    if ut.not_null_roi(tl, br):
        cv2.rectangle(rgba, tl, br, (255, 255, 0, OPACITY), 3)

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

                if l is not None:
                    height, width, channels = l.shape
                    resized_logo_image = cv2.resize(logo, (width / 5, height / 10), interpolation=cv2.INTER_AREA)
                    l[0 + 40:height / 10 + 40, width - width / 5: width] = resized_logo_image

                if r is not None:
                    height, width, channels = r.shape
                    resized_logo_image = cv2.resize(logo, (width / 5, height / 10), interpolation=cv2.INTER_AREA)
                    r[0 + 40:height / 10 + 40, width - width / 5: width] = resized_logo_image



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

    start_tornado(app, 5000)
