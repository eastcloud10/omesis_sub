#编写于python3.7，使用库numpy,opencv2
import numpy as np
import cv2
import time
import shutil
import ctypes

#修改终端标题
ctypes.windll.kernel32.SetConsoleTitleW("omesis字幕轴自动生成")

EMPTY_ASS=".\\empty.ass"
OUTPUT_ASS=".\\omesis_sub.ass"
VIDEO_FILENAME='video.mp4'

#向ass中写入时间轴数据。样式为ray_sub和rio_sub
def writetimestamp(starttimestring,endtimestring,name='ray'):
    with open(OUTPUT_ASS,'a') as f:
        f.write("Dialogue: 0,0:"+starttimestring+",0:"+endtimestring+","+name+"_sub"+",,0,0,0,,omesis\n")
    
#通过opencv显示图像取色        
#RIO R 52 G 138 B 216
#RAY R 226 G 76 B 93
#通过颜色判断字幕的存在
#颜色空间，每通道上下5
def RIO_count(R,G,B):
    return (R>=49)&(R<=55)&(G>=135)&(G<=141)&(B>=213)&(B<=219)

def RAY_count(R,G,B):
    return (R>=221)&(R<=231)&(G>=71)&(G<=81)&(B>=88)&(B<=98)
    
#字幕（出现/消失）像素判定数，可根据分辨率确定
SUB_START_NUM = 5000
SUB_END_NUM   = 5000

#计时开始
PROGRAM_starttime=time.time() 

#载入视频
cap = cv2.VideoCapture(VIDEO_FILENAME,cv2.CAP_FFMPEG) #打开视频
print('成功读取视频')
FPS=cap.get(cv2.CAP_PROP_FPS)                      #帧率
TOTAL_FRAMES=cap.get(CAP_PROP_FRAME_COUNT)          #总帧数
WIDTH=cap.get(cv2.CAP_PROP_FRAME_WIDTH)
HEIGHT=cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
frame_count=0

#初始化空判定
previous_RAY=np.zeros(1920*1080)
previous_RIO=np.zeros(1920*1080)
RAY_new=np.zeros(1920*1080)
RIO_new=np.zeros(1920*1080)
RAY_dis=np.zeros(1920*1080)
RIO_dis=np.zeros(1920*1080)

#待写入
RAYstarttimelist=[]
RIOstarttimelist=[]

#初始化空ass文件
shutil.copyfile(EMPTY_ASS,OUTPUT_ASS)

#进度条
print("----------")

