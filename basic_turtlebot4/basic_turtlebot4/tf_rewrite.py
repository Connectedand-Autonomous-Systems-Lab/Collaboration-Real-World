import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage

class TfRenameNode(Node):
    def __init__(self):
        super().__init__('tf_rename_node')

        self.sub = self.create_subscription(
            TFMessage,
            '/human/tf',
            self.tf_callback,
            10
        )

        self.pub = self.create_publisher(
            TFMessage,
            '/tf',
            10
        )

    def tf_callback(self, msg):
        new_msg = TFMessage()

        for t in msg.transforms:
            # Modify ONLY odom frame
            if t.header.frame_id == "odom":
                t.header.frame_id = "human_odom"

            if t.child_frame_id == "odom":
                t.child_frame_id = "human_odom"

            new_msg.transforms.append(t)

        self.pub.publish(new_msg)


def main():
    rclpy.init()
    node = TfRenameNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down tf_rewrite node')
    finally:
        node.destroy_node()

if __name__ == '__main__':
    main()