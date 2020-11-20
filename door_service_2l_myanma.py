# -*- coding: utf-8 -*-


from flask import *
import time
import serial
import logging
from threading import Thread
import optparse
import requests

cmd_open1="\xA0\x01\x01\xA2"
cmd_close1="\xA0\x01\x00\xA1"

cmd_open2="\xA0\x02\x01\xA3"
cmd_close2="\xA0\x02\x00\xA2"

import tornado.httpserver
import tornado.ioloop
import tornado.wsgi

logger = logging.getLogger(__name__)

app = Flask(__name__)

def start_tornado(app, port):
    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    logging.info("Starting Tornado server on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()
    logging.info("Tornado server started on port {}".format(port))

@app.route('/door_service', methods=['GET'])
def door_service():
    global ser, cmd_old, t0_old, cmd_open1_recv, cmd_open1_recv_time, cmd_open2_recv, cmd_open2_recv_time
    try:
        # We will save the file to disk for possible data collection.
        code = str(request.args.get("code", ""))
        cmd = "Y"
        if code == "H" or code == "N": # send to backup door service
            cmd = "Y"
            if has_backup:
                if code == "H":
                    res = requests.get(bk_door_service_url, params="code=G", timeout=1)
                if code == "N":
                    res = requests.get(bk_door_service_url, params="code=K", timeout=1)

        if code == "G" or code == "K":
            cmd = code

        if cmd == "G" and cmd != cmd_old:
            ser.write(cmd_open1)
            #print("cmd_open1")
            cmd_open1_recv = True
            cmd_open1_recv_time = time.time()


        if cmd == "K" and cmd != cmd_old:
            ser.write(cmd_open2)
            #print("cmd_open2")
            cmd_open2_recv = True
            cmd_open2_recv_time = time.time()

        if cmd_old != cmd:
            t0_old = time.time()
            cmd_old = cmd

            print(cmd)


    except Exception as err:
        logger.info('Error: %s', err)
        return jsonify(success=False)
    return jsonify(success=True)

def runTimerThread():
    global ser, t0_old, cmd_old, cmd_open1_recv, cmd_open1_recv_time, cmd_open2_recv, cmd_open2_recv_time
    while 1:
        try:
            t = time.time()

            if cmd_open1_recv and t > cmd_open1_recv_time + duration:
                ser.write(cmd_close1)
                #print("cmd_close1")
                cmd_open1_recv = False

            if cmd_open2_recv and t > cmd_open2_recv_time + duration:
                ser.write(cmd_close2)
                #print("cmd_close2")
                cmd_open2_recv = False

            if cmd_old != "X" and t - t0_old >= 0:
                cmd_old = "X"

        except Exception as err:
            print(err)

        time.sleep(0.05)


if __name__ == '__main__':

    parser = optparse.OptionParser()

    parser.add_option(
        '-b', '--bk_ip',
        help="backup IP",
        type='string', default='')

    opts, args = parser.parse_args()

    backup_ip = opts.bk_ip

    bk_door_service_url = ""
    has_backup = False

    if backup_ip != "":
        has_backup = True
        bk_door_service_url = "http://" + backup_ip + ":8081/door_service"

    logging.info("Begin")
    try:
        print("Init Door Service. Detect device type.")
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
        logger.error("Door controller not found. Cannot Open Device: %s", err)
        exit(-1)

    cmd_open1_recv = False
    cmd_open2_recv = False
    cmd_open1_recv_time = 0
    cmd_open2_recv_time = 0

    t0_old = time.time()

    cmd_old = "X"

    duration = 1 # duration in seconds

    Thread(target=runTimerThread).start()

    start_tornado(app, 8081)



