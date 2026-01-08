# Dataset description

Collaboration user study dataset has the following structure:

```text
root/
    subject1/
        Easy/
            HL2SS/
                data_si.csv
                data_pv.csv
                data_combined.csv
                pv_images/
            rosbag/
                yaml file
                db3
        Hard/
            HL2SS/
                data_si.csv
                data_pv.csv
                data_combined.csv
                pv_images/
            rosbag/
                yaml file
                db3
        subject1.rar
    subject2/
    ..
    ..
```

## Overview

- Subject data is collected from the users from two different machines.
- Fuji is used to collect HL2SS and rosbag.
- ALienware is used to collect Perception pkg and raw unity images. This is zipped to a rar file and resides inside each subject files.

### rar file

This contains the following two folders. Unzip to use them.

```
Unity
Perception
```

Perception pkg is saved according to their official script. https://docs.unity3d.com/Packages/com.unity.perception@1.0/manual/PerceptionCamera.html

Unity folder just has images with the timestamp they are captured as their filenames.

### HL2SS

write_max.py https://github.com/Connected-and-Autonomous-Systems-Lab/project_hl2ss/blob/master/codes/write_max.py was used to capture the hl2ss data.
Please refer https://github.com/Connected-and-Autonomous-Systems-Lab/project_hl2ss.git for its format.

### rosbag

ros2bag is collected with the roscli: `ros2 bag record -a`
Refer: https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html


