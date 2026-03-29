import numpy as np
import cv2

# image = cv2.imread("src/hololens_ros2_bridge/rosbag/hl_depth_calibration/frame_1773259722_547770150_0.png")
# image = cv2.imread("frame_1773259722_547770150_0.png")
image = cv2.imread("/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/rosbag/hl_depth_calibration/oakd_stereo_image_raw.png")

print(image.shape)
print(image.dtype)
print(image.min(), image.max())
print(np.unique(image))
cv2.imshow("Image", image/np.max(image))
cv2.waitKey(0)