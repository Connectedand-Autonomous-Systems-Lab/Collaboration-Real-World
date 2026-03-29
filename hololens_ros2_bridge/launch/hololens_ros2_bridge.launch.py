from launch import LaunchDescription
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    tf_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='tf_publisher',
        name='tf_publisher',
        output='screen'
    )

    si_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='si_publisher',
        name='si_publisher',
        output='screen'
    )

    si_publisher_new_node = Node(
        package='hololens_ros2_bridge',
        executable='si_publisher_new',
        name='si_publisher_new',
        output='screen'
    )

    sm_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='sm_publisher',
        name='sm_publisher',
        output='screen'
    )

    pointcloud_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='pointcloud_publisher',
        name='pointcloud_publisher',
        output='screen'
    )

    depth_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='depth_publisher',
        name='depth_publisher',
        output='screen'
    )

    depth_camerainfo_parser_node = Node(
        package='hololens_ros2_bridge',
        executable='depth_camerainfo_parser',
        name='depth_camerainfo_parser',
        output='screen'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', 'src/hololens_ros2_bridge/rviz/hololens.rviz', '--ros-args', '--log-level', 'fatal'],
        parameters=[{'use_sim_time': True}]
    )

    pointcloud_to_laserscan_node = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        remappings=[
            ('cloud_in', 'point_cloud2'),
            ('scan', 'scan'),
        ],
        parameters=[{
            'max_height': 2.0,
            'min_height': -0.5
        }],
        output='screen',
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': os.path.join(get_package_share_directory('hololens_ros2_bridge'), 'config', 'mapper_params_online_async.yaml'),
        }.items()
    )   

    depth_image_to_laserscan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        name='depth_image_to_laserscan',
        remappings=[
            ('depth', 'hololens/depth'),
            ('depth_camera_info', 'hololens/depth_cameraInfo'),
        ],  
        parameters=[{
            'output_frame': 'hololens',
        }],
        )
    
    stereo_to_laserscan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        name='depth_image_to_laserscan',
        remappings=[
            ('depth', 'oak/stereo/depth'),
            ('depth_camera_info', 'oak/stereo/camera_info'),
        ],  
        parameters=[{
            'output_frame': 'oak_rgb_camera_optical_frame',
        }],
        )

    hololens_to_oakd_tf = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_pub',
            output='screen',
            # Arguments (positional): x y z qx qy qz qw parent child
            arguments=['0', '0', '0', '0', '0', '0', '1', 'hololens', 'oakd_frame'],
        )
    
    pv_publisher_node = Node(
        package='hololens_ros2_bridge',
        executable='pv_publisher',
        name='pv_publisher',
        output='screen'
    )

    return LaunchDescription([
        tf_publisher_node,
        si_publisher_node,
        # si_publisher_new_node,
        # pv_publisher_node,
        # sm_publisher_node,
        # depth_publisher_node,
        # depth_camerainfo_parser_node,

        # depth_image_to_laserscan_node,
        # pointcloud_publisher_node,
        # stereo_to_laserscan_node,
        # pointcloud_to_laserscan_node,

        rviz_node,
        
        # slam_toolbox,

        hololens_to_oakd_tf,
        
    ])
