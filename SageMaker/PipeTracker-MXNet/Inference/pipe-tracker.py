import mxnet as mx
from mxnet import image
from gluoncv.data.transforms.presets.segmentation import test_transform
import gluoncv
from matplotlib import pyplot as plt
import cv2
import numpy as np

class PipeTracker:
    def __init__(self):
        self.ctx = mx.cpu()
        self.model = gluoncv.model_zoo.DeepLabV3(nclass=2, backbone='resnet50',ctx=self.ctx)
        self.model.load_parameters('model/model_algo-1',ctx=self.ctx)

    def collapse_contours(self, contours):
        contours = np.vstack(contours)
        contours = contours.squeeze()
        return contours
    
    def get_rough_contour(self, image):
        """Return rough contour of character.
        image: Grayscale image.
        """
        img = image.copy()
        # Linux
        # contours, h = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Windows
        im2, contours, h = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = self.collapse_contours(contours)
        return contour
    
    def draw_contour(self, image, contour, colors=(255, 255, 255)):
        for p in contour:
            cv2.circle(image, tuple(p), 1, colors, 2)

    
    def process_frame(self, frame):
        # cropped based on 240
        frame = cv2.resize(frm,(224,224))
        img = mx.nd.array(frame)
        img = test_transform(img, ctx=self.ctx)
        img = img.astype('float32')
        output = self.model.predict(img)

        # argx = mx.nd.argmax(output, 1)
        # argx = np.argmax(output, axis=1)
        argx = mx.nd.topk(output,1)

        predict = mx.nd.squeeze(argx).asnumpy()
        predict = predict.astype(np.uint8)
        dst = cv2.fastNlMeansDenoising(predict,None,10,7,21)
        ret, mask = cv2.threshold(dst, .5, 255, cv2.THRESH_BINARY)
        if cv2.countNonZero(mask) == 0:
            return mask
        contourMask  = self.get_rough_contour(mask)
        
        # Centroid
        M = cv2.moments(contourMask)
        if M['m00'] != 0:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            cv2.circle(frame, (cx,cy), 0,(0,255,255), 5)
        
        # rectangle
        rect = cv2.minAreaRect(contourMask)
        box = cv2.boxPoints(rect)
        box = np.int0(box)
        cv2.drawContours(frame,[box],0,(255,255,255),1)
        
        # Line
        rows,cols = mask.shape[:2]
        [vx,vy,x,y] = cv2.fitLine(contourMask, cv2.DIST_L2,0,0.01,0.01)
        lefty = int((-x*vy/vx) + y)
        righty = int(((cols-x)*vy/vx)+y)
        img = cv2.line(frame,(cols-1,righty),(0,lefty),(255,255,255),1)

        return frame


pipeTracker = PipeTracker()

frame_index = 0
fileName = "videos/027_Centre_2TL-Zone 3_2017-09-03_02-55-06_4.mp4"
cap = cv2.VideoCapture(fileName)
success, frm = cap.read()
while(success):
    frame_index +=1
    if (frame_index % 35 != 0):
        success, frm = cap.read()
        continue
    processed_frame = pipeTracker.process_frame(frm)
    if len(processed_frame.shape) == 2:
        continue
    cv2.imshow("result", processed_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    success, frm = cap.read()

cap.release()
cv2.destroyAllWindows()