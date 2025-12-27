from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction

def generate_launch_description():

    package_name = 'human_robot_pkg'
    package_dir = get_package_share_directory(package_name)
    bringup_dir = get_package_share_directory('nav2_bringup')


    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('turtlebot4_navigation'),
                'launch',
                'slam.launch.py'
            ])
        ])
        # launch_arguments={
        #     'use_sim_time': 'true',
        #     'slam_params_file': os.path.join(get_package_share_directory('basic_turtlebot4'), 'config', 'tb.yaml'),
        # }.items()
    )

    # tf_relay = Node(
    #     package="tf_relay",
    #     executable="relay",
    #     name="relay"        
    # )

    tf_relay = Node(
        package='tf_relay',
        executable='relay',
        name='tf_relay_tb',
        arguments=['tb', '1'],  # same as: ros2 run tf_relay relay 'tb' 1
        output='screen',
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('turtlebot4_navigation'),
                'launch',
                'nav2.launch.py'
            ])
        ])
    )


    rviz2 = ExecuteProcess(
        cmd=['rviz2', '-d','/home/mayooran/Documents/hololens_ros2_bridge/src/basic_turtlebot4/rviz2/basic_setup.rviz'],
        output='screen'
    )

    frontier_publisher = Node(
        package='human_robot_pkg',
        executable='frontier_publisher',
        output='screen',
        parameters=[{'use_sim_time':True}]
    )

    # ros2 launch nav2_bringup navigation_launch.py params_file:=/home/mayooran/Documents/iros/src/DRL-exploration/unity_end/human_robot_pkg/config/nav2_params.yaml

    navigation_tb3_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'navigation.launch.py')
        ),
        launch_arguments={'namespace': 'tb_0',
                          'use_namespace': 'True',
                          'use_sim_time': 'True',
                        #   'params_file': os.path.join(bringup_dir, 'params', 'nav2_params.yaml'),
                          'params_file': os.path.join(get_package_share_directory('human_robot_pkg'), 'config', 'tb3_0_nav2_params.yaml'),
                        #   'autostart': 'True',
                        #   'use_composition': 'True',
                        #   'use_respawn': 'False',
                        #   'container_name': 'nav2_container'
                          }.items())

    nav2_nodes = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'nav2_nodes.launch.py')),
        launch_arguments={
                          'params_file': os.path.join(get_package_share_directory('human_robot_pkg'), 'config', 'tb3_0_nav2_params.yaml')}.items())
    

    nav2_bringup_tb3_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('nav2_bringup'), 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
                          'namespace': 'robot1',
                          'use_namespace': 'True',
                          'use_sim_time': 'True',
                          'slam': 'True',
                          'map': os.path.join(bringup_dir, 'maps', 'turtlebot3_world.yaml') ,
                        #   'params_file': os.path.join(get_package_share_directory('human_robot_pkg'), 'config', 'tb3_0_nav2_params.yaml'),
                          'params_file': os.path.join(bringup_dir, 'params', 'nav2_multirobot_params_all.yaml'),
                          'autostart': 'True',
                          'use_composition': 'True',
                          'use_respawn': 'False',
                          'container_name': 'nav2_container'}.items())
    
    nav2_bringup_tb3_0_pushed = GroupAction(
        actions=[
            PushRosNamespace('tb3_0'),
            nav2_bringup_tb3_0,
        ]
    )

    custom_nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
                          'namespace': 'tb3_0',
                          'use_namespace': 'True',
                          'use_sim_time': 'True',
                          'slam': 'True',
                          'map': os.path.join(bringup_dir, 'maps', 'turtlebot3_world.yaml'),
                        #   'params_file': os.path.join(get_package_share_directory('human_robot_pkg'), 'config', 'tb3_0_nav2_params.yaml'),
                          'autostart': 'True',
                          'use_composition': 'True',
                          'use_respawn': 'False'}.items())

    cartographer_tb3_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('turtlebot3_cartographer'), 'launch', 'cartographer.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            # 'cartographer_config_dir': '/home/mayooran/Documents/DRL-Robot-Navigation-ROS2/src/drl_exploration/unity_end/human_robot_pkg/config'
            # 'slam_params_file': '/home/mayooran/Documents/human_robot_exploration_ws/src/human_robot_pkg/config/tb3_0.yaml',
            'namespace':'tb3_0'
        }.items()
    )

    slam_toolbox_human = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'namespace':'human'
        }.items()
    )

    slam_toolbox_tb3_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'namespace':''
        }.items()
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'slam_params_file': os.path.join(get_package_share_directory('human_robot_pkg'), 'config', 'robot.yaml'),
        }.items()
    )   

    slam_toolbox_altered_map = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join( os.path.join(get_package_share_directory('human_robot_pkg'), 'launch', 'slam_altered_map.launch.py')
        )
    )   )

    human_map_to_map = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments = ['--x', '0', '--y', '0', '--z', '1', '--yaw', '0', '--pitch', '0', '--roll', '0', '--frame-id', 'merged_map', '--child-frame-id', 'human/map']
        )

    tb3_0_map_to_map = Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments = ['--x', '0', '--y', '0', '--z', '1', '--yaw', '0', '--pitch', '0', '--roll', '0', '--frame-id', 'merged_map', '--child-frame-id', 'map']
        )

    map_merge = Node(
            package='human_robot_pkg',
            executable='map_merge_node'
            )

    
    params = Node(
            package='human_robot_pkg',
            executable='param_loader'
           )
    
    simple_navigator = Node(
        package="human_robot_pkg",
        executable="simple_navigator"
    )
    
    human_bag = ExecuteProcess(
            cmd=['ros2', 'bag', 'play', '/media/2TB/Collaborative_user_study/Akhita/Easy/rosbag2_2025_12_01-16_09_23', ],
            output='screen'
        )
    
    odom_publisher = Node(
        package="human_robot_pkg",
        executable="odom_publisher"
    )

    scan_limiter = Node(
        package="human_robot_pkg",
        executable="scan_limiter"
    )

    map_logger = Node(
        package="human_robot_pkg",
        executable="map_logger"
    )


    return LaunchDescription([
        GroupAction([
            PushRosNamespace('tb_0/'),
            # SetRemap(src='/tf', dst='/tb/tf'),
            # SetRemap(src='/tf_static', dst='/tb/tf_static'),
            slam_launch,
            # nav2
        ]),

        # slam_launch,
        # nav2,
        rviz2,
        tf_relay
        # depth_image_to_laserscan_node
    ])
