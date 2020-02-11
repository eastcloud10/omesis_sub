#编写于python3.7，使用库numpy,opencv(ffmpeg)
# -*- coding: UTF-8 -*-
import numpy as np
import cv2 as cv
import time
import ctypes
import os
from dataclasses import dataclass, field
from typing import List
DEBUG = False

def find_type_file(*exts):
    filelist = os.listdir() #在当前文件夹中查找扩展名为.mp4的文件
    select_list =[]
    for filename in filelist:
        for ext in exts:
            if os.path.splitext(filename)[1]== ext:
                select_list.append(filename)

    if len(select_list)>0:
        for i in range(len(select_list)):
            print(f'{i+1}: {select_list[i]}')
        chosen_one = int(input())-1
        return_FILENAME = select_list[chosen_one]
    else:
        return_FILENAME = input('请输入文件名（含扩展名）：\n')
    return return_FILENAME

if DEBUG:
    os.name = 'DEBUG'
def round_kernel_generator(radius):
    ret = np.ones((2*radius+1,2*radius+1),np.uint8)
    for x in range(2*radius+1):
        for y in range(2*radius+1):
            if (x-radius)**2 + (y-radius)**2 > radius**2:
                ret[x,y] = 0
    return ret
ROUND_KERNEL = np.ones((89,89),np.uint8)
BIG_KERNEL = round_kernel_generator(100)

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

    
    def __post_init__(self):
        self.kernel = np.ones((self.kernelsize,self.kernelsize),np.uint8)
        self.mask_alpha = ALLZEROS
        self.mask_alpha_sum = 0
        self.sub_count = 0
        ACTOR.actor_list.append(self)        

    def dis_compare(self,frame_list, criteria=0,position=0):
        if len(frame_list) == 1:
            startframemsec = self.startframelist[position].frame_msec
            self.sub_count += 1
            writetimestamp(FPS,startframemsec,frame_list[0].frame_msec,self.fontname,self.defaulttext+str(self.sub_count))
            self.startframelist.pop(position)
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].hsv
        mask_mid = get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
        mask_dis = cv.bitwise_and(self.startframelist[position].start_mask,cv.bitwise_not(mask_mid))
        mask_dis_sum = cv.countNonZero(mask_dis)
        if mask_dis_sum > criteria:
            self.dis_compare(frame_list[:(len(frame_list)+1)//2],criteria,position)
        else:
            self.dis_compare(frame_list[(len(frame_list)+1)//2:],criteria,position)
                
    def app_compare(self,frame_list, criteria=0):
        if len(frame_list) == 1:
            confirmed_mask = get_mask(self.type,frame_list[0].hsv,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
            self.startframelist.append(frameinfo(frame_msec = frame_list[0].frame_msec, \
                                        start_mask = confirmed_mask, \
                                        start_mask_count = cv.countNonZero(confirmed_mask)))
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].hsv
        mask_mid = get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
        mask_new = cv.bitwise_and(mask_mid,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        if mask_new_sum > criteria:
            self.app_compare(frame_list[:(len(frame_list)+1)//2],criteria)
        else:
            self.app_compare(frame_list[(len(frame_list)+1)//2:],criteria)
    
    def rough_compare(self,frame_list): #每隔16帧进行一次比对
        mask_omega = get_mask(self.type,frame_list[-1].hsv,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)          
        mask_omega_sum = cv.countNonZero(mask_omega)
        
        if len(self.startframelist)>0:
            for i in list(range(len(self.startframelist)))[::-1]:
                mask_dis = cv.bitwise_and(self.startframelist[i].start_mask,cv.bitwise_not(mask_omega))  
                mask_dis_sum = cv.countNonZero(mask_dis)
                criteria = int(self.startframelist[i].start_mask_count*self.end_ratio)
                if (mask_dis_sum>criteria):
                    self.dis_compare(frame_list,criteria,i)
            
        mask_new = cv.bitwise_and(mask_omega,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        flag = True
        if (mask_new_sum>self.start_amount):
            for newline in self.startframelist:
                duplication = cv.bitwise_and(newline.start_mask, mask_new)
                if 5*cv.countNonZero(duplication) > mask_new_sum:
                    flag = False
                    break
            if flag:
                criteria = int(mask_new_sum//2)
                self.app_compare(frame_list,criteria)
        self.mask_alpha = mask_omega 
        self.mask_alpha_sum = mask_omega_sum
        return
    
    def allend(self,frame_msec): #收尾可能没结束的字幕
        for st,start_mask,start_mask_count in self.startframelist:
            writetimestamp(FPS,st,frame_msec,self.fontname,self.defaulttext)
        
#根据范围取mask
def get_mask(type,hsvimg,lowerhsv,upperhsv,kernel,bordlowhsv=1,borduphsv=1,previous_hsvimg=1): #在HSV颜色空间判断字幕像素点
    if type == ACTOR.CONTENT_ONLY:
        got_mask = cv.inRange(hsvimg,lowerhsv,upperhsv)
        temp = cv.morphologyEx(got_mask, cv.MORPH_OPEN, kernel) #OPEN操作，消除噪点
        if cv.countNonZero(got_mask)<8000:
            return ALLZEROS
        res = cv.morphologyEx(temp, cv.MORPH_CLOSE, ROUND_KERNEL) #补洞
        return got_mask
    if type == ACTOR.BORD:
        bord_mask = cv.morphologyEx(cv.inRange(hsvimg,bordlowhsv,borduphsv), cv.MORPH_OPEN, kernel)
        content_mask = cv.morphologyEx(cv.inRange(hsvimg,lowerhsv,upperhsv), cv.MORPH_CLOSE, kernel) 
        bord_close = cv.morphologyEx(bord_mask, cv.MORPH_BLACKHAT, ROUND_KERNEL)
        confirmed_mask = cv.bitwise_and(content_mask,bord_close)
        return confirmed_mask
    
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

#初始化空ass文件
def initial_ass():    
    ASS_BASE="""[Script Info]
; Script generated by Aegisub 3.2.2
; http://www.aegisub.org/
Title: New subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
[Aegisub Project Garbage]
Last Style Storage: Default
Audio File: %s
Video File: %s
Video AR Mode: 4
Video AR Value: 1.777778
Video Zoom Percent: 0.375000
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,45,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,4.5,4.5,2,30,30,23,1
Style: ray字幕,Microsoft YaHei UI,100,&H005F4EE3,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,10,10,220,1
Style: rio字幕,Microsoft YaHei UI,100,&H00D98936,&H000000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,10,10,220,1
Style: 薄边框注释,Microsoft YaHei UI,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1
Style: 双色,Microsoft YaHei UI,100,&H005F4EE3,&H000000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,8,0,2,10,10,360,1
Style: 边缘模糊注释,宋体,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: ray1通常,Microsoft YaHei UI,80,&H005F4EE3,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,10,1
Style: rio1通常,Microsoft YaHei UI,80,&H00D98936,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,10,1
Style: 加厚边框注释,Microsoft YaHei UI,120,&H00FFFFFF,&H000000FF,&H00202020,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,10,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Comment: 2,0:00:00.00,0:00:00.01,ray字幕,,0,0,0,template line keeptags,
Comment: 1,0:00:00.00,0:00:00.01,ray字幕,,0,0,0,template line keeptags,{\\bord9\\3c&H5F4EE3&}
Comment: 2,0:00:00.00,0:00:00.01,ray1通常,,0,0,0,template line keeptags,
Comment: 1,0:00:00.00,0:00:00.01,ray1通常,,0,0,0,template line keeptags,{\\bord7\\3c&H5F4EE3&}
Comment: 2,0:00:00.00,0:00:00.01,rio字幕,,0,0,0,template line keeptags,
Comment: 1,0:00:00.00,0:00:00.01,rio字幕,,0,0,0,template line keeptags,{\\bord9\\3c&HD98936&}
Comment: 2,0:00:00.00,0:00:00.01,rio1通常,,0,0,0,template line keeptags,
Comment: 1,0:00:00.00,0:00:00.01,rio1通常,,0,0,0,template line keeptags,{\\bord7\\3c&HD98936&}
Comment: 2,0:00:00.00,0:00:00.01,双色,,0,0,0,template line keeptags,{\\pos($sx,$sy)\\clip(!$lleft-20!,!$ltop-20!,!$lright+20!,$lmiddle)}
Comment: 1,0:00:00.00,0:00:00.01,双色,,0,0,0,template line keeptags,{\\pos($sx,$sy)\\bord12\\3c&H5F4EE3&\\clip(!$lleft-20!,!$ltop-20!,!$lright+20!,$lmiddle)}
Comment: 2,0:00:00.00,0:00:00.01,双色,,0,0,0,template line keeptags,{\\pos($sx,$sy)\\1c&HD98936&\\clip(!$lleft-20!,$lmiddle,!$lright+20!,!$lbottom+20!)}
Comment: 1,0:00:00.00,0:00:00.01,双色,,0,0,0,template line keeptags,{\\pos($sx,$sy)\\bord12\\3c&HD98936&\\1c&HD98936&\\clip(!$lleft-20!,$lmiddle,!$lright+20!,!$lbottom+20!)}
"""%(VIDEO_FILENAME,VIDEO_FILENAME)
    with open(ASS_FILENAME,"w",encoding='utf-8') as f:
        f.write(u'\ufeff') #防Aegisub乱码
        f.write(ASS_BASE)
        
def msec_to_timestring(msec):
    intmsec = int(msec-0.1)
    hour = intmsec//1000//60//60
    minute = (intmsec//1000//60)%60
    second = (intmsec//1000)%60
    msecstring = intmsec%1000//10
    timestring = f'{hour}:{minute}:{second}.'+'{:02d}'.format(msecstring)
    return timestring
    

#向ass中写入时间轴数据
def writetimestamp(FPS,startfmsec,endfmsec,fontname,defaulttext):
    with open(ASS_FILENAME,'a',encoding="utf-8") as f:
        f.write("\nDialogue: 0,%s,%s,%s,,0,0,0,,%s"%(msec_to_timestring(startfmsec),msec_to_timestring(endfmsec),fontname,defaulttext))

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
    def GRAY_END(self):
        for st,start_mask,start_mask_count in self.startframelist:
            writetimestamp(FPS,st,fc,'边缘模糊注释',"【模糊%d】"%self.sub_count)
        return

if __name__ == "__main__": 
    #修改终端标题    
    SERIES_LENGTH = 16 #每隔16帧进行一次对比
    if os.name == 'nt':
        os.system("cls")
        ctypes.windll.kernel32.SetConsoleTitleW("omesis字幕轴自动生成")
    global VIDEO_FILENAME,ASS_FILENAME
       
    VIDEO_FILENAME = find_type_file(u'.webm', u'.mp4')
    
    #载入视频
    cap = cv.VideoCapture(VIDEO_FILENAME,cv.CAP_FFMPEG) #打开视频
    print('成功读取视频')
    global FPS,TOTAL_FRAMES,WIDTH,HEIGHT,ALLZEROS

    FPS = cap.get(cv.CAP_PROP_FPS)                      #帧率
    TOTAL_FRAMES = cap.get(cv.CAP_PROP_FRAME_COUNT)          #总帧数
    WIDTH = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    HEIGHT = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))  
    ALLZEROS = np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
    

    ASS_FILENAME = "【自动生成】"+VIDEO_FILENAME[:-5]+'.ass'
    initial_ass()
    
    #样式列表，可按需添加
    RAY = ACTOR(name='ray',fontname='ray字幕',defaulttext='【ray说：】',lowh=np.array([172,160,218]),uph=np.array([179,173,230]), \
                kernelsize=5,start_amount=2000,end_ratio = 0.5, type=ACTOR.CONTENT_ONLY)
    RIO = ACTOR(name='rio',fontname='rio字幕',defaulttext='【rio说：】',lowh=np.array([102,189,211]),uph=np.array([107,199,222]), \
                kernelsize=5,start_amount=2000,end_ratio = 0.5, type=ACTOR.CONTENT_ONLY)
    BLACK =ACTOR(name='BLACK',fontname='加厚边框注释',defaulttext=r'【黑边框文字】',lowh=np.array([0,0,252]),uph=np.array([255,6,255]), \
                kernelsize=5,start_amount=20000,end_ratio = 0.5, type=ACTOR.BORD,\
                bordlowh=np.array([0,0,0]),borduph=np.array([255,255,43]))
    GRAY = GRAY_ACTOR()
    
    #PONPOKO = ACTOR(name='ponpoko',fontname='ponpoko字幕',defaulttext='【ponpoko说：】',lowh=np.array([56,178,189]),uph=np.array([67,193,207]), \
    #            kernelsize=5,start_amount=2000,end_ratio = 0.5, type=ACTOR.CONTENT_ONLY)
    #PEANUTS = ACTOR(name='peanuts',fontname='peanuts字幕',defaulttext='【peanuts说：】',lowh=np.array([4,188,233]),uph=np.array([12,196,248]), \
    #            kernelsize=5,start_amount=2000,end_ratio = 0.5, type=ACTOR.CONTENT_ONLY)
    #进度条
    global frame_count
    print("----------")
    frame_count = -1
    period_frames = []
    clock = TIME_it()
    alpha_frame_count = -1
    previoushsv = np.zeros((HEIGHT,WIDTH,3),dtype=np.uint8)
    while(cap.isOpened()):
        ret, img = cap.read()
        if ret is False:#没有帧了    
            break
        current_frame_msec = cap.get(cv.CAP_PROP_POS_MSEC)
        frame_count += 1 #成功读帧，帧数+1
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        
        #GRAY
        period_frames.append(frame_and_msec(hsv=hsv,frame_msec=current_frame_msec))
        GRAY.GRAY_check(hsv,previoushsv,current_frame_msec)
        previoushsv = hsv
        
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
    GRAY.GRAY_END()
        
    #释放资源
    cap.release()
    cv.destroyAllWindows()
    
    print("\n处理完成")
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW("(处理完成)%s"%(VIDEO_FILENAME))
    input('按Enter结束。。。')

