import base64

from config import *
import utils as ut

import cv2
import numpy as np
import time
from PIL import Image, ImageFont, ImageDraw
import threading

g_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
g_font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)

def draw_unicode(img, unicode_text, origin, max_w=500, small_font=False):
    if small_font is True:
        font = g_font_small
    else:
        font = g_font

    left = max(0, origin[0])
    top = max(0, origin[1])
    bottom = min(img.shape[0], origin[1] + 80)
    right = min(img.shape[1], left + max_w)
    crop = img[top:bottom, left:right, :]

    pil_im = Image.fromarray(crop)  # opencv Mat -> PIL image
    draw = ImageDraw.Draw(pil_im)

    draw.text((0, 0), unicode_text, (255, 255, 255), font)
    crop = np.array(pil_im)  # PIL image -> opencv Mat
    img[top:bottom, left:right, :] = crop

def get_profile_cell(w, h, profile, border_thickness = 3, bg_color=COLOR_OK):
    rs = np.ones((h, w, 3), np.uint8) * 255
    # set aside 3 pixel outermost border
    rs[border_thickness:h-border_thickness,border_thickness:w-border_thickness,:] = bg_color

    profile_size = min(w, h) * 8 / 10
    offset_x = (w - profile_size) / 2

    if profile.title:
        offset_y = (h - profile_size) / 2 - 60
    else:
        offset_y = (h - profile_size) / 2

    offset_y = max(border_thickness, offset_y)
    offset_x = max(border_thickness, offset_x)

    # make 3 pixel profile picture border
    rs[
    offset_y-border_thickness:(offset_y+profile_size)+border_thickness,
    offset_x-border_thickness:(offset_x + profile_size)+3, :] = (255, 255, 255)

    if profile.title:
        draw_unicode(rs, profile.id, (offset_x, offset_y + profile_size + 10), max_w=500)
        draw_unicode(rs, profile.title, (offset_x, offset_y + profile_size + 65), max_w=500, small_font=True)

    #print profile.img.shape
    #print rs.shape, offset_x, offset_y, profile_size
    rs[offset_y:(offset_y+profile_size), offset_x:(offset_x + profile_size), :] = \
        cv2.resize(profile.img, (profile_size, profile_size))

    return rs

def draw_profile(img, position_code, profile):
    w = img.shape[1]
    h = img.shape[0]

    bg_color = COLOR_OK
    if profile.id == "STOP":
        bg_color = COLOR_EXCEPTION

    def get_cell(w, h):
        return get_profile_cell(w, h, profile, bg_color=bg_color)

    if (position_code == 'l'):
        img[0:h,0:(w/2),:] = get_cell(w / 2, h)
    if (position_code == 'r'):
        img[0:h,(w/2):w,:] = get_cell(w - w / 2, h)
    if (position_code == 'tr'):
        img[0:(h/2),(w/2):w,:] = get_cell(w - w / 2, h / 2)
    if (position_code == 'br'):
        img[(h/2):h,(w/2):w,:] = get_cell(w - w / 2, h - h / 2)
    if (position_code == 'tl'):
        img[0:(h/2),0:(w/2),:] = get_cell(w / 2, h / 2)
    if (position_code == 'bl'):
        img[(h/2):h,0:(w/2),:] = get_cell(w / 2, h - h / 2)

def draw_profiles(img, requests):
    llane = [r.profile for r in requests if r.profile.lane_id == 'L']
    rlane = [r.profile for r in requests if r.profile.lane_id == 'R']

    # display only 2 oldest profile requests max -> 2 closest people
    if (rlane != None):
        rlane.sort(key=lambda x: x.id)
        if (len(rlane) == 1):
            draw_profile(img, 'r', rlane[0])
        if (len(rlane) > 1):
            draw_profile(img, 'tr', rlane[0])
            draw_profile(img, 'br', rlane[1])

    if (llane != None):
        llane.sort(key=lambda x: x.id)
        if (len(llane) == 1):
            draw_profile(img, 'l', llane[0])
        if (len(llane) > 1):
            draw_profile(img, 'tl', llane[0])
            draw_profile(img, 'bl', llane[1])

