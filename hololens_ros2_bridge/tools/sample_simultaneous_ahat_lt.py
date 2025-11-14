#------------------------------------------------------------------------------
# Experimental simultaneous RM Depth AHAT and RM Depth Long Throw.
# Press esc to stop.
#------------------------------------------------------------------------------
import sys
sys.path.append('/home/mayooran/Documents/hl2ss/viewer')
import cv2
import hl2ss_imshow
import hl2ss
import hl2ss_lnm
import hl2ss_mp
import hl2ss_3dcv
import threading
import hl2ss_utilities
import time
import numpy as np
from pynput import keyboard

# Settings --------------------------------------------------------------------

# HoloLens address
host = "10.196.21.62"

#------------------------------------------------------------------------------
class depth_client:
    def __init__(self):
        self.depth = None
        calibration_path = '/home/mayooran/Documents/hololens_ros2_bridge/src/hololens_ros2_bridge/calibration'
        self.calibration_ht = hl2ss_3dcv.get_calibration_rm(calibration_path, host, hl2ss.StreamPort.RM_DEPTH_AHAT)
        self.thread = threading.Thread(target=self.run_simultaneous_ahat_lt)
        self.thread.start()


    def get_depth(self):
        return self.depth

    def run_simultaneous_ahat_lt(self):
        # Start streams ----------------------------------------------------------
        listener = hl2ss_utilities.key_listener(keyboard.Key.esc)
        listener.open()
        sink_ht = hl2ss_mp.stream(hl2ss_lnm.rx_rm_depth_ahat(host, hl2ss.StreamPort.RM_DEPTH_AHAT))

        # Without this delay, the depth streams might crash and require rebooting 
        # the HoloLens to fix
        sink_ht.open()

        # cv2.namedWindow(hl2ss.get_port_name(hl2ss.StreamPort.RM_DEPTH_AHAT) + '-depth')
        
        while (not listener.pressed()):
            _, data_ht = sink_ht.get_most_recent_frame()

            if (data_ht is not None):
                # cv2.imshow(hl2ss.get_port_name(hl2ss.StreamPort.RM_DEPTH_AHAT) + '-depth', hl2ss_3dcv.rm_depth_colormap(data_ht.payload.depth, 1056)) # Scaled for visibility
                depth = hl2ss_3dcv.rm_depth_undistort(data_ht.payload.depth, self.calibration_ht.undistort_map)
                self.depth = depth
        # Stop streams ------------------------------------------------------------
        sink_ht.close()
  
if __name__ == '__main__':
    # Start streams -----------------------------------------------------------
    client = depth_client()