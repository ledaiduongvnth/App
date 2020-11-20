# -*- coding: utf-8 -*-


from flask import *
import time
import serial
import logging
import tornado.httpserver
import tornado.ioloop
import tornado.wsgi
from threading import Thread

cmd_open1="\xA0\x01\x01\xA2"
cmd_close1="\xA0\x01\x00\xA1"

cmd_open2="\xA0\x02\x01\xA3"
cmd_close2="\xA0\x02\x00\xA2"


logger = logging.getLogger(__name__)

app = Flask(__name__)

def start_tornado(app, port):
    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    logging.info("Starting Tornado server on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()
    logging.info("Tornado server started on port {}".format(port))

@app.route('/alarm_service', methods=['GET'])
def door_service():
    global ser, cmd_open1_recv, cmd_open1_recv_time, cmd_open2_recv, cmd_open2_recv_time
    try:
        # We will save the file to disk for possible data collection.

        code = str(request.args.get("code",""))

        if code == "A":
            ser.write(cmd_open1)
            cmd_open1_recv = True
            cmd_open1_recv_time = time.time()

        if code == "a":
            ser.write(cmd_close1)

        if code == "B":
            ser.write(cmd_open2)
            cmd_open2_recv = True
            cmd_open2_recv_time = time.time()

        if code == "b":
            ser.write(cmd_close2)


    except Exception as err:
        logger.info('Error: %s', err)
        return jsonify(success=False)
    return jsonify(success=True)

def runTimerThread():
    global ser, cmd_open1_recv, cmd_open1_recv_time, cmd_open2_recv, cmd_open2_recv_time
    while 1:
        try:
            t = time.time()

            if cmd_open1_recv and t > cmd_open1_recv_time + duration:
                ser.write(cmd_close1)
                cmd_open1_recv = False

            if cmd_open2_recv and t > cmd_open2_recv_time + duration:
                ser.write(cmd_close2)
                cmd_open2_recv = False

        except Exception as err:
            print(err)

        time.sleep(0.01)


if __name__ == '__main__':
    logging.info("Begin")
    try:
        print("Init Alarm Service. Detect device type.")
        initialized = False

        try:
            ser = serial.Serial("/dev/ttyACM0", 9600)
            initialized = True
        except:
            pass

        try:
            ser = serial.Serial("/dev/ttyUSB0", 9600)
            initialized = True
        except:
            pass

        if initialized is False:
            raise IOError("Cannot detect device type.")

    except Exception as err:
        logger.error("Alarm controller not found. Cannot Open Device: %s", err)
        exit(-1)

    cmd_open1_recv = False
    cmd_open2_recv = False
    cmd_open1_recv_time = 0
    cmd_open2_recv_time = 0

    duration = 2 # alarm duration in seconds

    Thread(target=runTimerThread).start()

    start_tornado(app, 8081)



