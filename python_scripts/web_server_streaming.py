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


PAGE="""\
<html>
<head>
<title>Raspberry Pi - MIR watching</title>
</head>
<body>
<center><h1>Raspberry Pi - MIR watching</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""
start_time = -1
webserver = -1
#fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20, (640,480))


class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        global start_time, webserver, cap, out
        if time.time() - start_time > 15:
           webserver.shutdown()
        

        
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
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
                print("Zapis do pliku")
                print(e)
        return ret_val

class StreamingHandler(server.BaseHTTPRequestHandler):
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

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    #Uncomment the next line to change your Pi's Camera rotation (in degrees)
    camera.rotation = 90
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8000)
        webserver = StreamingServer(address, StreamingHandler)
        start_time = time.time() 
        webserver.serve_forever()
        print("ended")
        out.release()
    except Exception as e:
        print("Glowny exception")
        print(e)

    finally:
        camera.stop_recording()
