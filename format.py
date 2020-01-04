import pysubs2
import os

filelist = os.listdir() #在当前文件夹中查找扩展名为.mp4的文件
for filename in filelist:
    if filename[-4:] == '.ass' and filename [:6] != "【自动生成】":
        print("已发现：%s"%filename)
        ASS_FILENAME = filename
        break
else:
    VIDEO_FILENAME = input('请输入视频文件名（含扩展名）：\n') 

count = 0
subs = pysubs2.load(ASS_FILENAME, encoding="utf-8")
for line in subs:
    if line.text[:4]=="ray：":
        line.style = "ray1通常"
        line.text = line.text[4:]
    elif line.text[:4]=="rio：":
        line.style = "rio1通常"
        line.text = line.text[4:]
    line.text = line.text[1:-1]      
            
subs.save('ass_'+ASS_FILENAME, encoding="utf-8")