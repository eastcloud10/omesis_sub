#编写于python3.7，使用库numpy,opencv(ffmpeg)
# -*- coding: UTF-8 -*-
FFMPEG_BIN = "ffmpeg.exe" # on Windows
import subprocess as sp
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
SCALE = 1



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
    img: np.array
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
            if DEBUG:
                print("字幕消失时间："+str(frame_list[0].frame_msec))
            startframemsec = self.startframelist[position].frame_msec
            self.sub_count += 1
            writetimestamp(FPS,startframemsec,frame_list[0].frame_msec,self.fontname,self.defaulttext,repeat)
            self.startframelist.pop(position)
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].img
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
                if DEBUG:
                    print("字幕出现时间："+str(frame_list[0].frame_msec))
                time_interval =  frame_list[0].frame_msec - newline.frame_msec
                if time_interval < MINIMUM_INTERVAL:
                    return
            confirmed_mask = self.get_mask(self.type,frame_list[0].img,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
            self.startframelist.insert(0,frameinfo(frame_msec = frame_list[0].frame_msec, \
                                        start_mask = confirmed_mask, \
                                        start_mask_count = cv.countNonZero(confirmed_mask)))
            return
        mid_frame = frame_list[(len(frame_list)-1)//2].img
        mask_mid = self.get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)
        mask_new = cv.bitwise_and(mask_mid,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        if mask_new_sum > criteria:
            self.app_compare(frame_list[:(len(frame_list)+1)//2],criteria)
        else:
            self.app_compare(frame_list[(len(frame_list)+1)//2:],criteria)
    
    def rough_compare(self,frame_list): #每隔16帧进行一次比对
        mask_omega = self.get_mask(self.type,frame_list[-1].img,self.lowh,self.uph,self.kernel,self.bordlowh,self.borduph)          
        mask_omega_sum = cv.countNonZero(mask_omega)
        
        if len(self.startframelist)>0:
            repeat_flag = False
            for i in list(range(len(self.startframelist)))[::-1]:
                mask_dis = cv.bitwise_and(self.startframelist[i].start_mask,cv.bitwise_not(mask_omega))  
                mask_dis_sum = cv.countNonZero(mask_dis)
                criteria = int(self.startframelist[i].start_mask_count*self.end_ratio)
                if (mask_dis_sum>criteria):
                    if DEBUG:
                        print("字幕消失："+self.name+" 消失像素数："+str(mask_dis_sum))
                    self.dis_compare(frame_list,criteria,i,repeat_flag)
                    repeat_flag = True
            
        mask_new = cv.bitwise_and(mask_omega,cv.bitwise_not(self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        if (mask_new_sum>self.start_amount):
            if DEBUG:
                print("字幕出现："+self.name+" 新出现像素数："+str(mask_new_sum))
            criteria = int(mask_new_sum//2)
            self.app_compare(frame_list,criteria)
        self.mask_alpha = mask_omega 
        self.mask_alpha_sum = mask_omega_sum
        return
    
    def allend(self,frame_msec): #收尾可能没结束的字幕
        for item in self.startframelist:
            writetimestamp(FPS,item.frame_msec,frame_msec,self.fontname,self.defaulttext,False)
        
#根据范围取mask
    def get_mask(self, type,img,lowerimg,upperimg,kernel,bordlowimg=1,bordupimg=1,previous_img=1): #判断字幕像素点
        if type == ACTOR.CONTENT_ONLY:
            got_mask = cv.inRange(img,lowerimg,upperimg)
            return got_mask
        if type == ACTOR.BORD:
            bord_mask = cv.morphologyEx(cv.inRange(img,bordlowimg,bordupimg), cv.MORPH_OPEN, kernel)
            content_mask = cv.morphologyEx(cv.inRange(img,lowerimg,upperimg), cv.MORPH_CLOSE, kernel) 
            bord_close = cv.morphologyEx(bord_mask, cv.MORPH_BLACKHAT, self.BORD_EXAM)
            confirmed_mask = cv.bitwise_and(content_mask,bord_close)
            return confirmed_mask
            
#初始化空ass文件
def initial_ass():    
    ASS_BASE = f"""
[Script Info]
; Script generated by Aegisub 3.2.2
; http://www.aegisub.org/
Title: New subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[Aegisub Project Garbage]
Last Style Storage: Default
Audio File: {VIDEO_FILENAME}
Video File: {VIDEO_FILENAME}
Video AR Mode: 4
Video AR Value: 1.777778
Video Zoom Percent: 0.375000
Scroll Position: 0
Active Line: 0
Video Position: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,45,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,4.5,4.5,2,30,30,23,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
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
        if KEEP_REPEAT is False:
            return
        else:
            text = "[可能重复]"+defaulttext
    else:
        text = defaulttext
    with open(ASS_FILENAME,'a',encoding="utf-8") as f:
        f.write("\nDialogue: 0,%s,%s,%s,,0,0,0,,%s"%(msec_to_timestring(startfmsec),msec_to_timestring(endfmsec),fontname,text))

#进度条显示        
def progress_bar(frame_count,frame_msec):
    totaltime = clock.tick()
    if os.name == 'nt' :
        if not DEBUG:
            os.system("cls")
        ctypes.windll.kernel32.SetConsoleTitleW("(%d%%)%s"%(100*frame_count/TOTAL_FRAMES,VIDEO_FILENAME+" by 见象 from Omesis搬运组"))
    print('进度：%d%%'%(100*frame_count/TOTAL_FRAMES))
    print("已处理帧数： %d"%frame_count)
    print("已处理至：%s"%(msec_to_timestring(frame_msec)))
    print("已用时间 %d秒"%totaltime)
    print("每秒视频处理用时 %.2f秒"%(FPS*totaltime/frame_count))
    time_left = (TOTAL_FRAMES - frame_count)*totaltime/frame_count
    print("预计剩余时间：%d分%d秒"%(time_left/60,time_left%60))
    print("--------") #进度条

if __name__ == "__main__": 
    #修改终端标题
    
    if os.name == 'nt':
        os.system("cls")
        ctypes.windll.kernel32.SetConsoleTitleW("omesis字幕轴自动生成 by 见象 from Omesis搬运组")
    global VIDEO_FILENAME,ASS_FILENAME,VIDEO_DIRNAME,VIDEO_BASENAME

    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    print("当前工作目录："+application_path)
    
    if len(sys.argv)>1:
        VIDEO_FILENAME = sys.argv[1]
    else:
        VIDEO_FILENAME = find_type_file(u'.webm', u'.mp4', u'.mkv')
    VIDEO_DIRNAME = os.path.dirname(VIDEO_FILENAME)
    VIDEO_BASENAME = os.path.basename(VIDEO_FILENAME)
    #载入视频
    
    global MINIMUM_INTERVAL, KEEP_REPEAT
    settings = configparser.ConfigParser()
    print('config.ini')
    try:
        settings.read(application_path+'\\config.ini',encoding='utf-8')
        print(settings['CONFIG'])
        KEEP_REPEAT = settings.getboolean('CONFIG','保留重叠')
        MINIMUM_INTERVAL = int(settings['CONFIG']['最小间隔'])
    except:
        KEEP_REPEAT = False
        MINIMUM_INTERVAL = 500
    #DEBUG = settings.getboolean('CONFIG','DEBUG_MODE')
    
        
    command = [ FFMPEG_BIN,
            '-i', VIDEO_FILENAME,
            #'-c:v','h264',
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vf', "scale=in_color_matrix=bt709",
            '-vcodec', 'rawvideo',
            '-loglevel', 'quiet' , '-']
    pipe = sp.Popen(command, stdout = sp.PIPE, bufsize=10**7,close_fds=True)
    
    if DEBUG:
        print("视频路径："+VIDEO_FILENAME)
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


    if abs(FPS-60) < 1:
        SERIES_LENGTH = 16
    elif abs(FPS-30) < 1:
        SERIES_LENGTH = 8
    else:
        SERIES_LENGTH = 2

    ALLZEROS = np.zeros((round(HEIGHT/SCALE),round(WIDTH/SCALE)),dtype=np.uint8)
    
    ASS_FILENAME =VIDEO_DIRNAME + r"\\【自动生成】"+VIDEO_BASENAME[:-5]+'.ass'
    initial_ass()
    
    #样式列表，可按需添加
    config = configparser.ConfigParser()
    ACTOR_DEFAULT_BASE = """###############
[DEFAULT]
#备注名
name = 示例

#aegisub中将用到的样式名
样式名 = unchi字幕

#在本样式的行中打入的默认文字。可留空。可使用大括号写入tag、注释
默认文字 = {ぶりぶり}

#字幕颜色上下界。字幕颜色可使用QQ截图，或视频截图+取色工具查看。建议在中间色基础上，上下容差度各10。
#红
low_R = 50
high_R = 70

#绿
low_G = 110
high_G = 130

#蓝
low_B = 200
high_B = 220

#边框HSV上下界。仅在开启边框判定时需要
#边框红
bord_low_R = 0
bord_high_R = 255

#边框绿
bord_low_G = 0
bord_high_G = 255

#边框蓝
bord_low_B = 0
bord_high_B = 43

#消除噪点
降噪等级 = 5

#出现多少面积认定为字幕出现。参考值：正常字幕，一个字约占全画面的千分之3。
出现判定（千分比） = 5

# 0~1的小数。字幕中有多少比例消失时，认定为结束。例如：0.3表示有30%消失时触发结束
结束消失比例 = 0.5

#判定类型：1=只判断一种颜色，2=判断边框及字色
判定类型 = 1

#仅边框判定类型需要。边框向内覆盖半径（像素数）。建议稍大于字的笔画粗度的一半。
边框内覆盖 = 89
"""
    try:
        with open(application_path+'\\default.ini',"w",encoding='utf-8') as f:
            f.write(ACTOR_DEFAULT_BASE)
    except OSError:
        input("无法建立文件...")
        sys.exit()
        
    try:
        config.read(application_path+'\\default.ini',encoding='utf-8')
        config.read(application_path+'\\actor.ini',encoding='utf-8')

        for style in config.sections():
            ACTOR(name=config[style]['name'],fontname=config[style]['样式名'],defaulttext=config[style]['默认文字'],lowh=np.array([int(config[style]['low_B']),int(config[style]['low_G']),int(config[style]['low_R'])]),\
                    uph=np.array([int(config[style]['high_B']),int(config[style]['high_G']),int(config[style]['high_R'])]), BORD_EXAM=np.ones((int(config[style]['边框内覆盖']),int(config[style]['边框内覆盖'])),np.uint8), \
                    kernelsize=int(config[style]['降噪等级']),start_amount = WIDTH*HEIGHT*float(config[style]['出现判定（千分比）'])//(SCALE*1000),end_ratio = float(config[style]['结束消失比例']), type=int(config[style]['判定类型']) ,\
                        bordlowh=np.array([int(config[style]['bord_low_B']),int(config[style]['bord_low_G']),int(config[style]['bord_low_R'])]),borduph=np.array([int(config[style]['bord_high_B']),int(config[style]['bord_high_G']),int(config[style]['bord_high_R'])]))
    except OSError:
        print('没找到字幕颜色信息，请生成')

    #进度条
    global frame_count
    print("----------")
    frame_count = -1
    period_frames = []
    clock = TIME_it()
    alpha_frame_count = -1
    previousimg = np.zeros((round(HEIGHT/SCALE),round(WIDTH/SCALE),3),dtype=np.uint8)
    while(cap.isOpened()):
        raw_image = pipe.stdout.read(WIDTH*HEIGHT*3)
        image =  np.frombuffer(raw_image, dtype='uint8')
        
        
        ret, imgshit = cap.read()
        if ret is False or image.size == 0:#没有帧了    
            pipe.stdout.flush()
            break
        img = image.reshape((HEIGHT,WIDTH,3))
        current_frame_msec = cap.get(cv.CAP_PROP_POS_MSEC)
        frame_count += 1 #成功读帧，帧数+1
        small_img=cv.resize(img,None,fx=1/SCALE,fy=1/SCALE,interpolation=cv.INTER_NEAREST)

        period_frames.append(frame_and_msec(img=small_img,frame_msec=current_frame_msec))
        
        if frame_count%SERIES_LENGTH == SERIES_LENGTH-1:
            if DEBUG:
                print("当前帧数"+str(frame_count))
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