while(cap.isOpened()):
    ret, img = cap.read()        
    if ret is False:#没有帧了    
        break 
        
    frame_count = frame_count + 1 #成功读帧，帧数+1
    
    #进度条
    if frame_count%60==0:
        print('|',end='',flush=True)
        if frame_count%600==0:
            print('')
        
    #三色空间
    B,G,R=img.transpose(2,0,1).reshape(3,-1)
    current_RIO = RIO_count(R,G,B)
    current_RAY = RAY_count(R,G,B)
    
    #调试
    #cv2.imshow('omesis',img)

    #判定项
    RAY_new=(previous_RAY==False)&(current_RAY==True)
    RIO_new=(previous_RIO==False)&(current_RIO==True)
    RAY_dis=(previous_RAY==True)&(current_RAY==False)
    RIO_dis=(previous_RIO==True)&(current_RIO==False)
    
    #调试
    #print('time:%02d:%05.2f, RIO mask:%d, RAY mask:%d'%(minute,second,np.sum(current_RIO),np.sum(current_RAY)))
    #print('RAY new=%d,RAY dis=%d'%(np.sum(RAY_new),np.sum(RAY_dis)))
    #print('RIO new=%d,RIO dis=%d'%(np.sum(RIO_new),np.sum(RIO_dis)))
    
    #判定起始与终止. 先判终止后判开始避免秒瞬间结束
    #RAY结束
    if (np.sum(RAY_dis)>SUB_END_NUM) & (np.sum(RAY_dis)/(np.sum(previous_RAY)+1) > 0.5):        #超过一半消失则判定为结束
        minute=((frame_count-2)/FPS)/60 #结束帧在前一帧
        second=((frame_count-2)/FPS)%60
        for st in RAYstarttimelist:
            writetimestamp(st,("%02d:%06.3f"%(minute,second+0.01))[0:8],"ray")  #结束时间点向上取整(0.01s)
        RAYstarttimelist=[] #清空列表，待复用
        
    #RIO结束    
    if (np.sum(RIO_dis)>SUB_END_NUM) & (np.sum(RIO_dis)/(np.sum(previous_RIO)+1) > 0.5):
        minute=((frame_count-2)/FPS)/60
        second=((frame_count-2)/FPS)%60
        for st in RIOstarttimelist:
            writetimestamp(st,("%02d:%06.3f"%(minute,second+0.01))[0:8],"rio")
        RIOstarttimelist=[]
    
    #RAY起始
    if (np.sum(RAY_new)>SUB_START_NUM) & (np.sum(RAY_new)/(np.sum(current_RAY)+1) > 0.5):       #超过一半为新出现则判定为新行
        minute=((frame_count-1)/FPS)/60 #起始帧在本帧
        second=((frame_count-1)/FPS)%60
        RAYstarttimelist.append(("%02d:%06.3f"%(minute,second))[0:8])   #起始时间点向下取整(0.01s)
    
    #RIO起始
    if (np.sum(RIO_new)>SUB_START_NUM) & (np.sum(RIO_new)/(np.sum(current_RIO)+1) > 0.5):
        minute=((frame_count-1)/FPS)/60
        second=((frame_count-1)/FPS)%60
        RIOstarttimelist.append(("%02d:%06.3f"%(minute,second))[0:8])    
    
    #处理结束，当前帧 存为 上一帧
    previous_RAY=current_RAY
    previous_RIO=current_RIO
  
    #调试
    #if cv2.waitKey(1) & 0xFF == ord('q'): 
    #    break
    
    #每600帧（约10秒）显示一次进度
    if frame_count%600 == 0:        
        PROGRAM_currenttime=time.time()
        print('进度：%d%%'%(100*frame_count/TOTAL_FRAMES))
        ctypes.windll.kernel32.SetConsoleTitleW("(%d)omesis字幕轴自动生成"%(100*frame_count/TOTAL_FRAMES))
        print("已处理帧数： %d"%frame_count)
        print("已用时间 %d秒"%(PROGRAM_currenttime-PROGRAM_starttime))
        print("每60帧处理用时 %.2f秒"%(60*(PROGRAM_currenttime-PROGRAM_starttime)/frame_count))
        time_left = (TOTAL_FRAMES - frame_count)*(PROGRAM_currenttime-PROGRAM_starttime)/frame_count
        print("预计剩余时间：%d分%d秒"%(time_left/60,time_left%60))
        print("----------") #进度条

#收尾可能没结束的字幕
for st in RAYstarttimelist:
    minute=((frame_count-2)/FPS)/60 #结束帧在前一帧
    second=((frame_count-2)/FPS)%60
    for st in RAYstarttimelist:
        writetimestamp(st,("%02d:%06.3f"%(minute,second+0.01))[0:8],"ray")

for st in RIOstarttimelist:
    minute=((frame_count-2)/FPS)/60
    second=((frame_count-2)/FPS)%60
    for st in RIOstarttimelist:
        writetimestamp(st,("%02d:%06.3f"%(minute,second+0.01))[0:8],"rio")

print("\n处理完成")
ctypes.windll.kernel32.SetConsoleTitleW("(处理完成)omesis字幕轴自动生成")
input('按Enter结束。。。')
    
#释放资源
cap.release()
cv2.destroyAllWindows()