class Profile(object):
    def __init__(self, encoded_profile_image, encoded_license_plate_image, lane_id, id, title = '', is_landscape=1):
        self.is_landscape = is_landscape
        self.title = title
        self.lane_id = lane_id
        self.encoded_profile_image = encoded_profile_image
        self.encoded_license_plate_image = encoded_license_plate_image
        self.img = None
        self.id = id

    def decode(self):
        if self.encoded_profile_image.startswith('data'):
            encoded_data = self.encoded_profile_image.split(',')[1]
        else:
            encoded_data = self.encoded_profile_image
        np_array = np.fromstring(base64.b64decode(encoded_data), np.uint8)
        profile_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if self.encoded_license_plate_image.startswith('data'):
            encoded_data = self.encoded_license_plate_image.split(',')[1]
        else:
            encoded_data = self.encoded_license_plate_image
        np_array = np.fromstring(base64.b64decode(encoded_data), np.uint8)
        license_plate_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        height, width, channels = profile_image.shape
        resized_license_plate_image = cv2.resize(license_plate_image, (width/3, height/3), interpolation=cv2.INTER_AREA)
        profile_image[0:height/3, 0:width/3] = resized_license_plate_image
        self.img = profile_image
        if self.is_landscape != 1:
            self.img = cv2.transpose(self.img)

class DisplayRequest(object):
    def __init__(self, profile):
        self.profile = profile
        self.start_time = time.time()

class DisplayRequestHandle(object):
    """
    ttl: time to live of profile picture after last display request 
    """
    def __init__(self):
        self.requests = []
        self.last_render_content_hash = ''
        self.lock = threading.Lock()

    def add(self, profile):
        existed = False
        t0 = time.time()

        #print('add get lock')
        self.lock.acquire()
        for r in self.requests:
            if r.profile.id == profile.id and r.profile.lane_id == profile.lane_id:
                r.start_time = t0
                existed = True
        self.lock.release()
        #print('release lock')

        if not existed:
            profile.decode()
            request = DisplayRequest(profile)
            self.lock.acquire()
            self.requests.append(request)
            self.lock.release()

    def _get_content_hash(self):
        return ' '.join([r.profile.id for r in self.requests])

    def check_update(self):
        now = time.time()

        # remove timeout requests
        #print('check update get lock')
        self.lock.acquire()
        self.requests = [r for r in self.requests if now - r.start_time < PROFILE_DISPLAY_MAX_TTL]
        self.requests.sort(key=lambda x: x.profile.id)
        self.lock.release()
        #print('check update release lock')

        hash = self._get_content_hash()
        if hash != self.last_render_content_hash:
            self.last_render_content_hash = hash
            return True
        else:
            return False

    @property
    def left_profiles(self):
        return [r.profile for r in self.requests if r.profile.lane_id == 'L']

    @property
    def right_profiles(self):
        return [r.profile for r in self.requests if r.profile.lane_id == 'R']

    @property
    def _has_left_content(self):
        return len(self.left_profiles) > 0

    @property
    def _has_right_content(self):
        return len(self.right_profiles) > 0

    def render(self, img):
        self.check_update()

        # divide the image into left and right parts
        w = img.shape[1]
        limg = None
        if self._has_left_content:
            limg = img[:,0:w/2,:]
        rimg = None
        if self._has_right_content:
            rimg = img[:,w/2:w,:]

        tl, br = ut.get_default_roi('R', img.shape[1], img.shape[0])
        cv2.rectangle(img, tl, br, (0, 255, 0), 3)
        tl, br = ut.get_default_roi('L', img.shape[1], img.shape[0])
        cv2.rectangle(img, tl, br, (0, 255, 0), 3)

        draw_profiles(img, self.requests)

        return limg, rimg


    def render_left_right(self, img):
        # divide the image into left and right parts
        w = img.shape[1]
        limg = None
        if self._has_left_content:
            limg = img[:,0:w/2,:]
        rimg = None
        if self._has_right_content:
            rimg = img[:,w/2:w,:]

        draw_profiles(img, self.requests)

        return limg, rimg
