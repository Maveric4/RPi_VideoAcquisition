# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import cv2
import copy
import numpy as np
import time
from PIL import Image
from datetime import datetime
from glob import glob
from time import sleep
import argparse
import os

## Parser handling
parser = argparse.ArgumentParser(description='Parsing arguments for recording video ')
parser.add_argument('--res', default='(640,400)', help='Type resolution')
parser.add_argument('--framerate', default='25', help='Type framerate')
parser.add_argument('--time', default='60', help='Type time of recording in minutes')
parser.add_argument('--verbose', default='0', help='Type 1 to enable verbose mode')
args = parser.parse_args()

## Page container
PAGE="""\
<html>
<head>
<title>Rpi Cam 1</title>
</head>
<body>
<center><h1>Raspberry Pi - MIR watching - Cam 1</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

# Time of recording and others
REC_TIME = int(args.time) * 60 
REC_FOLDER = './out'
REC_NAME = 'video.h264'
NBR_OF_RECORDINGS = 24
rec_continue = True

## Global variables
RES = tuple(map(int, args.res.replace('(', '').replace(')', '').split(',')))
FPS = int(args.framerate)
rec_start_time = -1
start_time = -1
webserver = -1
output = -1

fourcc = cv2.VideoWriter_fourcc(*'XVID')
#out = cv2.VideoWriter('output.avi', fourcc, 20, (640,480))

## File recording functions
def mkdir_if_not_exists(folder_path):
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
        print_msg("Created folder " + folder_path)

#def record_video(rec_time, rec_folder, rec_name):
#    mkdir_if_not_exists(rec_folder)
#    camera.start_recording(os.path.join(rec_folder, rec_name))
#    sleep(rec_time)
#    camera.stop_recording()


def del_last_hour_rec(rec_folder):
    vid_names = glob(os.path.join(rec_folder, '*.avi'))
    if len(vid_names) > NBR_OF_RECORDINGS:
        vid_names.sort()
        last_vid = vid_names[0]
        ## TODO leavy only 24 videos in folder
        os.remove(last_vid)
        print_msg("Removed " + last_vid)


def get_video_name():
    return "./out/" + str(datetime.now()).replace(' ', '_').replace(':', '_') + '.avi'


def print_msg(msg):
    if int(args.verbose) == 1:
        print('\n' + msg + '\n')


def handle_recording():
    global out, rec_start_time, fourcc, RES, FPS, REC_FOLDER, rec_start_time
    try:
        out.release()
        del_last_hour_rec(REC_FOLDER)
        video_name = get_video_name()
        print_msg("Recording {}. Saving in {}".format(video_name, REC_FOLDER))
        out = cv2.VideoWriter(video_name, fourcc, FPS, RES)
        rec_start_time = time.time()
    except Exception as e:
        print(e)
    
    

## Webserver definition
class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        global start_time, webserver, cap, out, rec_start_time, REC_TIME
        #if time.time() - start_time > 90:
           #webserver.shutdown()
           
        if time.time() - rec_start_time > REC_TIME:
            handle_recording()
        
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all clients that's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
            ret_val = self.buffer.write(buf)
            clone = copy.deepcopy(buf)
            try:
                image_as_file = io.BytesIO(clone)
                image_as_pil = Image.open(image_as_file).convert('RGB')
                image_as_cv = np.array(image_as_pil)
                image_as_cv = image_as_cv[:, :, ::-1].copy()
                #cv2.imwrite("test_cv.jpg", image_as_cv) 
                #image_as_pil.save("test.jpg")
                out.write(image_as_cv)
            except Exception as e:
                print(e)
        return ret_val

class StreamingHandler(server.BaseHTTPRequestHandler):
    global output
    def do_GET(self): 
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


## Main function
def main():
    global out, fourcc, RES, FPS, start_time, rec_start_time, webserver, output, REC_FOLDER
    # Start recording
    mkdir_if_not_exists(REC_FOLDER)
    video_name = get_video_name()
    out = cv2.VideoWriter(video_name, fourcc, FPS, RES)
    
    # Camera work
    with picamera.PiCamera(resolution=RES, framerate=FPS) as camera:
        output = StreamingOutput()
        camera.rotation = 90
        camera.start_recording(output, format='mjpeg')
        try:
            if int(args.verbose) == 1:
                print("Camera resolution: " + str(camera.resolution))
                print("Camera framerate: " + str(camera.framerate))
            address = ('', 8000)
            webserver = StreamingServer(address, StreamingHandler)
            start_time = time.time()
            rec_start_time = time.time()
            webserver.serve_forever()
            print("Session ended")
            out.release()
        except Exception as e:
            print("Main exception catched")
            print(e)

        finally:
            camera.stop_recording()



if __name__== "__main__":
    main()