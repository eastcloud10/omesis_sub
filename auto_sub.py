#编写于python3.7，使用库numpy,opencv(ffmpeg)
# -*- coding: UTF-8 -*-
import numpy as np
import cv2 as cv
import time
import ctypes
import os

os.name = '123321'

def round_kernel_generator(radius):
    ret = np.ones((2*radius+1,2*radius+1),np.uint8)
    for x in range(2*radius+1):
        for y in range(2*radius+1):
            if (x-radius)**2 + (y-radius)**2 > radius**2:
                ret[x,y] = 0
    return ret
ROUND_KERNEL = round_kernel_generator(40)

class TIME_it():
    def __init__(self):
        self.starttime = time.time()
        self.ticktime = self.starttime
    def tick(self):
        return time.time() - self.starttime
class ACTOR():
    CONTENT_ONLY = 1
    BORD = 2
    DIFFERENTIAL = 3
    actor_list = []

    def __init__(self,name='ray',fontname='ray字幕',defaulttext='【ray说：】',lowh=np.array([0,0,0]),uph=np.array([180,255,255]),kernelsize=5, \
                start_amount=1200,end_amount=1000, \
                type = CONTENT_ONLY, \
                bordlowh=np.array([0,0,0]),borduph=np.array([180,255,255]), **kwargs):
        self.name = name
        self.lowh = lowh #HSV颜色空间的上、下界
        self.uph = uph
        self.kernelsize = kernelsize #OPEN操作的框尺寸
        self.start_amount = start_amount
        self.end_amount = end_amount
        self.previous_mask = np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
        self.previous_mask_sum = 0
        self.startframelist =[]
        self.mask_alpha = np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
        self.mask_alpha_sum = 0
        self.fontname = fontname
        self.defaulttext = defaulttext #默认文本
        self.bordlowh = bordlowh
        self.borduph = borduph
        self.type = type
        
        if self.type == ACTOR.DIFFERENTIAL:
            self.mask2_alpha = np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
            self.mask2_alpha_sum = 0
            self.frame_minusone = np.zeros((1080,1920,3))
            self.saved_mask = []
        ACTOR.actor_list.append(self)
        
        if self.type == ACTOR.DIFFERENTIAL:
            '''
            Very very time consuming
            '''
            def differential_compare(frame_list,frame_count_of_list0):
                mask_omega = get_mask(ACTOR.CONTENT_ONLY,frame_list[-1],self.lowh,self.uph,self.kernelsize)          
                mask_omega_sum = cv.countNonZero(mask_omega)
                mask_new = cv.bitwise_and(mask_omega,cv.bitwise_xor(mask_omega,self.mask_alpha))
                mask_new_sum = cv.countNonZero(mask_new)
                mask_dis_sum = self.mask_alpha_sum + mask_new_sum - mask_omega_sum 
                self.mask_alpha = mask_omega 
                self.mask_alpha_sum = mask_omega_sum 
                
                if mask_new_sum < 15000 and mask_dis_sum <15000:
                    return
                for i in range(len(frame_list)):
                    if i == 0:
                        mask = get_mask(self.type,frame_list[0],self.lowh,self.uph,self.kernelsize,bordlowhsv=self.bordlowh,borduphsv=self.borduph,previous_hsvimg=self.frame_minusone)
                    else:
                        mask = get_mask(self.type,frame_list[i],self.lowh,self.uph,self.kernelsize,bordlowhsv=self.bordlowh,borduphsv=self.borduph,previous_hsvimg=frame_list[i-1])
                    if len(self.saved_mask)>0:
                        for j in range(len(self.saved_mask)):
                            check = cv.countNonZero(\
                                       cv.bitwise_and(\
                                       self.saved_mask[j],\
                                       get_mask(ACTOR.CONTENT_ONLY,frame_list[i],self.lowh,self.uph,self.kernelsize)\
                                       ))
                            if check>self.end_amount:
                                for st in self.startframelist:
                                    if frame_count_of_list0 - st >= 30:
                                        writetimestamp(FPS,st,frame_count_of_list0,self.fontname,self.defaulttext)
                                self.startframelist=[]
                                self.saved_mask = []
                                break
                    if cv.countNonZero(mask) > self.start_amount:
                        self.startframelist.append(frame_count_of_list0+i)
                        self.saved_mask.append(mask)
                        break
                self.frame_minusone = frame_list[-1]
                return
            self.rough_compare = differential_compare

    def deep_compare(self,frame_list, criteria_new=0, criteria_dis=0,frame_count_of_list0=1):
        if len(frame_list) == 1:
            if criteria_dis:
                for st in self.startframelist:
                    if frame_count_of_list0 - st >= 30:
                        writetimestamp(FPS,st,frame_count_of_list0,self.fontname,self.defaulttext)
                self.startframelist=[]
            if criteria_new:
                if len(self.startframelist)>0:
                    if frame_count_of_list0 - self.startframelist[-1] < 60:
                        return
                self.startframelist.append(frame_count_of_list0)
            return
        mid_frame = frame_list[(len(frame_list)-1)//2]
        mask_mid = get_mask(self.type,mid_frame,self.lowh,self.uph,self.kernelsize)
        if criteria_dis:
            mask_dis = cv.bitwise_and(self.mask_alpha,cv.bitwise_xor(self.mask_alpha,mask_mid))
            mask_dis_sum = cv.countNonZero(mask_dis)
            if mask_dis_sum > criteria_dis:
                self.deep_compare(frame_list[:(len(frame_list)+1)//2],0,criteria_dis,frame_count_of_list0)
            else:
                self.deep_compare(frame_list[(len(frame_list)+1)//2:],0,criteria_dis,frame_count_of_list0+(len(frame_list)+1)//2)
        if criteria_new:
            mask_new = cv.bitwise_and(mask_mid,cv.bitwise_xor(mask_mid,self.mask_alpha))
            mask_new_sum = cv.countNonZero(mask_new)
            if mask_new_sum > criteria_new:
                self.deep_compare(frame_list[:(len(frame_list)+1)//2],criteria_new,0,frame_count_of_list0)
            else:
                self.deep_compare(frame_list[(len(frame_list)+1)//2:],criteria_new,0,frame_count_of_list0+(len(frame_list)+1)//2)
    
    def rough_compare(self,frame_list,frame_count_of_alpha): #每隔16帧进行一次比对
        criteria_dis,criteria_new = 0,0
        mask_omega = get_mask(self.type,frame_list[-1],self.lowh,self.uph,self.kernelsize,self.bordlowh,self.borduph)          
        mask_omega_sum = cv.countNonZero(mask_omega)
        mask_new = cv.bitwise_and(mask_omega,cv.bitwise_xor(mask_omega,self.mask_alpha))
        mask_new_sum = cv.countNonZero(mask_new)
        mask_dis_sum = self.mask_alpha_sum + mask_new_sum - mask_omega_sum    
        
        if (mask_dis_sum>self.end_amount):
            criteria_dis = mask_dis_sum//2
        if (mask_new_sum>self.start_amount):
            criteria_new = mask_new_sum//2
        if criteria_dis+criteria_new>0:
            print('\ntime:'+str(frame_to_time(frame_count_of_alpha))+' '+self.name+"into deep search,app:"+str(mask_new_sum)+",dis:"+str(mask_dis_sum))
            self.deep_compare(frame_list,criteria_new,criteria_dis,frame_count_of_alpha+1) #如果发现新出现或消失，则使用二分法定位改变帧
        self.mask_alpha = mask_omega 
        self.mask_alpha_sum = mask_omega_sum
        return
    
    def allend(self,frame_count): #收尾可能没结束的字幕
        for st in self.startframelist:
            writetimestamp(FPS,st,frame_count,self.fontname,self.defaulttext)
        
#根据范围取mask
def get_mask(type,hsvimg,lowerhsv,upperhsv,kernelsize,bordlowhsv=1,borduphsv=1,previous_hsvimg=1): #在HSV颜色空间判断字幕像素点
    if type == ACTOR.CONTENT_ONLY:
        got_mask = cv.inRange(hsvimg,lowerhsv,upperhsv)
        res = cv.inRange(hsvimg,lowerhsv,upperhsv)
        if kernelsize > 0:
            res = cv.morphologyEx(got_mask, cv.MORPH_OPEN, np.ones((kernelsize,kernelsize),np.uint8)) #OPEN操作，消除噪点
        return res
    if type == ACTOR.BORD:
        bord_mask = cv.morphologyEx(cv.inRange(hsvimg,bordlowhsv,borduphsv), cv.MORPH_OPEN, np.ones((5,5),np.uint8))
        content_mask = cv.inRange(hsvimg,lowerhsv,upperhsv)
        confirmed_mask = cv.bitwise_and(content_mask,cv.morphologyEx(bord_mask, cv.MORPH_CLOSE, ROUND_KERNEL))
        return confirmed_mask
    if type == ACTOR.DIFFERENTIAL:
        signhsv = np.array(hsvimg,np.int16)
        signprevious_hsv = np.array(previous_hsvimg,np.int16)
        minus = np.subtract(signhsv,signprevious_hsv)
        lower_difference = bordlowhsv
        upper_difference = borduphsv
        mask = cv.inRange(minus,lower_difference,upper_difference)
        temp = np.array(mask,np.uint8)
        if cv.countNonZero(temp)>15000:
            return np.zeros((HEIGHT,WIDTH),dtype=np.uint8)
        else:
            bord_mask = cv.morphologyEx(temp, cv.MORPH_OPEN, np.ones((5,5),np.uint8))
            content_mask = cv.inRange(hsvimg,lowerhsv,upperhsv)
            confirmed_mask = cv.bitwise_and(content_mask,cv.morphologyEx(bord_mask, cv.MORPH_CLOSE, ROUND_KERNEL))
            KEY= cv.waitKey(0)   
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
Style: ray字幕,Microsoft YaHei UI,100,&H005D5EEF,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,10,10,220,1
Style: rio字幕,Microsoft YaHei UI,100,&H00DE882B,&H000000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,10,10,220,1
Style: 薄边框注释,Microsoft YaHei UI,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1
Style: 双色,Microsoft YaHei UI,100,&H005F4EE3,&H000000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,8,0,2,10,10,360,1
Style: 边缘模糊注释,宋体,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: ray1通常,Microsoft YaHei UI,80,&H005D5EEF,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,10,1
Style: rio1通常,Microsoft YaHei UI,80,&H00DE882B,&HFF0000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,4,0,2,10,10,10,1
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
        
#向ass中写入时间轴数据
def writetimestamp(FPS,startframe,endframe,fontname,defaulttext):
    with open(ASS_FILENAME,'a',encoding="utf-8") as f:
        f.write("\nDialogue: 0,%s,%s,%s,,0,0,0,,%s"%(frame_to_time(startframe),frame_to_time(endframe),fontname,defaulttext))

#进度条显示        
def progress_bar(frame_count):
    totaltime = clock.tick()
    if os.name == 'nt':
        os.system("cls")
    print('进度：%d%%'%(100*frame_count/TOTAL_FRAMES))
    ctypes.windll.kernel32.SetConsoleTitleW("(%d%%)%s"%(100*frame_count/TOTAL_FRAMES,VIDEO_FILENAME))
    print("已处理帧数： %d"%frame_count)
    print("已处理至：%s"%(frame_to_time(frame_count)))
    print("已用时间 %d秒"%totaltime)
    print("每秒视频处理用时 %.2f秒"%(FPS*totaltime/frame_count))
    time_left = (TOTAL_FRAMES - frame_count)*totaltime/frame_count
    print("预计剩余时间：%d分%d秒"%(time_left/60,time_left%60))
    print("--------") #进度条
    

 
if __name__ == "__main__": 
    #修改终端标题
    ctypes.windll.kernel32.SetConsoleTitleW("omesis字幕轴自动生成")
    SERIES_LENGTH = 16 #每隔16帧进行一次对比，32效果差而且速度并没有提高多少
    if os.name == 'nt':
        os.system("cls")
    global VIDEO_FILENAME,ASS_FILENAME
    filelist = os.listdir() #在当前文件夹中查找扩展名为.mp4的文件
    for filename in filelist:
        if filename[-4:] == '.mp4':
            print("已发现：%s"%filename)
            VIDEO_FILENAME = filename
            break
    else:
        VIDEO_FILENAME = input('请输入视频文件名（含扩展名）：\n') 

    #载入视频
    cap = cv.VideoCapture(VIDEO_FILENAME,cv.CAP_FFMPEG) #打开视频
    print('成功读取视频')
    global FPS,TOTAL_FRAMES,WIDTH,HEIGHT
    FPS = cap.get(cv.CAP_PROP_FPS)                      #帧率
    TOTAL_FRAMES = cap.get(cv.CAP_PROP_FRAME_COUNT)          #总帧数
    WIDTH = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    HEIGHT = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))    

    ASS_FILENAME = "【自动生成】"+VIDEO_FILENAME[:-4]+'.ass'
    initial_ass()
    
    #样式列表，可按需添加
    RAY = ACTOR(name='ray',fontname='ray字幕',defaulttext='【ray说：】',lowh=np.array([173,163,219]),uph=np.array([178,173,230]), \
                kernelsize=5,start_amount=2000,end_amount=1000, type=ACTOR.CONTENT_ONLY)
    RIO = ACTOR(name='rio',fontname='rio字幕',defaulttext='【rio说：】',lowh=np.array([102,192,213]),uph=np.array([106,196,220]), \
                kernelsize=5,start_amount=2000,end_amount=1000, type=ACTOR.CONTENT_ONLY)
    BLACK =ACTOR(name='BLACK',fontname='加厚边框注释',defaulttext=r'{\bord8}【加厚边框注释】',lowh=np.array([0,0,252]),uph=np.array([255,6,255]), \
                kernelsize=5,start_amount=15000,end_amount=12000, type=ACTOR.BORD,\
                bordlowh=np.array([1,5,1]),borduph=np.array([255,255,43]))
    GRAY = ACTOR(name='GRAY',fontname='边缘模糊注释',defaulttext=r'{\blur5}【边缘模糊文字】',lowh=np.array([0,0,252]),uph=np.array([255,4,255]), \
                kernelsize=5,start_amount=5000,end_amount=5000, type=ACTOR.DIFFERENTIAL,\
                bordlowh=np.array([-10,-25,-143]),borduph=np.array([10,7,-49]))
    
    #进度条
    print("----------")
    frame_count = -1
    period_frames = []
    clock = TIME_it()
    
    alpha_frame_count = -1
    
    while(cap.isOpened()):
        ret, img = cap.read()
        if ret is False:#没有帧了    
            break
        frame_count += 1 #成功读帧，帧数+1
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        period_frames.append(hsv)
        if frame_count%SERIES_LENGTH == SERIES_LENGTH-1:
            for actor in ACTOR.actor_list:
                actor.rough_compare(period_frames,alpha_frame_count)
            alpha_frame_count = frame_count
            period_frames = []
            print('|',end='',flush=True)
            if frame_count%(10*SERIES_LENGTH) == SERIES_LENGTH-1:
                progress_bar(frame_count)

    #收尾可能没结束的字幕
    for actor in ACTOR.actor_list:
        actor.allend(frame_count)
        
    #释放资源
    cap.release()
    cv.destroyAllWindows()
    
    print("\n处理完成")
    ctypes.windll.kernel32.SetConsoleTitleW("(处理完成)%s"%(VIDEO_FILENAME))
    input('按Enter结束。。。')
        

