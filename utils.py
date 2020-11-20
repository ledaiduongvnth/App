from config import *
import os

# region ROI
# ==============================================================================
def get_null_roi():
    return (0, 0), (1, 1)


def not_null_roi(tl, br):
    return (br[0] - tl[0]) > 1 and (br[1] - tl[1]) > 1


def get_default_roi(display_side, img_w = SCREEN_W, img_h = SCREEN_H, roi_translation=(0,0), l_roi_w_ratio=0.5):
    offset_w = img_w / 10
    offset_h = img_h / 10
    dy = int(roi_translation[1] * img_h)
    dx = int(roi_translation[0] * img_w)

    if display_side == "R":
        roi_w = int((img_w - offset_w * 2) * l_roi_w_ratio) # display right is person's left
        roi_tl = (offset_w + dx, offset_h + dy)
        roi_br = (offset_w + roi_w + dx, img_h - offset_h * 2 + dy)
        if l_roi_w_ratio < 0.4:
            return get_null_roi()
    if display_side == "L":
        roi_w = int((img_w - offset_w * 2) * (1 - l_roi_w_ratio))
        roi_tl = (img_w - offset_w - roi_w + dx, offset_h + dy)
        roi_br = (img_w - offset_w + dx, img_h - offset_h * 2 + dy)
        if (1.0 - l_roi_w_ratio) < 0.4:
            return get_null_roi()

    return roi_tl, roi_br
# ==============================================================================
# endregion

# region Handle exceptions
# ==============================================================================
def handle_cam_disconnected(cam_service_url, cap, try_count):
    logging.error("Fail to grab image")
    try_count += 1
    if try_count > 30:
        cap = cv2.VideoCapture(cam_service_url)
        try_count = 0
        logging.error('Reconnected.')
    time.sleep(0.033)
    return try_count, cap
# ------------------------------------------------------------------------------
def handle_exception(ex):
    logging.exception(ex)
# ==============================================================================
# endregion

# region Utils
# ==============================================================================
def limit_fps_by_sleep(max_fps, frame_start_time):
    sleep_time = 1.0 / max_fps - (time.time() - frame_start_time)
    if (sleep_time > 0):
        time.sleep(sleep_time)
# ------------------------------------------------------------------------------
def ping(hostname):
    response = os.system("ping -c 1 " + hostname)
    return response == 0 # 0: is up
# ==============================================================================
# endregion


def get_config(key, default=None):
    if key in PI_CF:
        return PI_CF[key]
    else:
        return default


from logging.handlers import RotatingFileHandler
def get_logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)

    if not os.path.exists('./log'):
        os.mkdir('./log')

    hdlr = RotatingFileHandler(
        './log/{}_{}.log'.format(logging._levelNames[level], name),
        mode='a', maxBytes=5*1024*1024, backupCount=2, encoding=None, delay=0)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)

    logger.addHandler(hdlr)
    logger.setLevel(level)

    return logger