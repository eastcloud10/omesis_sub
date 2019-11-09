import numpy as np
import cv2 as cv
def BGR2HSV(*RGB):
    for r,g,b in RGB:
        print(cv.cvtColor(np.uint8([[[b,g,r]]]),cv.COLOR_BGR2HSV))
        
if __name__ == "__main__":
    BGR2HSV((108,108,103),(119,112,110),(105,105,105),(100,100,100),(122,122,122),(115,120,119),(122,119,123))