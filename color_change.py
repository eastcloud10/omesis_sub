"""
将RGB值转换为HSV值
"""

import numpy as np
import cv2 as cv
def BGR2HSV(*RGB):
    for r,g,b in RGB:
        print(cv.cvtColor(np.uint8([[[b,g,r]]]),cv.COLOR_BGR2HSV))
        
if __name__ == "__main__":
    BGR2HSV((44,178,54),(255,107,57))
    input()