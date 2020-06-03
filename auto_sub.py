#编写于python3.7，使用库numpy,opencv(ffmpeg)
# -*- coding: UTF-8 -*-
import numpy as np
import cv2 as cv
import time
import ctypes
import os
import configparser
import sys
from string import Template
from dataclasses import dataclass, field
from typing import List
DEBUG = False
SCALE = 20

def myexcepthook(type, value, traceback, oldhook=sys.excepthook):
    oldhook(type, value, traceback)
    input("请把以上错误信息截图反馈... ")    # use input() in Python 3.x

sys.excepthook = myexcepthook

def find_type_file(*exts):
    filelist = os.listdir() #在当前文件夹中查找扩展名为.mp4的文件
    select_list =[]
    for filename in filelist:
        for ext in exts:
            if os.path.splitext(filename)[1]== ext:
                select_list.append(filename)

    if len(select_list) == 1:
        return_FILENAME = select_list[0]
    elif len(select_list)>1:
        for i in range(len(select_list)):
            print(f'{i+1}: {select_list[i]}')
        chosen_one = int(input("请输入想识别的文件序号，然后回车："))-1
        return_FILENAME = select_list[chosen_one]
    else:
        return_FILENAME = input('请输入文件名（含扩展名）：\n')
    return return_FILENAME

class TIME_it():
    def __init__(self):
        self.starttime = time.time()
        self.ticktime = self.starttime
    def tick(self):
        return time.time() - self.starttime

    
@dataclass
class frame_and_msec:
    hsv: np.array
    frame_msec: int

@dataclass
class frameinfo:
    frame_msec: int
    start_mask: np.array
    start_mask_count: int
    
    

