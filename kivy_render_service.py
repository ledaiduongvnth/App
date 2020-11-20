
from kivy.app import App

from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.clock import Clock

import os

import cv2
from threading import Thread

from multiprocessing.connection import Listener

screen_h = 800
screen_w = 1280
ip = '10.61.212.16'
address = (ip, 6000)

def runImgGrabberThread():
    global buf, has_update, finished

    listener = Listener(address, authkey='secret password')
    conn = listener.accept()
    print 'connection accepted from', listener.last_accepted

    while not finished:
        try:
            msg = conn.recv()
            if type(msg) == str:
                if msg == 'close':
                    conn.close()
                    finished = True
                    has_update = True
            else:
                cv_img = msg
                bgra = cv_img.copy()
                rgba = bgra[:,:,[2,1,0,3]]
                buf1 = cv2.flip(rgba, 0)
                buf = buf1.tostring()
                has_update = True

        except:
            print("Error on reception Thread")
            has_update = True
            finished = True
            pass

    listener.close()

class KivyPNGDisplayer(Image):
    cnt = 0
    def __init__(self, fps, **kwargs):
        super(KivyPNGDisplayer, self).__init__(**kwargs)
        dt = 1.0 / fps
        Clock.schedule_interval(self.update, dt)

    def update(self, dt):
        global buf, has_update
        # display image from the texture
        if has_update:
            has_update = False
            image_texture = Texture.create(size=(screen_w, screen_h), colorfmt='rgba')
            image_texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
            self.texture = image_texture
            self.cnt += 1
            print("Update frame, cnt %d" % self.cnt)


class KivyRenderApp(App):
    def build(self):
        self.my_camera = KivyPNGDisplayer(fps=30)
        return self.my_camera

    def on_stop(self):
        global finished

        finished = True
        print("exit")


if __name__ == '__main__':

    finished = False
    has_update = False
    filename = ""
    os.environ["KIVY_BCM_DISPMANX_LAYER"] = "2"
    layer = int(os.environ.get("KIVY_BCM_DISPMANX_LAYER", "0"))
    print("Kivy layer: %d" % layer)

    buf = None

    Thread(target=runImgGrabberThread).start()

    Window.clearcolor = (0, 0, 0, 0)

    KivyRenderApp().run()