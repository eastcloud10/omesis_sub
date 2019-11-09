import numpy as np
import cv2 as cv
from auto_sub import frame_to_time 

def RAY_mask(img):
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    lower_ray = np.array([174,163,215])
    upper_ray = np.array([180,170,245])
    ray_mask = cv.inRange(hsv,lower_ray,upper_ray)
    res = cv.morphologyEx(ray_mask, cv.MORPH_OPEN, np.ones((5,5),np.uint8))
    return res
    
def RIO_mask(img):
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    lower_ray = np.array([100,170,188])
    upper_ray = np.array([105,210,217])
    rio_mask = cv.inRange(hsv,lower_ray,upper_ray)
    res = cv.morphologyEx(rio_mask, cv.MORPH_OPEN, np.ones((5,5),np.uint8))
    return res
    
def BLACK_mask(img):
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    lower_ray = np.array([0,0,14])
    upper_ray = np.array([179,40,46])
    black_mask = cv.inRange(hsv,lower_ray,upper_ray)
    res = cv.morphologyEx(black_mask, cv.MORPH_OPEN, np.ones((3,3),np.uint8))
    return res

if __name__ == "__main__": 
    VIDEO_FILENAME = input('请输入视频文件名：\n')
    if VIDEO_FILENAME[-4:] != '.mp4':
        VIDEO_FILENAME = VIDEO_FILENAME+'.mp4'
    cap = cv.VideoCapture(VIDEO_FILENAME,cv.CAP_FFMPEG)
    FPS = cap.get(cv.CAP_PROP_FPS)
    frame_count = 0
    
    previous_BLACK = np.zeros(1920*1080)
    BLACK_new = np.zeros(1920*1080)
    while(cap.isOpened()):
        ret, img = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        frame_count += 1
        if frame_count%30 == 0:
            small_img=cv.resize(img,None,fx=0.5,fy=0.5,interpolation=cv.INTER_AREA)
            cv.imshow('frame', small_img)
            RAYmask=RAY_mask(img)
            RIOmask=RIO_mask(img)
            BLACKmask=BLACK_mask(img)
            cv.imshow('ray', cv.resize(RAYmask,None,fx=0.5,fy=0.5,interpolation=cv.INTER_AREA))            
            cv.imshow('rio', cv.resize(RIOmask,None,fx=0.5,fy=0.5,interpolation=cv.INTER_AREA))
            cv.imshow('black',cv.resize(BLACKmask,None,fx=0.5,fy=0.5,interpolation=cv.INTER_AREA))
            print("RAY pxs:%d\tRIO pxs:%d\tBLACK pxs:%d"%(cv.countNonZero(RAYmask),cv.countNonZero(RIOmask),cv.countNonZero(BLACKmask)))
            KEY= cv.waitKey(0)
            if KEY == ord('q'):
                break               
            elif KEY == ord('c'):
                cv.imwrite("%s.bmp"%str(frame_count),img)
            
    cap.release()
    cv.destroyAllWindows()        
            