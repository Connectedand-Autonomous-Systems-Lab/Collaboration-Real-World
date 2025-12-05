import sys
sys.path.append('/home/mayooran/Documents/hl2ss/viewer')
from pynput import keyboard
import hl2ss
import hl2ss_lnm
import hl2ss_utilities
import hl2ss_3dcv
# import open3d as o3d
import threading
import time 
import numpy as np
import tools.sm_utilities as sm_utilities
# import cv2

host_address = "192.168.1.10"

# These clients works with new hl2ss repo. Run the new hl2ss app on hololens.
# These clients publish data without an external UDP server.

class si_client:
    def __init__(self):
        self.payload = None
        self.previous_head_position = None
        self.previous_head_orientation = None

        host = host_address
        self.si_client = hl2ss_lnm.rx_si(host, hl2ss.StreamPort.SPATIAL_INPUT)
        self.si_client.open()
        self.done = False
        # self.unpacked_si_object = hl2ss.decode_si()

        self.thread = threading.Thread(target=self.run_si_client, daemon=True)
        self.thread.start()
        print("SI client initialized...................................from the python side")

    def run_si_client(self):
        

        while not self.done:
            data = self.si_client.get_next_packet()            
            self.payload = data.payload
            # head_pose, self.eye_ray, self.hand_left, self.hand_right, _,_,_,_ = self.unpacked_si_object.decode(self.payload)

        self.si_client.close()

    def end_thread(self):
        self.done = True
        self.thread.join()
        print("SI client thread ended...................................from the python side")
    
    def get_position(self):
        if self.payload == None:
            # print(self.previous_head_position)
            return self.previous_head_position
        else:
            head_position = [
                    self.payload.head_pose.position[0],
                    self.payload.head_pose.position[1],
                    self.payload.head_pose.position[2]
                ]
            self.previous_head_position = head_position
            return head_position

    def get_orientation(self):
            #        ↑ Y (up)
            #        |
            #        |
            #        *----→ X (right)
            #       /
            #      /
            #  -Z (forward)
        if self.payload == None:
            return self.previous_head_orientation
        
        forward = np.array(self.payload.head_pose.forward)
        up = np.array(self.payload.head_pose.up)
        forward /= np.linalg.norm(forward)
        up /= np.linalg.norm(up)
        right = np.cross(up, -forward)

        # Create a 3x3 rotation matrix with basis vectors as columns
        # rot3 = np.column_stack((right, up, -forward))  # align with ROS frame: X, Y, Z
        # rot3 = np.column_stack((-forward, right, up))  # align with ROS frame: X, Y, Z
        rot3 = np.column_stack((right, up, forward))  # align with ROS frame: X, Y, Z

        # Convert to 4x4 homogeneous matrix
        rot4 = np.eye(4)
        rot4[:3, :3] = rot3
        self.previous_head_orientation = rot4
        return rot4

    def get_hand(self):
        if self.payload == None:
            return str(None)
        
        if self.payload.hand_right_valid:
            hand_right = {
                "position": self.payload.hand_right.position,
                "orientation": self.payload.hand_right.orientation,
                "radius": self.payload.hand_right.radius,
                "accuracy": self.payload.hand_right.accuracy,
            }
        else:
            hand_right = None

        if self.payload.hand_left_valid:
            hand_left = {
                "position": self.payload.hand_left.position,
                "orientation": self.payload.hand_left.orientation,
                "radius": self.payload.hand_left.radius,
                "accuracy": self.payload.hand_left.accuracy,
            }
        else:
            hand_left = None    
            
        json = {"right": hand_right, "left": hand_left}
        return str(json)

    def get_eye(self):
        if self.payload == None:
            return str(None)
        json = {"origin": self.payload.eye_ray.origin, "direction": self.payload.eye_ray.direction}
        return str(json)

class sm_client:
    def __init__(self):
        self.pointcloud = None
        host = host_address

        # Maximum triangles per cubic meter
        self.tpcm = 1000

        # Data format
        self.vpf = hl2ss.SM_VertexPositionFormat.R32G32B32A32Float
        self.tif = hl2ss.SM_TriangleIndexFormat.R32Uint
        self.vnf = hl2ss.SM_VertexNormalFormat.R32G32B32A32Float

        print("Initializing SM client... - python side")
        self.sm_client = hl2ss_lnm.ipc_sm(host, hl2ss.IPCPort.SPATIAL_MAPPING)
        self.sm_client.open()
        self.frame = 0
        print("SM client initialized")


    def get_pcd(self, center):

            box_dim = 2.0
            extents = [box_dim, box_dim, box_dim]

            volumes = hl2ss.sm_bounding_volume()
            volumes.add_box(center, extents)

            self.sm_client.set_volumes(volumes)
            surface_infos = self.sm_client.get_observed_surfaces()

            tasks = hl2ss.sm_mesh_task()
            for surface_info in surface_infos:
                tasks.add_task(surface_info.id, self.tpcm, self.vpf, self.tif, self.vnf)

            meshes = self.sm_client.get_meshes(tasks)

            pcd, mesh = sm_utilities.visualise_3d_lidar(meshes, surface_infos, center)
            # list of [x, y, z]
            
            # print(f'Frame {self.frame} : Observed {len(surface_infos)} surfaces and {len(pcd)} points')

            self.frame += 1
            return pcd

