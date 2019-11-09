import numpy as np
import cv2 as cv
def BGR2HSV(*RGB):
    for r,g,b in RGB:
        print(cv.cvtColor(np.uint8([[[b,g,r]]]),cv.COLOR_BGR2HSV))
        
if __name__ == "__main__":
    BGR2HSV((36,36,36),(25,25,25),(26,25,28),(27,32,28),(35,29,22),(30,29,32),(31,29,30),(32,30,31))