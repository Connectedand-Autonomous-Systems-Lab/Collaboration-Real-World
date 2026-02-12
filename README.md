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
export ROS_DISCOVERY_SERVER=";127.0.0.1:11888"
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
fastdds discovery -i 1 --udp-address <ip-address_of_middleware_machine> --udp-port 11811
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
