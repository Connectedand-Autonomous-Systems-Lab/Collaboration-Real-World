from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    threading_node = Node(
        package='hololens_ros2_bridge',
        executable='thread_publisher',
        name='thread_publisher',
        output='screen'
    )

    return LaunchDescription([
        threading_node,
    ])
