import json

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import String
import numpy as np


class DepthCameraInfoParser(Node):
    def __init__(self):
        super().__init__('depth_camerainfo_parser')
        self.publisher_ = self.create_publisher(CameraInfo, 'hololens/depth_camerainfo', 10)
        self.create_subscription(String, 'hololens/depth_cameraInfo_dummy', self._camera_info_cb, 10)

    def _camera_info_cb(self, msg: String):
        try:
            payload = json.loads(msg.data)
            camera_info_msg = self._build_camera_info(payload)
        except Exception as err:
            self.get_logger().warn(f'Failed to parse /hololens/depth_cameraInfo_dummy: {err}')
            return

        if camera_info_msg is None:
            self.get_logger().warn('Failed to build CameraInfo message from dummy data')
            return
        self.publisher_.publish(camera_info_msg)

    def _build_camera_info(self, payload):
        width = payload.get("Width")
        height = payload.get("Height")

        d = [0.0] * 5
        intrinsics = np.array(payload.get("intrinsics")).T
        p = intrinsics[:3, :4].flatten().tolist()
        camera_info = CameraInfo()
        camera_info.header.stamp = self.get_clock().now().to_msg()
        camera_info.header.frame_id = "hololens"
        camera_info.width = width
        camera_info.height = height
        camera_info.distortion_model = "plumb_bob"
        camera_info.d = [float(v) for v in d]
        # camera_info.k = self._get_array(payload, ["K", "k"])
        # camera_info.r = self._get_array(payload, ["R", "r"])
        camera_info.p = p
        return camera_info

    def _get_int(self, payload, keys):
        for key in keys:
            if key in payload:
                return int(payload[key])
        return None

    def _get_array(self, payload, keys):
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
        return None

    def _mat_to_flat(self, matrix, rows, cols):
        if matrix is None:
            return None
        arr = np.array(matrix, dtype=float)
        if arr.size == 0:
            return None
        if arr.size == rows * cols:
            arr = arr.reshape((rows, cols))
        if arr.shape == (rows, cols):
            return arr.flatten().tolist()
        if arr.shape == (rows, cols - 1):
            return np.hstack((arr, np.zeros((rows, 1)))).flatten().tolist()
        if arr.shape == (rows + 1, cols) and np.allclose(arr[rows, :], 0):
            return arr[:rows, :cols].flatten().tolist()
        return None


def main(args=None):
    rclpy.init(args=args)
    node = DepthCameraInfoParser()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
