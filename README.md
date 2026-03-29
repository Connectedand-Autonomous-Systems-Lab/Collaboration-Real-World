> # SIMULATION
> To simulate the Concord, redirect to this repository
> [Click here to navigate to Simulation repository](https://github.com/Connected-and-Autonomous-Systems-Lab/HumanRobotSim.git)
> <img src="readme_files/collaborative_search_10min_16x_masked.gif" width="80%" />

# Run real world experiment

According to the user study we conducted, we collected the perceptions of the users while they search and acknowledge QR codes around GITC 4th floor, NJIT.

<img src="readme_files/Human_headset4.jpeg" width="30%" />

The following is a speeded instance of the corresponding scan and map generated using a OAKD stereo camera mounted on the headset. This is visualised in Rviz, a standard tool in ROS2.

<img src="readme_files/oakd_slam_on_gitc4_timelapse.gif" width="80%" />



## Requirements

1. ROS2 Humble [Get Started](https://docs.ros.org/en/humble/Installation.html)
2. ROS2 packages (install via `sudo apt install ...`):
   - ros-humble-nav2-bringup
   - ros-humble-slam-toolbox
   - ros-humble-turtlebot3-cartographer
   - ros-humble-ros-tcp-endpoint
   - ros-humble-rviz2
   - ros-humble-tf2-ros
3. Turtlebot4 Standard [Get Started with Turtlebot4 Standard](https://turtlebot.github.io/turtlebot4-user-manual/setup/basic.html)

### Run realworld demonstration

(Under development) This runs an instance of Concord (Human-in-the-loop exploration) at GITC 4th floor, NJIT. Both human and turtlebot4 data are stored in ros2 bags when a Human-in-the-loop exploration is conducted.

```bash
ros2 launch collaborate run_demo.launch.py
``` 

### Run turtlebot4 asynchronously

This runs the turtlebot4 with already saved realworld human data. To lookup what the human data(ros2 bag) contains, refer [Dataset Documentation](readme_files/dataset_README.md)

The following starts the collected human data on GITC 4th floor, NJIT.

```bash
ros2 launch hololens_ros2_bridge collaborate_async.launch.py
```

The following starts the turtlebot4 with navigation. To learn how to get started with Turtlebot4, refer the official documentation. [Get Started with Turtlebot4 Standard](https://turtlebot.github.io/turtlebot4-user-manual/setup/basic.html)

```bash
ros2 launch basic_turtlebot4 slam.launch.py
``` 

The following starts the Concord (Human-in-the-loop exploration for turtlebot)

```bash
ros2 launch collaborate concord.launch.py
```

## Run Turtlebot4 and Human synchronousely (Documentation under development)

Instead of using the userstudy data, if you want to have your own human headset, you will need to follow the additional requirements.

### Additional Requirements for headset

<p align="center">
  <img src="readme_files/human_headset.jpeg" width="30%" />
  <img src="readme_files/human_headset2.jpeg" width="30%" />
  <img src="readme_files/human_headset3.jpeg" width="30%" />
</p>

1. Hololens2 [Product](https://learn.microsoft.com/en-us/hololens/hololens-commercial-features)
2. RaspberryPi 5 [Product](https://www.raspberrypi.com/products/raspberry-pi-5/)
3. OAK-D camera [Product](https://docs.luxonis.com/hardware/products/OAK-D%20Pro)
4. Powerbank capable of delivering AC and DC. [Powerbank we used](https://www.ebay.com/itm/236368640961?chn=ps&norover=1&mkevt=1&mkrid=711-117182-37290-0&mkcid=2&mkscid=101&itemid=236368640961&targetid=2295557532670&device=c&mktype=pla&googleloc=9003544&poi=&campaignid=21388819155&mkgroupid=173029508548&rlsatarget=pla-2295557532670&abcId=9447217&merchantid=114754267&gad_source=1&gad_campaignid=21388819155&gbraid=0AAAAAD_QDh9jPnM_oqFOksZsT_4VFhHVN&gclid=Cj0KCQiAgbnKBhDgARIsAGCDdldxvuLYyBrT5zp3LVymghit18GrSErPeK-NqysLLw58UMCMqx72SDIaArlOEALw_wcB)


### Headset

Every document related to Hololens2 can be found [here](hololens_ros2_bridge/README.md)

Follow these commands to run on the RaspberryPi 5 mounted with OAKD stereo camera.
Clone the following workspace to the RPi5 and build it. 

To discover topics around other terminals in discover server setting, export the settings as instructed [here](https://docs.ros.org/en/humble/Tutorials/Advanced/Discovery-Server/Discovery-Server.html#daemon-s-related-tools)

Terminal 1 (RaspberryPi 5 connected with OAKD stereo camera)
```bash
fastdds discovery -i 1 --udp-address 127.0.0.1 --udp-port 11888
```

Terminal 2 (RaspberryPi 5 connected with OAKD stereo camera)
```bash
cd ~/Documents/dai_ws
source install/setup.bash
export ROS_DISCOVERY_SERVER=";127.0.0.1:11888"  # be careful about the discovery server id. if it is 0; ROS_DISCOVERY_SERVER="<ip-address of TB4>:<port>". If it is 1;  ROS_DISCOVERY_SERVER=";<ip-address of TB4>:<port>" likewise
ros2 launch depthai_ros_driver oak_stereo_minimal.launch.py  # This script is written based on the official depthai_ros_driver repo in a way only the necessary topics are querried from the OAKD camera.
```

Terminal 3 (RaspberryPi 5 connected with OAKD stereo camera)
```bash
cd ~/Documents/dai_ws
source install/setup.bash
export ROS_DISCOVERY_SERVER="<ip-address_of_middleware_machine>:11811;127.0.0.1:11888"
export FASTRTPS_DEFAULT_PROFILES_FILE=super_client_configuration_file.xml    #check the remote server prefix, udp address, port in this xml file
ros2 launch depthimage_to_laserscan depthimage_to_laserscan-launch.py
```

Then from the middleware machine run the following

Terminal 1 (Middleware machine)
```bash
fastdds discovery -i 0 --udp-address <ip-address_of_middleware_machine> --udp-port 11811
```

Terminal 2 (Middleware machine)
```bash
export ROS_DISCOVERY_SERVER="<ip-address_of_middleware_machine>:11811"
export FASTRTPS_DEFAULT_PROFILES_FILE=super_client_configuration_file.xml    #check the remote server prefix, udp address (should be the one, you want to listen to), port in this xml file
```

You should see the /scan topic extracted from the stereo camera in Terminal 2. Restart ros daemon if needed.

```bash
ros2 daemon stop; ros2 daemon start
```


### Running Turtlebot4

Use the official guide to setup the TB4 to host and run in a discovery server [here](https://turtlebot.github.io/turtlebot4-user-manual/setup/discovery_server.html). This is to decrease the packet traffic. 

(Experimental point->)But for the Middleware machine, do not export the discovery server settings to bashrc since it will applied to all the terminals.

Terminal 1 (Middleware machine)
```bash
export ROS_DISCOVERY_SERVER="<ip-address of TB4>:<port>"  # be careful about the discovery server id. if it is 0; ROS_DISCOVERY_SERVER="<ip-address of TB4>:<port>". If it is 1;  ROS_DISCOVERY_SERVER=";<ip-address of TB4>:<port>" likewise
cd hololens_ros2_bridge
source install/setup.bash
ros2 launch basic_turtlebot4 discovery_server.launch.py
```

Terminal 2 (Middleware machine)
```bash
export ROS_DISCOVERY_SERVER="<ip-address of TB4>:<port>"
export FASTRTPS_DEFAULT_PROFILES_FILE=super_client_configuration_file.xml    #check the remote server prefix, udp address (should be the one, you want to listen to), port in this xml file
ros2 launch turtlebot4_navigation nav2.launch.py namespace:=robot_0 params_file:=/home/mayooran/Documents/iros/src/DRL-exploration/unity_end/human_robot_pkg/config/nav2_real_world.yaml use_sim_time:=true
```

Terminal 3 (Middleware machine)
```bash
export ROS_DISCOVERY_SERVER="<ip-address of TB4>:<port>"
export FASTRTPS_DEFAULT_PROFILES_FILE=super_client_configuration_file.xml    #check the remote server prefix, udp address (should be the one, you want to listen to), port in this xml file
# Make sure you do 2D pose estimate before you do this step! otherwise this will throw goal was rejected!
ros2 action send_goal /robot_0/navigate_to_pose nav2_msgs/action/NavigateToPose "pose: {header: {frame_id: map}, pose: {position: {x: -0.84, y: -0.28, z: 0.0}, orientation:{x: 0.0, y: 0.0, z: 0, w: 1.0000000}}}" # Try this just to check whether the navigate to pose is working
```


## Known Errors

1. When you give navigate to pose command for Turtlebot4, you might get the following error.

```bash
ros2 action send_goal /robot_0/navigate_to_pose nav2_msgs/action/NavigateToPose "pose: {header: {frame_id: map}, pose: {position: {x: -0.84, y: -0.28, z: 0.0}, orientation:{x: 0.0, y: 0.0, z: 0, w: 1.0000000}}}"
Waiting for an action server to become available...
Sending goal:
     pose:
  header:
    stamp:
      sec: 0
      nanosec: 0
    frame_id: map
  pose:
    position:
      x: -0.84
      y: -0.28
      z: 0.0
    orientation:
      x: 0.0
      y: 0.0
      z: 0.0
      w: 1.0
behavior_tree: ''

Goal was rejected.
```

First, check whether your nav2 stack is launched properly. 

```bash
[bt_navigator-5] [ERROR] [1771605764.906961073] [robot_0.bt_navigator]: Exception when loading BT: Action server compute_path_through_poses not available
[bt_navigator-5] [ERROR] [1771605764.907007294] [robot_0.bt_navigator]: Error loading XML file: /opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml
[lifecycle_manager-8] [ERROR] [1771605764.907243894] [robot_0.lifecycle_manager_navigation]: Failed to change state for node: bt_navigator
[lifecycle_manager-8] [ERROR] [1771605764.907285971] [robot_0.lifecycle_manager_navigation]: Failed to bring up all requested nodes. Aborting bringup.
```
The above error messages indicate that the nav2 is not launched properly.

2. Use an easier behavior tree for nav2 if the recovery behaviors give trouble.

example:
/share/nav2_bt_navigator/behavior_trees/navigate_w_replanning_only_if_goal_is_updated.xml

3. nav2 will may reject the goal when a navigate to pose is given.

```bash
[bt_navigator-5] [WARN] [1771354216.964211362] [robot_0.bt_navigator.rclcpp_action]: Failed to send goal response 2884ae599bd24b70a1dcfd877ea9d5d4 (timeout): client will not receive response, at ./src/rmw_response.cpp:154, at ./src/rcl/service.c:314
```

4. The action client gets timeout out waiting for the action server to respond.

```bash
[bt_navigator-5] [WARN] [1771455420.015176679] [robot_0.bt_navigator_navigate_to_pose_rclcpp_node]: Timed out while waiting for action server to acknowledge goal request for compute_path_to_pose
```
Setting the flag use_sim_time=true with navigation thread would fix this. 
But worked instance would look like this [warp instance](https://app.warp.dev/block/L67SiwinRyJJ6LDhtosR4Z)

5.

```bash
[bt_navigator-5] [ERROR] [1772117416.149270458] [robot_0.bt_navigator_navigate_through_poses_rclcpp_node]: "compute_path_through_poses" action server not available after waiting for 1.00s
[bt_navigator-5] [ERROR] [1772117416.180793887] [robot_0.bt_navigator]: Exception when loading BT: Action server compute_path_through_poses not available
[bt_navigator-5] [ERROR] [1772117416.180857119] [robot_0.bt_navigator]: Error loading XML file: /opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml
[lifecycle_manager-8] [ERROR] [1772117416.181165815] [robot_0.lifecycle_manager_navigation]: Failed to change state for node: bt_navigator
[lifecycle_manager-8] [ERROR] [1772117416.181214508] [robot_0.lifecycle_manager_navigation]: Failed to bring up all requested nodes. Aborting bringup.
```

If any of these happens, the nav2 stack is not properly intitated. Try restarting the TB.
```bash
sudo reboot now
```

6. 

```bash
[controller_server-1] [WARN] [1733850699.044709052] [sheldon.controller_server.rclcpp]: failed to send response to /sheldon/controller_server/change_state (timeout): client will not receive response, at ./src/rmw_response.cpp:154, at ./src/rcl/service.c:314
```

