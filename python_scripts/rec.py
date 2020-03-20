# Importing modules
from picamera import PiCamera
from time import sleep
import argparse
import os
from datetime import datetime
from glob import glob

# Parser handling
parser = argparse.ArgumentParser(description='Parsing arguments for recording video ')
parser.add_argument('--res', default='(640,400)', help='Type resolution')
parser.add_argument('--framerate', default='25', help='Type framerate')
parser.add_argument('--time', default='60', help='Type time of recording in minutes')
parser.add_argument('--verbose', default='0', help='Type 1 to enable verbose mode')
args = parser.parse_args()

# Camera setup
camera = PiCamera()
camera.rotation = 180
camera.resolution = tuple(map(int, args.res.replace('(', '').replace(')', '').split(','))) 
camera.framerate = int(args.framerate)

# Time of recording and others
REC_TIME = int(args.time) * 60 
REC_FOLDER = './out'
REC_NAME = 'video.h264'
NBR_OF_RECORDINGS = 24
rec_continue = True


def mkdir_if_not_exists(folder_path):
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
        print_msg("Created folder " + folder_path)

def record_video(rec_time, rec_folder, rec_name):
    mkdir_if_not_exists(rec_folder)
    camera.start_recording(os.path.join(rec_folder, rec_name))
    sleep(rec_time)
    camera.stop_recording()


def del_last_hour_rec(rec_folder):
    vid_names = glob(os.path.join(rec_folder, '*.h264'))
    if len(vid_names) > NBR_OF_RECORDINGS:
        vid_names.sort()
        last_vid = vid_names[0]
        os.remove(last_vid)
        print_msg("Removed " + last_vid)


def get_video_name():
    return str(datetime.now()).replace(' ', '_').replace(':', '_') + '.h264'


def print_msg(msg):
    if int(args.verbose) == 1:
        print('\n' + msg + '\n')


def main():
    while rec_continue:
        video_name = get_video_name()
        del_last_hour_rec(REC_FOLDER)
        record_video(REC_TIME, REC_FOLDER, video_name)
        print_msg(video_name + " recorded and saved in " + REC_FOLDER)


if __name__== "__main__":
    main()

