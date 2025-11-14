This is a ros2 package to get the Hololens feed and publish as ros2 topic.

# hololens bridge

This has following nodes.

    1. tf publisher for odom and hololens from the IMU of hololens

    2. si publisher head position and orientation

    3. sm publisher - captured from spatial mapping as just string data

    4. depth publisher - captured longthrow images from HOlolens and its camera info - not correctly rectified yet

    5. depth image to laser scan - convert the above to 2d laser scan

    6. point cloud publisher - converts spatial mapping string into ros2 supported pointcloud2 topic

    7. stereo to laser scan - gets the stereo camera depth feed from the oakd camera running on a raspberry pi through local network. Then this node converts it to a scan topic

    8. point cloud to laser scan - gets a pcd and converts it to a 2d scan

    9. slam toolbox 

To launch run,

```ros2 launch hololens_ros2_bridge hololens_ros2_bridge.launch.py```

# Oakd publisher 

This uses the official depthai_ros_driver to publish the sensors of OAKD camera. Run this ONLY IF THE CAMERA IS CONNECTED TO THIS DEVICE.

```ros2 launch hololens_ros2_bridge oakd.launch.py```

# ROS bag

This plays recorded rosbag along with necessary utilities.

```ros2 launch hololens_ros2_bridge rosbag.launch.py```