class depth_client:
    def __init__(self):
        self.calibration_thread = threading.Thread(target=self.run_depth_calibration_client)
        self.calibration_thread.start()
        self.calibration_thread.join()
        self.thread = threading.Thread(target=self.run_depth_client, daemon=True)
        self.thread.start()

    def run_depth_client(self):
        host = host_address
        listener = hl2ss_utilities.key_listener(keyboard.Key.esc)
        listener.open()


        depth_client = hl2ss_lnm.rx_rm_depth_longthrow(host, hl2ss.StreamPort.RM_DEPTH_LONGTHROW, mode=hl2ss.StreamMode.MODE_1)
        depth_client.open()

        counter = 0
        while (not listener.pressed()):
            data = depth_client.get_next_packet()
            self.time_stamp = data.timestamp
            self.sensor_ticks = data.payload.sensor_ticks
            self.camera_pose = data.pose

            self.depth = data.payload.depth
            
            uv2xy = hl2ss_3dcv.compute_uv2xy(self.intrinsics, hl2ss.Parameters_RM_DEPTH_LONGTHROW.WIDTH, hl2ss.Parameters_RM_DEPTH_LONGTHROW.HEIGHT)
            xy1, scale = hl2ss_3dcv.rm_depth_compute_rays(uv2xy, self.scale)

            self.depth = hl2ss_3dcv.rm_depth_undistort(self.depth, self.undistort_map)
            # self.depth = hl2ss_3dcv.rm_depth_normalize(self.depth, scale)
            
            counter += 1

        depth_client.close()
        listener.close()

    def run_depth_calibration_client(self):
        data = hl2ss_lnm.download_calibration_rm_depth_longthrow(host_address, hl2ss.StreamPort.RM_DEPTH_LONGTHROW)

        self.extrinsics = data.extrinsics
        self.intrinsics = data.intrinsics
        self.undistort_map = data.undistort_map
        self.scale = data.scale
        self.uv2xy = data.uv2xy
        return

    def end_thread(self):
        self.thread.join()
    
    def get_depth(self):
        # if self.depth.all() == None:
        #     return self.previous_depth
        # else:
        #     self.previous_depth = self.depth
        #     return self.depth
        # destination = cv2.remap(self.depth, self.undistort_map[:,:,0], self.undistort_map[:,:,1], interpolation=cv2.INTER_LINEAR)
        # destination = hl2ss_3dcv.rm_depth_undistort(self.depth, self.undistort_map)
        # destination = hl2ss_3dcv.rm_depth_normalize(destination, self.scale)
        destination = self.depth
        return destination

    def get_camera_info(self):
        return self.camera_info

class pv_client:
    def __init__(self):
        self.thread = threading.Thread(target=self.run_pv_client, daemon=True)
        self.thread.start()
        self.frame = None
        self.receive_time_stamp = None

    def run_pv_client(self):
        host = host_address
        listener = hl2ss_utilities.key_listener(keyboard.Key.esc)
        listener.open()
      
        hl2ss_lnm.start_subsystem_pv(host, hl2ss.StreamPort.PERSONAL_VIDEO, enable_mrc=False, shared=False)
        pv_client = hl2ss_lnm.rx_pv(host, hl2ss.StreamPort.PERSONAL_VIDEO, mode=hl2ss.StreamMode.MODE_1, width=1920, height=1080, framerate=30, profile=hl2ss.VideoProfile.H265_MAIN, bitrate=None, decoded_format='bgr24')
        pv_client.open()

        while not listener.pressed():
            data = pv_client.get_next_packet()
            self.receive_time_stamp = data.timestamp
            self.frame = data.payload.image

        pv_client.close()
        listener.close()

    def end_thread(self):
        self.thread.join()
        print("PV client thread ended...................................from the python side")
    
    def get_frame(self):
        return self.frame, self.receive_time_stamp

class time_client:
    def __init__(self):
        pass

    def get_time(self):
        host = host_address
        client = hl2ss_lnm.ipc_rc(host, hl2ss.IPCPort.REMOTE_CONFIGURATION)
        client.open()
        utc_offset = client.ts_get_utc_offset()
        client.close()
        return utc_offset

if __name__ == "__main__":
    pass
    # si_client_instance = si_client()
    # time.sleep(1)
    # while True:
    #     si_client_instance.get_position()
    #     time.sleep(0.5)

    # sm_client_instance = sm_client()
    # while True:
    #     pcd = sm_client_instance.get_pcd()
    #     time.sleep(0.5)