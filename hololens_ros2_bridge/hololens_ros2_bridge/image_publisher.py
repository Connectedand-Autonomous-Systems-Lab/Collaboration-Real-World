import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np
import time

class SimpleImagePublisher(Node):
    def __init__(self):
        super().__init__('simple_image_publisher')

        # Publisher on topic "image"
        self.publisher_ = self.create_publisher(Image, 'image', 10)
        self.counter = 0    
        # Publish at 10 Hz
        self.timer = self.create_timer(0.05, self.timer_callback)

    def timer_callback(self):
        msg = Image()

        # Image size
        height = 270
        width = 480

        # Fill Image message fields
        msg.height = height
        msg.width = width
        msg.encoding = 'rgb8'      # 3 channels (R,G,B), 8 bits each
        msg.is_bigendian = 0
        msg.step = width * 3       # bytes per row

        # Create a simple green image
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = [0, 255, 0]    # R, G, B

        # print(np.unique(img))
        start_time = time.time()
        msg.data = img.tobytes()
        end_time = time.time()
        
        self.get_logger().info(f'Image conversion to bytes took {end_time - start_time} seconds')

        self.publisher_.publish(msg)
        # self.get_logger().info(f'Published a green image {self.counter} at {time.time()}')
        self.counter += 1


def main(args=None):
    rclpy.init(args=args)
    node = SimpleImagePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
