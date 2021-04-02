'''
统计图片中的像素值分布
'''

import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
img_name = '5s.bmp'
#previous_img_name = 'white.bmp'
img = cv.imread(img_name,cv.IMREAD_UNCHANGED)
#previous_img = cv.imread(previous_img_name,cv.IMREAD_UNCHANGED)

intervals=[]
for i in range(512):
    intervals.append(i-255.5)



B,G,R =img.reshape((-1,3)).transpose((1,0))
plt.hist(R,bins=intervals)
plt.title(img_name+"-R")
plt.show()
plt.hist(G,bins=intervals)
plt.title(img_name+"-G")
plt.show()
plt.hist(B,bins=intervals)
plt.title(img_name+"-B")
plt.show()

