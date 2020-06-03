# -*- coding: UTF-8 -*-
'''
截取视频，识别结果可视化
'''
import numpy as np
import cv2 as cv
import os
from auto_sub import msec_to_timestring
    
def RAY_mask(hsv):
    lowerhsv = np.array([173,163,219])
    upperhsv = np.array([178,173,230])
    
    #修改这里
    type = 1 #只看颜色是1, 边框交界判断为2
    denoise_level = 5
    bord_meet = 89
    #以上
    
    if type == 1:
        got_mask = cv.inRange(hsv,lowerhsv,upperhsv)
        return got_mask
    if type == 2:
        kernel = np.ones((denoise_level,denoise_level),np.uint8)
        bord_cover = np.ones((bord_meet,bord_meet),np.uint8)        
        bord_lowerhsv = np.array([173,163,219])
        bord_upperhsv = np.array([178,173,230])
        bord_mask = cv.morphologyEx(cv.inRange(hsv,bord_lowhsv,bord_upperhsv), cv.MORPH_OPEN, kernel)
        content_mask = cv.morphologyEx(cv.inRange(hsv,lowerhsv,upperhsv), cv.MORPH_CLOSE, kernel) 
        bord_close = cv.morphologyEx(bord_mask, cv.MORPH_BLACKHAT, bord_cover)
        confirmed_mask = cv.bitwise_and(content_mask,bord_close)
        return confirmed_mask  
 
if __name__ == "__main__": 
    filelist = os.listdir() #在当前文件夹中查找扩展名为.mp4的文件
    select_list =[]
    for filename in filelist:
        if os.path.splitext(filename)[1]== '.webm' or os.path.splitext(filename)[1]== '.mp4' :
            select_list.append(filename)

    if len(select_list)>0:
        for i in range(len(select_list)):
            print(f'{i+1}: {select_list[i]}')
        chosen_one = int(input())-1
        VIDEO_FILENAME = select_list[chosen_one]
    else:
        VIDEO_FILENAME = input('请输入视频文件名（含扩展名）：\n')
    cap = cv.VideoCapture(VIDEO_FILENAME,cv.CAP_FFMPEG)
    FPS = cap.get(cv.CAP_PROP_FPS)
    frame_count = -1
    simple_kernel = np.array([[0,1,0],[1,1,1],[0,1,0]],np.uint8)
    BLACK_new = np.zeros(1920*1080)
    while(cap.isOpened()):
        ret, img = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        frame_count += 1
        print(frame_count)      
      
        if frame_count  % 30 == 0:
                
            small_img=cv.resize(img,None,fx=1,fy=1,interpolation=cv.INTER_NEAREST)
            small_hsv = cv.cvtColor(small_img, cv.COLOR_BGR2HSV)   
            RAYmask=RAY_mask(small_hsv)
            current_frame_msec = cap.get(cv.CAP_PROP_POS_MSEC)
            cv.imshow(f'frame{VIDEO_FILENAME}', small_img)
            print("Frame count:%d"%frame_count)
            print(f"Current time:{msec_to_timestring(current_frame_msec)}")
            print("identified pixels:%d"%(cv.countNonZero(RAYmask)))
            KEY= cv.waitKey(0)
            if KEY == ord('q'):
                break               
            elif KEY == ord('c'):
                print("Captured")
                cv.imwrite(f"{VIDEO_FILENAME}{str(frame_count)}.bmp",img)
            cv.destroyAllWindows() 
            
    cap.release()
    cv.destroyAllWindows()        
            