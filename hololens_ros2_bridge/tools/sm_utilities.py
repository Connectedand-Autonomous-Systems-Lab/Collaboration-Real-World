import pandas as pd
import matplotlib.pyplot as plt
import open3d as o3d
import numpy as np
import datetime
import hl2ss_3dcv
import hl2ss_sa
import time
import asyncio
import threading

def visualize_2d_point_cloud(csv_path):
    # Load the 2D point cloud
    df = pd.read_csv(csv_path)

    # Ensure required columns are present
    if not {'x', 'y'}.issubset(df.columns):
        raise ValueError("CSV must contain 'x' and 'y' columns.")

    # Create a scatter plot
    plt.figure(figsize=(8, 8))
    plt.scatter(df['x'], df['y'], s=1, c='blue', alpha=0.7)
    plt.title("2D Point Cloud (XY Projection)")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.axis("equal")
    plt.grid(True)
    plt.show()

def visualise_mesh_thread(meshes, timeout=1.0):
    def run_visualizer():
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name='Mesh View', width=640, height=480, left=200, top=200)
        vis.add_geometry(meshes)
        vis.get_render_option().mesh_show_back_face = False

        start_time = time.time()
        while time.time() - start_time < timeout:
            vis.poll_events()
            vis.update_renderer()
            time.sleep(0.01)

        vis.destroy_window()

    t = threading.Thread(target=run_visualizer)
    t.start()
    return t  # Optional: return the thread if you want to join or check it later

def filter_height_and_save_2d(df, output_csv_path, min_height=-1.0, max_height=1.0, save_to_csv=True):
    
    # Ensure required columns are present
    if not {'x', 'y', 'z'}.issubset(df.columns):
        raise ValueError("CSV must contain 'x', 'y', 'z' columns.")

    # Filter based on height (z)
    filtered_df = df[(df['y'] >= min_height) & (df['y'] <= max_height)]

    # Drop the 'z' column to keep only 2D (x, y)
    filtered_2d_df = filtered_df[['x', 'y']]

    if save_to_csv:
        # Save to new CSV
        filtered_2d_df.to_csv(output_csv_path, index=False)
        print(f"Saved 2D filtered point cloud to: {output_csv_path}")
    
    return filtered_2d_df

def surfaces_to_mesh(meshes, surface_infos, center, ply_file_path="output_mesh.ply", save_to_csv=False):

    open3d_meshes = []

    for index, mesh in meshes.items():
        id_hex = surface_infos[index].id.hex()
        timestamp = surface_infos[index].update_time
        # Convert Windows FILETIME to datetime
        timestamp_dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=timestamp / 10)

        if (mesh is None):
            print(f'Task {index}: surface id {id_hex} compute mesh failed')
            continue

        # Surface timestamps are given in Windows FILETIME (utc)
        # print(f'Task {index}: surface id {id_hex} @ {timestamp_dt} has {mesh.vertex_positions.shape[0]} vertices {mesh.triangle_indices.shape[0]} triangles {mesh.vertex_normals.shape[0]} normals')

        hl2ss_3dcv.sm_mesh_cast(mesh, np.float64, np.uint32, np.float64)
        hl2ss_3dcv.sm_mesh_normalize(mesh)
        
        open3d_mesh = hl2ss_sa.sm_mesh_to_open3d_triangle_mesh(mesh)
        open3d_mesh = hl2ss_sa.open3d_triangle_mesh_swap_winding(open3d_mesh)
        open3d_mesh.vertex_colors = open3d_mesh.vertex_normals
        open3d_meshes.append(open3d_mesh)

    # Merge all individual meshes into a single one
    combined_mesh = o3d.geometry.TriangleMesh()
    for mesh in open3d_meshes:
        combined_mesh += mesh

    # Save to a file (choose .ply or .obj)
    if save_to_csv:
        o3d.io.write_triangle_mesh("spatial_mapping_mesh_new.ply", combined_mesh)
        # print("Saved full spatial mesh to spatial_mapping_mesh.ply")
    return combined_mesh

def mesh_to_pcd(combined_mesh, save_to_csv=False, csv_file_path="merged_mesh_vertices.csv"):
    # Convert mesh vertices to numpy array
    vertices = np.asarray(combined_mesh.vertices)
    vertices = vertices[:, [2, 0, 1]]  # change this depending on actual mix-up

    # Save to CSV (optional)
    if save_to_csv:
        df = pd.DataFrame(vertices, columns=["x", "y", "z"])
        df.to_csv(csv_file_path, index=False)
        print(f"Saved mesh vertices to CSV: {csv_file_path}")

    # Return as list of [x, y, z]
    return vertices.tolist()

def visualise_3d_lidar(meshes, surface_infos, center):
    combined_mesh = surfaces_to_mesh(meshes, surface_infos, center, save_to_csv=False)
    pcd = mesh_to_pcd(combined_mesh, save_to_csv=False)
    return pcd, combined_mesh

def visualise_lidar(meshes, surface_infos, center):
    combined_mesh = surfaces_to_mesh(meshes, surface_infos, center, save_to_csv=False)
    # print(f"start of async {time.time()}")
    # visualise_mesh_thread(combined_mesh)
    # print(f"End of async {time.time()}")
    pcd = mesh_to_pcd(combined_mesh, save_to_csv=False)
    pcd_2d = filter_height_and_save_2d(pcd, "filtered_2d_point_cloud.csv", min_height=-1.0, max_height=1.0, save_to_csv=False)
    return pcd_2d, combined_mesh
    
def visualise_2d_pcd(ax, pcd_2d, center, si, frame):
    forward = si.head_pose.forward
    arrow_dx = forward[0]
    arrow_dy = -forward[2]
    arrow_scale = 0.1
    arrow_dx *= arrow_scale
    arrow_dy *= arrow_scale

    ax.clear()
    ax.scatter(pcd_2d['x'], pcd_2d['y'], s=1)
    # ax.plot(center[0], center[1], 'r+', markersize=12, markeredgewidth=2, label='Center')
    ax.arrow(center[0], center[1], arrow_dx, arrow_dy,
         head_width=0.02, head_length=0.02, fc='red', ec='red', label='Forward')
    ax.set_title(f"Frame {frame}")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect('equal')

    plt.draw()
    plt.pause(0.01)