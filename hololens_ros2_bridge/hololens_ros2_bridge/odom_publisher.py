import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformListener, Buffer, LookupException
from geometry_msgs.msg import TransformStamped
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import tf2_ros


class OdomPublisherNode(Node):
    def __init__(self):
        super().__init__('odom_publisher_node')

        # QoS setup
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Publishers
        # self.robot_pub = self.create_publisher(Odometry, '/odom', qos_profile)
        self.human_pub = self.create_publisher(Odometry, '/odom', qos_profile)

        # TF listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Timer
        self.timer = self.create_timer(0.2, self.timer_callback)  # 1 Hz

        self.get_logger().info("OdomPublisherNode started. Publishing robot and human odometry...")

    def timer_callback(self):
        # self.publish_pose('odom', 'Robot', self.robot_pub, '/odom')
        self.publish_pose('odom', 'hololens', self.human_pub, '/odom')

    def publish_pose(self, parent_frame, child_frame, publisher, topic_name):
        try:
            transform: TransformStamped = self.tf_buffer.lookup_transform(
                parent_frame,
                child_frame,
                rclpy.time.Time()
            )

            odometry = Odometry()
            odometry.header = transform.header
            odometry.child_frame_id = child_frame
            odometry.pose.pose.position.x = transform.transform.translation.x
            odometry.pose.pose.position.y = transform.transform.translation.y
            odometry.pose.pose.position.z = transform.transform.translation.z
            odometry.pose.pose.orientation = transform.transform.rotation 
            publisher.publish(odometry)

            self.get_logger().debug(f"Published {child_frame} pose to {topic_name}")

        except LookupException:
            self.get_logger().warn(f"TF lookup failed for {child_frame}. Waiting for TF...")



def main(args=None):
    rclpy.init(args=args)
    node = OdomPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
