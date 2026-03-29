import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
from sensor_msgs.msg import Image, CameraInfo
import numpy as np
from cv_bridge import CvBridge
from scipy.optimize import least_squares
from pynput import keyboard
import cv2

import sys
sys.path.append('/home/mayooran/Documents/project_hl2ss/codes')
import hl2ss
from colorama import Fore, Style

# Replace with actual client
# from tools.sample_integrator_pv import depth_client
# from tools.sample_simultaneous_ahat_lt import depth_client

def on_press(key):
    global enable
    enable = key != keyboard.Key.esc

    return enable

class DepthPublisher(Node):
    def __init__(self):
        super().__init__('depth_publisher')
        self.depth_publisher_ = self.create_publisher(Image, 'hololens/depth', 10)
        self.depth_cameraInfo_publisher_ = self.create_publisher(CameraInfo, 'hololens/depth_cameraInfo', 10)
        self.dummy_cameraInfo_publisher_ = self.create_publisher(String, 'hololens/depth_cameraInfo_dummy', 10)
        self.counter = 0
        self.bridge = CvBridge()
        mode = hl2ss.StreamMode.MODE_1
        png_filter = hl2ss.PngFilterMode.Paeth
        host = "10.196.109.211"

        global enable
        enable = True
        data = hl2ss.download_calibration_rm_depth_longthrow(host,  hl2ss.StreamPort.RM_DEPTH_LONGTHROW)
        self.camera_info = {
            "Width": int(data.undistort_map.shape[1]),
            "Height": int(data.undistort_map.shape[0]),
            "uv2xy_shape": list(data.uv2xy.shape),
            "extrinsics": data.extrinsics.tolist(),
            "scale": float(data.scale),
            "undistort_map_shape": list(data.undistort_map.shape),
            "intrinsics": data.intrinsics.tolist(),
            "undistort_map": data.undistort_map.tolist(),
        }

        # file = open("/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/rosbag/hl_depth_calibration_data.json", "w")
        # json.dump(self.camera_info, file, indent=4)
        # file.close()

        try:
            self.client = hl2ss.rx_decoded_rm_depth_longthrow(host, hl2ss.StreamPort.RM_DEPTH_LONGTHROW, hl2ss.ChunkSize.RM_DEPTH_LONGTHROW, mode, png_filter)
            self.client.open()
            self.get_logger().info("HL2 Depth client connected successfully.")
        except Exception as e:
            print(Fore.RED,f'HL not connected : {e}')
            return

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        self.frame_num = 0

        # time.sleep(3)  # Allow client to initialize
        self.create_timer(0.05, self.publish_depth)
        # self.create_timer(1.0, self.publish_camera_info)
        self.create_timer(1.0, self.publish_dummy_camera_info)
        # self.publish_depth()

    def publish_dummy_camera_info(self):
        camera_info_dummy = String()
        camera_info_dummy.data = json.dumps(self.camera_info)
        # camera_info_dummy.data = "Dummy camera info for depth stream"
        self.dummy_cameraInfo_publisher_.publish(camera_info_dummy)

    def publish_depth(self):
        try:
            data = self.client.get_next_packet()  # for depth
            # cv2.imshow('Depth', data.payload.depth / np.max(data.payload.depth)) # Normalized for visibility
            # cv2.waitKey(1)
            HL_connected = True
        
            self.frame_num += 1
            # try:
            msg = Image()
            depth = data.payload.depth
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "hololens"
            msg.height = depth.shape[0]
            msg.width = depth.shape[1]
            msg.encoding = "16UC1"  # Assuming depth is in unsigned 16-bit
            msg.is_bigendian = False
            msg.step = msg.width * depth.dtype.itemsize
            # msg.data = self.bridge.cv2_to_imgmsg(depth, encoding="passthrough").data
            msg.data = depth

            self.depth_publisher_.publish(msg)
            self.get_logger().debug(f"Published depth frame {self.counter}")
            self.counter += 1


        except Exception as e:
            # print(Fore.RED,'#',end='', flush=True)
            print(Fore.RED, f'HL not connected: {e}')
            HL_connected = False
            pass

    def publish_camera_info(self):
        try:
            publish_empty_camera_info = True
            if publish_empty_camera_info:
                camera_info_msg = CameraInfo()
                camera_info_msg.header.stamp = self.get_clock().now().to_msg()
                camera_info_msg.header.frame_id = "hololens"
                camera_info_msg.width = self.client.undistort_map.shape[1]
                camera_info_msg.height = self.client.undistort_map.shape[0]
                camera_info_msg.k = self.client.intrinsics.T[:3,:3].T.flatten().tolist()
                camera_info_msg.d = [0.0] * 5  # Assuming no distortion
                camera_info_msg.r = np.eye(3).flatten().tolist()
                camera_info_msg.p = self.client.intrinsics.T[:3,:4].flatten().tolist()
                camera_info_msg.distortion_model = "plumb_bob"
                self.depth_cameraInfo_publisher_.publish(camera_info_msg)
                return
            
            camera_info_msg = CameraInfo()
            # camera_info_msg.width = self.client.calibration_ht.undistort_map.shape[1]
            # camera_info_msg.height = self.client.calibration_ht.undistort_map.shape[0]

            camera_info_msg.width = self.client.undistort_map.shape[1]
            camera_info_msg.height = self.client.undistort_map.shape[0]
        
            camera_info_msg.k = self.client.intrinsics.T[:3,:3].T.flatten().tolist()
            # camera_info_msg.k = self.client.calibration_ht.intrinsics.T[:3,:3].flatten().tolist()
            # camera_info_msg.k = np.eye(3).flatten().tolist()
            camera_info_msg.d = [0.0] * 5  # Assuming no distortion
            camera_info_msg.r = np.eye(3).flatten().tolist()
            camera_info_msg.p = self.client.intrinsics.T[:3,:4].flatten().tolist()
            # camera_info_msg.p = np.hstack((self.client.calibration_ht.intrinsics.T[:3,:3], np.zeros((3,1)))).flatten().tolist()
            # camera_info_msg.p = np.hstack((np.eye(3), np.zeros((3,1)))).flatten().tolist()
            camera_info_msg.header.stamp = self.get_clock().now().to_msg()
            camera_info_msg.header.frame_id = "hololens"
            camera_info_msg.distortion_model = "plumb_bob"
            # camera_info_msg.d = self.find_distortion_coefficients()
            # camera_info_msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]  # Assuming no distortion
            self.depth_cameraInfo_publisher_.publish(camera_info_msg)

        except Exception as e:
            self.get_logger().warn(f"Camera info publish failed: {e}", throttle_duration_sec=1, once=True)

    def stop(self):
        self.client.end_thread()

    def find_distortion_coefficients(self):
        def normalize(K, pts_pix):
            # pts_pix: (N,2) pixels -> (N,2) normalized
            Kinv = np.linalg.inv(K)
            pts_h = np.c_[pts_pix, np.ones(len(pts_pix))]
            n = (Kinv @ pts_h.T).T
            return n[:, :2] / n[:, 2:3]

        def distort_points(xy, k1,k2,p1,p2,k3):
            x, y = xy[:,0], xy[:,1]
            r2 = x*x + y*y
            radial = 1.0 + k1*r2 + k2*r2*r2 + k3*r2*r2*r2
            x_tan = 2*p1*x*y + p2*(r2 + 2*x*x)
            y_tan = p1*(r2 + 2*y*y) + 2*p2*x*y
            xd = x*radial + x_tan
            yd = y*radial + y_tan
            return np.stack([xd, yd], axis=1)

        def fit_distortion(map_xy, K, newK, sample_step=8, robust=True):
            """
            map_xy: (H,W,2) float32/float64 mapping from rectified pixel (x',y') to original distorted pixel (x,y)
            K:     original camera matrix (3x3)
            newK:  rectified camera matrix (3x3) used to build the map
            """
            H, W, _ = map_xy.shape

            # 1) Build a grid of rectified pixel coords (destination)
            xs, ys = np.meshgrid(np.arange(W), np.arange(H))
            dst_pix = np.stack([xs, ys], axis=-1)[::sample_step, ::sample_step].reshape(-1, 2)

            # 2) Source distorted pixel coords from the map (same samples)
            src_pix = map_xy[::sample_step, ::sample_step, :].reshape(-1, 2)

            # 3) Convert to normalized coords
            und_norm = normalize(newK, dst_pix)   # (x, y)
            dis_norm = normalize(K, src_pix)      # (xd, yd)

            # 4) Optimize k's so that distort(und_norm) ~= dis_norm
            def resid(params):
                k1,k2,p1,p2,k3 = params
                pred = distort_points(und_norm, k1,k2,p1,p2,k3)
                r = (pred - dis_norm).ravel()
                return r

            x0 = np.array([0.0, 0.0, 0.0, 0.0, 0.0])  # reasonable start
            kwargs = dict(method="trf", max_nfev=2000)
            if robust:
                kwargs.update(loss="soft_l1", f_scale=1.0)

            sol = least_squares(resid, x0, **kwargs)
            k1,k2,p1,p2,k3 = sol.x
            return {"k1":k1, "k2":k2, "p1":p1, "p2":p2, "k3":k3, "success":sol.success, "cost":sol.cost}


        # map_xy = your HxWx2 undistort map (float32)
        # K = original camera matrix used for the distorted image (3x3)
        # newK = the rectified camera matrix used when you generated the map (often same as K)

        map_xy = self.client.undistort_map
        K = self.client.intrinsics.T[:3,:3]
        newK = K.copy()  # assuming the same intrinsics were used for rectification

        res = fit_distortion(map_xy, K, newK, sample_step=8)
        coefficients = [res["k1"], res["k2"], res["p1"], res["p2"], res["k3"]]
        return coefficients

def main(args=None):
    rclpy.init(args=args)
    node = DepthPublisher()
    rclpy.spin(node)
    node.stop()
    node.destroy_node()
    rclpy.shutdown()
