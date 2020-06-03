'''
统计图片中的像素值分布
'''

import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
img_name = 'bat.png'
#previous_img_name = 'white.bmp'
img = cv.imread(img_name,cv.IMREAD_UNCHANGED)
#previous_img = cv.imread(previous_img_name,cv.IMREAD_UNCHANGED)

hsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)

'''
previous_hsv = cv.cvtColor(previous_img,cv.COLOR_BGR2HSV)

signhsv = np.array(hsv,np.int16)
signprevious_hsv = np.array(previous_hsv,np.int16)
minus = np.subtract(signhsv,signprevious_hsv)
'''

H,S,V = hsv.reshape((-1,3)).transpose((1,0))
intervals=[]
for i in range(512):
    intervals.append(i-255.5)

"""
B,G,R =img.reshape((-1,3)).transpose((1,0))
plt.hist(R,bins=intervals)
plt.title(img_name+"-H")
plt.show()
plt.hist(G,bins=intervals)
plt.title(img_name+"-S")
plt.show()
plt.hist(B,bins=intervals)
plt.title(img_name+"-V")
plt.show()
"""
plt.hist(H,bins=intervals)
plt.title(img_name+"-H")
plt.show()
plt.hist(S,bins=intervals)
plt.title(img_name+"-S")
plt.show()
plt.hist(V,bins=intervals)
plt.title(img_name+"-V")
plt.show()