@dataclass
class ACTOR:
    CONTENT_ONLY = 1
    BORD = 2
    DIFFERENTIAL = 3
    actor_list = []
    
    name: str='ray'
    fontname: str='ray字幕'
    defaulttext: str='【ray说：】'
    lowh: np.array=np.array([0,0,0])
    uph: np.array=np.array([180,255,255])
    kernelsize: int=5
    start_amount: int=1200
    end_ratio: float=0.5
    type: int= CONTENT_ONLY
    bordlowh: np.array=np.array([0,0,0])
    borduph: np.array=np.array([180,255,255])
    startframelist: List[frameinfo] = field(default_factory=list)
    BORD_EXAM: np.array=np.ones((89,89),np.uint8)
    
    def __post_init__(self):
        self.kernel = np.ones((self.kernelsize,self.kernelsize),np.uint8)
        self.mask_alpha = ALLZEROS
        self.mask_alpha_sum = 0
        self.sub_count = 0
        ACTOR.actor_list.append(self)        

    def dis_compare(self,frame_list, criteria=0,position=0,repeat=False):
        if len(frame_list) == 1:
            startframemsec = self.startframelist[position].frame_msec
            self.sub_count += 1
            writetimestamp(FPS,startframemsec,frame_list[0].frame_msec,self.fontname,self.defaulttext+str(self.sub_count),repeat)
            self.startframelist.pop(position)
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].hsv
        mask_mid = self.get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
        mask_dis = cv.bitwise_and(self.startframelist[position].start_mask,cv.bitwise_not(mask_mid))
        mask_dis_sum = cv.countNonZero(mask_dis)
        if mask_dis_sum > criteria:
            self.dis_compare(frame_list[:(len(frame_list)+1)//2],criteria,position,repeat)
        else:
            self.dis_compare(frame_list[(len(frame_list)+1)//2:],criteria,position,repeat)
                
    def app_compare(self,frame_list, criteria=0):
        if len(frame_list) == 1:
            for newline in self.startframelist:
                time_interval =  frame_list[0].frame_msec - newline.frame_msec
                if time_interval < MINIMUM_INTERVAL:
                    return
            confirmed_mask = self.get_mask(self.type,frame_list[0].hsv,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
            self.startframelist.insert(0,frameinfo(frame_msec = frame_list[0].frame_msec, \
                                        start_mask = confirmed_mask, \
                                        start_mask_count = cv.countNonZero(confirmed_mask)))
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].hsv
        mask_mid = self.get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
        mask_new = cv.bitwise_and(mask_mid,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        if mask_new_sum > criteria:
            self.app_compare(frame_list[:(len(frame_list)+1)//2],criteria)
        else:
            self.app_compare(frame_list[(len(frame_list)+1)//2:],criteria)
    
    def rough_compare(self,frame_list): #每隔16帧进行一次比对
        mask_omega = self.get_mask(self.type,frame_list[-1].hsv,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)          
        mask_omega_sum = cv.countNonZero(mask_omega)
        
        if len(self.startframelist)>0:
            repeat_flag = False
            for i in list(range(len(self.startframelist)))[::-1]:
                mask_dis = cv.bitwise_and(self.startframelist[i].start_mask,cv.bitwise_not(mask_omega))  
                mask_dis_sum = cv.countNonZero(mask_dis)
                criteria = int(self.startframelist[i].start_mask_count*self.end_ratio)
                if (mask_dis_sum>criteria):
                    self.dis_compare(frame_list,criteria,i,repeat_flag)
                    repeat_flag = True
            
        mask_new = cv.bitwise_and(mask_omega,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        if (mask_new_sum>self.start_amount):
            criteria = int(mask_new_sum//2)
            self.app_compare(frame_list,criteria)
        self.mask_alpha = mask_omega 
        self.mask_alpha_sum = mask_omega_sum
        return
    
    def allend(self,frame_msec): #收尾可能没结束的字幕
        for item in self.startframelist:
            writetimestamp(FPS,item.frame_msec,frame_msec,self.fontname,self.defaulttext,False)
        
#根据范围取mask
    def get_mask(self, type,hsvimg,lowerhsv,upperhsv,kernel,bordlowhsv=1,borduphsv=1,previous_hsvimg=1): #在HSV颜色空间判断字幕像素点
        if type == ACTOR.CONTENT_ONLY:
            got_mask = cv.inRange(hsvimg,lowerhsv,upperhsv)
            return got_mask
        if type == ACTOR.BORD:
            bord_mask = cv.morphologyEx(cv.inRange(hsvimg,bordlowhsv,borduphsv), cv.MORPH_OPEN, kernel)
            content_mask = cv.morphologyEx(cv.inRange(hsvimg,lowerhsv,upperhsv), cv.MORPH_CLOSE, kernel) 
            bord_close = cv.morphologyEx(bord_mask, cv.MORPH_BLACKHAT, self.BORD_EXAM)
            confirmed_mask = cv.bitwise_and(content_mask,bord_close)
            return confirmed_mask
"""    
#从帧数计算（该帧向前取整）的时间，返回的是字符串，第一帧为00:00.00
def frame_to_time(fc): #由于浮点数误差，对60帧和59.94帧特化
    hour,minute,second,centisecond = 0,0,0,0
    if abs(FPS-60)<0.01:
        hour = (fc//216000)
        minute = (fc//3600)%60
        second = (fc//60)%60
        centisecond = (100*fc//60)%100
    elif abs(FPS-59.94)<0.01:
        hour = 1001*fc//216000000
        minute = (1001*fc//3600000)%60
        second = (1001*fc//60000)%60
        centisecond = (1001*fc//600)%100
    else:   #不精确
        hour = int((fc/FPS)/3600)
        minute = int(((fc/FPS)/60)%60)
        second =  int((fc/FPS)%60)
        centisecond = str(fc/FPS%1)[2:4]
    return ("%d:%02d:%02d.%02d"%(hour,minute,second,centisecond))
"""
#初始化空ass文件
def initial_ass():    
    try:
        with open('C:\\Users\\imago\\Documents\\GitHub\\omesis_sub\\empty.ass','r',encoding='utf-8') as fe:
            t=Template(fe.read())
            ASS_BASE = t.substitute(videoname=VIDEO_FILENAME,audioname=VIDEO_FILENAME,)
    except OSError:
        input("无法找到empty.ass...")
        sys.exit()
    try:
        with open(ASS_FILENAME,"w",encoding='utf-8') as f:
            f.write(u'\ufeff') #防Aegisub乱码
            f.write(ASS_BASE)
    except OSError:
        input("无法建立ass字幕文件...")
        sys.exit()
def msec_to_timestring(msec):
    intmsec = int(msec-0.1)
    hour = intmsec//1000//60//60
    minute = (intmsec//1000//60)%60
    second = (intmsec//1000)%60
    msecstring = intmsec%1000//10
    timestring = f'{hour}:{minute}:{second}.'+'{:02d}'.format(msecstring)
    return timestring
    

#向ass中写入时间轴数据
def writetimestamp(FPS,startfmsec,endfmsec,fontname,defaulttext,repeat_flag):
    if repeat_flag:
        text = "[可能重复]"+defaulttext
    else:
        text = defaulttext
    with open(ASS_FILENAME,'a',encoding="utf-8") as f:
        f.write("\nDialogue: 0,%s,%s,%s,,0,0,0,,%s"%(msec_to_timestring(startfmsec),msec_to_timestring(endfmsec),fontname,text))

#进度条显示        
def progress_bar(frame_count,frame_msec):
    totaltime = clock.tick()
    if os.name == 'nt':
        os.system("cls")
        ctypes.windll.kernel32.SetConsoleTitleW("(%d%%)%s"%(100*frame_count/TOTAL_FRAMES,VIDEO_FILENAME))
    print('进度：%d%%'%(100*frame_count/TOTAL_FRAMES))
    print("已处理帧数： %d"%frame_count)
    print("已处理至：%s"%(msec_to_timestring(frame_msec)))
    print("已用时间 %d秒"%totaltime)
    print("每秒视频处理用时 %.2f秒"%(FPS*totaltime/frame_count))
    time_left = (TOTAL_FRAMES - frame_count)*totaltime/frame_count
    print("预计剩余时间：%d分%d秒"%(time_left/60,time_left%60))
    print("--------") #进度条
"""    
@dataclass
class GRAY_ACTOR:
    startframelist: List[frameinfo] = field(default_factory=list)
    lower_h: np.array = np.array([0,0,-156])
    upper_h: np.array = np.array([0,0,-63])
    white_lower_h: np.array = np.array([0,0,252])
    white_upper_h: np.array = np.array([0,6,255])
    kernel: np.array = np.ones((5,5),np.uint8)
    sub_count: int = 0

    def GRAY_check(self,hsv,previous_hsv,current_frame_msec):        
        if len(self.startframelist)>0:
            for i in list(range(len(self.startframelist)))[::-1]:
                content_mask = cv.morphologyEx(cv.inRange(hsv,self.white_lower_h,self.white_upper_h), cv.MORPH_CLOSE, self.kernel)
                if cv.countNonZero(cv.bitwise_and(self.startframelist[i].start_mask, content_mask)) < (self.startframelist[i].start_mask_count*0.8):
                    st = self.startframelist[i].frame_msec
                    self.sub_count += 1
                    writetimestamp(FPS,st,current_frame_msec,'边缘模糊注释',"【模糊%d】"%self.sub_count)
                    self.startframelist.pop(i)  
        signhsv = np.array(hsv,np.int16)
        signprevious_hsv = np.array(previous_hsv,np.int16)
        minus = np.subtract(signhsv,signprevious_hsv)
        mask = cv.inRange(minus,self.lower_h,self.upper_h)
        temp = np.array(mask,np.uint8)
        bord = cv.morphologyEx(temp, cv.MORPH_OPEN, self.kernel)
        if cv.countNonZero(bord)<10000:
            return
        content_mask = cv.morphologyEx(cv.inRange(hsv,self.white_lower_h,self.white_upper_h), cv.MORPH_CLOSE, self.kernel)
        bord_close = cv.morphologyEx(bord, cv.MORPH_BLACKHAT, BIG_KERNEL)
        confirmed_mask = cv.bitwise_and(content_mask,bord_close)
        confirmed_count = cv.countNonZero(confirmed_mask)
        if confirmed_count>20000:
            self.startframelist.append(frameinfo(frame_msec = current_frame_msec,start_mask = confirmed_mask,start_mask_count = confirmed_count))
        return
    def GRAY_END(self,fc):
        for st,start_mask,start_mask_count in self.startframelist:
            writetimestamp(FPS,st,fc,'边缘模糊注释',"【模糊%d】"%self.sub_count)
        return
"""
if __name__ == "__main__": 
    #修改终端标题
    
    if os.name == 'nt':
        os.system("cls")
        ctypes.windll.kernel32.SetConsoleTitleW("omesis字幕轴自动生成")
    global VIDEO_FILENAME,ASS_FILENAME,VIDEO_DIRNAME,VIDEO_BASENAME

    if len(sys.argv)>1:
        VIDEO_FILENAME = sys.argv[1]
    else:
        VIDEO_FILENAME = find_type_file(u'.webm', u'.mp4')
    VIDEO_DIRNAME = os.path.dirname(VIDEO_FILENAME)
    VIDEO_BASENAME = os.path.basename(VIDEO_FILENAME)
    #载入视频
    
    cap = cv.VideoCapture(VIDEO_FILENAME,cv.CAP_FFMPEG) #打开视频
    if not cap.isOpened():
        input("无法读取视频...")
        sys.exit()
    print('成功读取视频')
    global FPS,TOTAL_FRAMES,WIDTH,HEIGHT,ALLZEROS

    FPS = cap.get(cv.CAP_PROP_FPS)                      #帧率
    TOTAL_FRAMES = cap.get(cv.CAP_PROP_FRAME_COUNT)          #总帧数
    WIDTH = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    HEIGHT = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))  
    ALLZEROS = np.zeros((round(HEIGHT/SCALE),round(WIDTH/SCALE)),dtype=np.uint8)

    global MINIMUM_INTERVAL
    settings = configparser.ConfigParser()
    print('config.ini')
    settings.read('C:\\Users\\imago\\Documents\\GitHub\\omesis_sub\\config.ini',encoding='utf-8')
    print(settings['CONFIG'])
    MINIMUM_INTERVAL = int(settings['CONFIG']['最小间隔'])
    SERIES_LENGTH = int(settings['CONFIG']['隔帧判定']) #每隔16帧进行一次对比
    DEBUG = settings.getboolean('CONFIG','DEBUG_MODE')

    
    ASS_FILENAME =VIDEO_DIRNAME + r"【自动生成】"+VIDEO_BASENAME[:-5]+'.ass'
    initial_ass()
    
    #样式列表，可按需添加
    config = configparser.ConfigParser()
    config.read('C:\\Users\\imago\\Documents\\GitHub\\omesis_sub\\actor.ini',encoding='utf-8')

    for style in config.sections():
        ACTOR(name=config[style]['name'],fontname=config[style]['样式名'],defaulttext=config[style]['默认文字'],lowh=np.array([int(config[style]['low_H']),int(config[style]['low_S']),int(config[style]['low_V'])]),\
                uph=np.array([int(config[style]['high_H']),int(config[style]['high_S']),int(config[style]['high_V'])]), BORD_EXAM=np.ones((int(config[style]['边框内覆盖']),int(config[style]['边框内覆盖'])),np.uint8), \
                kernelsize=int(config[style]['降噪等级']),start_amount=int(config[style]['出现判定数']),end_ratio = float(config[style]['结束消失比例']), type=int(config[style]['判定类型']) ,\
                    bordlowh=np.array([int(config[style]['bord_low_H']),int(config[style]['bord_low_S']),int(config[style]['bord_low_V'])]),borduph=np.array([int(config[style]['bord_high_H']),int(config[style]['bord_high_S']),int(config[style]['bord_high_V'])]))

    #进度条
    global frame_count
    print("----------")
    frame_count = -1
    period_frames = []
    clock = TIME_it()
    alpha_frame_count = -1
    previoushsv = np.zeros((round(HEIGHT/SCALE),round(WIDTH/SCALE),3),dtype=np.uint8)
    while(cap.isOpened()):
        ret, img = cap.read()
        if ret is False:#没有帧了    
            break
        current_frame_msec = cap.get(cv.CAP_PROP_POS_MSEC)
        frame_count += 1 #成功读帧，帧数+1
        small_img=cv.resize(img,None,fx=1/SCALE,fy=1/SCALE,interpolation=cv.INTER_NEAREST)
        hsv = cv.cvtColor(small_img, cv.COLOR_BGR2HSV)
        period_frames.append(frame_and_msec(hsv=hsv,frame_msec=current_frame_msec))
        
        if frame_count%SERIES_LENGTH == SERIES_LENGTH-1:
            for actor in ACTOR.actor_list:
                actor.rough_compare(period_frames)
            alpha_frame_count = frame_count
            period_frames = []
            print('|',end='',flush=True)
            if frame_count%(10*SERIES_LENGTH) == SERIES_LENGTH-1:
                progress_bar(frame_count,current_frame_msec)
        
    #收尾可能没结束的字幕
    for actor in ACTOR.actor_list:
        actor.allend(current_frame_msec)
        
    #释放资源
    cap.release()
    cv.destroyAllWindows()
    
    print("\n处理完成")
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW("(处理完成)%s"%(VIDEO_FILENAME))
    input('按Enter结束。。。')

