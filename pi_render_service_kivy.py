#!/usr/bin/env python

from flask import *

import optparse
from threading import Thread
from Queue import Queue
import Tkinter

from draw import *
import utils as ut

from multiprocessing.connection import Client


# root = Tkinter.Tk()
screen_w = 1280  # root.winfo_screenwidth()
screen_h = 800  # root.winfo_screenheight()
ip = '10.61.212.16'
address = (ip, 6000)

print("Screen w ,h: %d, %d" % (screen_w, screen_h))

CAM_URL_TEMPLATES = [
    'rtsp://admin:abcd1234@{}{}:554/Streaming/Channels/2',
    'rtsp://admin:abcd1234@{}{}:554/cam/realmonitor?channel=1&subtype=1',
]

app = Flask(__name__)
q = Queue(1)
hnd = DisplayRequestHandle()


@app.route('/display', methods=['POST', 'GET'])
def display():
    global hnd
    try:
        id = request.values['id']
        lane_id = request.values['lane_id']
        logging.info('request={}, laneid={}, id={}'.format(request, lane_id, id))
        if (id != 'Unknown'):
            title = request.values.get('title', '')
            encoded_img_filestream = request.files['profile_image']
            hnd.add(Profile(encoded_img_filestream, lane_id, id, title))
    except Exception as ex:
        ut.handle_exception(ex)

    return jsonify(success=True)


def runCamGrabberThread():
    global q, finished
    cap = cv2.VideoCapture(cam_service_url)
    cnt = 0
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
                img = cv2.resize(img, (screen_w, screen_h))
                hnd.render(img)
                cv2.imshow(' ', img)
            else:
                time.sleep(0.01)
            key = cv2.waitKey(1)
            if key % 256 == 27:  # press esc
                finished = True
        except Exception as ex:
            ut.handle_exception(ex)

        ut.limit_fps_by_sleep(MAX_FPS, t0)

    cv2.destroyAllWindows()


def make_display_img(left_img, right_img):
    bgra = np.zeros((screen_h, screen_w, 4), np.uint8)
    tl, br = ut.get_default_roi('R', bgra.shape[1], bgra.shape[0])
    cv2.rectangle(bgra, tl, br, (0, 255, 0, OPACITY), 3)
    tl, br = ut.get_default_roi('L', bgra.shape[1], bgra.shape[0])
    cv2.rectangle(bgra, tl, br, (0, 255, 0, OPACITY), 3)

    if left_img is not None:
        bgra[:, 0:screen_w / 2, 0:3] = left_img
        bgra[:, 0:screen_w / 2, 3] = OPACITY

    if right_img is not None:
        bgra[:, screen_w / 2:screen_w, 0:3] = right_img
        bgra[:, screen_w / 2:screen_w, 3] = OPACITY

    return bgra


def runImageRendererThread(dir):
    first_run = True
    cnt = 0
    conn = Client(address, authkey='secret password')
    print("Connected")

    while True:
        t0 = time.time()
        try:
            if hnd.check_update() or first_run:
                first_run = False
                img = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
                l, r = hnd.render(img)

                try:
                    bgra = make_display_img(l, r)
                    if bgra is not None:
                        cnt += 1
                        print('time: {}: update screen image, cnt: {}'.format(t0, cnt))
                        conn.send(bgra)


                except Exception as ex:
                    ut.handle_exception(ex)

            if flg_debug and img is not None:
                cv2.imshow('', img)
                cv2.waitKey(1)

        except Exception as ex:
            ut.handle_exception(ex)



if __name__ == '__main__':

    parser = optparse.OptionParser()

    parser.add_option('--debug', type='int', default=0)
    parser.add_option('--render_image', help='render to image file not screen', type='int', default=0)
    parser.add_option('--render_dir', help='abs path to directory of rendered image', type='string',
                      default="/home/pi/Desktop/App")

    opts, args = parser.parse_args()

    flg_debug = bool(opts.debug)
    render_image = bool(opts.render_image)

    my_cf = PI_CF_TABLE[MY_IP_SUFFIX]
    cam_type = my_cf['cam_type']
    cam_service_url = CAM_URL_TEMPLATES[cam_type].format(BASE_IP, my_cf['cam_ip'])

    if flg_debug:
        cam_service_url = 0

    finished = False

    if render_image:
        Thread(target=runImageRendererThread, args=(opts.render_dir,)).start()
    else:
        Thread(target=runCamGrabberThread).start()
        Thread(target=runScreenRendererThread).start()

    app.run(host='0.0.0.0', port=5000)
