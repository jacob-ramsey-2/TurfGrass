import time
import os
import random
from google.cloud import storage
import gphoto2 as gp #type: ignore
import logging
import locale
import subprocess
import sys
import mimetypes
import datetime
import platform
import traceback
from pathlib import Path
import cv2 # type: ignore
import numpy as np # type: ignore
import io # type: ignore
import uuid # type: ignore
from PIL import Image # type: ignore

# Google Cloud Storage configuration
BUCKET_NAME = "turfgrass"  # Replace with your actual bucket name
GCS_FOLDER = "a6700_frames"  # Folder in the bucket to store frames

def setup():
    """Initialize logging and basic setup"""
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    callback_obj = gp.check_result(gp.use_python_logging())
    
    
    # Set your bucket name
    global bucket_name
    bucket_name = "turfgrass"
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
        
    global storage_client
    storage_client = storage.Client()
    global bucket
    bucket = storage_client.bucket(bucket_name)

def connect_to_cam():
    """Connect to the camera"""
    camera = gp.check_result(gp.gp_camera_new())
    
    while True:
        try:
            gp.check_result(gp.gp_camera_init(camera))
            print("Camera initialized successfully")
            return camera
        except gp.GPhoto2Error as e:
            print(f"Error initializing camera: {str(e)}")
            time.sleep(1)
            continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            time.sleep(1)
            continue
        

        print(f"Error uploading to GCS: {str(e)}")
        traceback.print_exc()
        return False

def prompt():
    """Get user input for capture parameters"""
    print("Welcome to the A6700 Rapid Frame Capture Script")
    
    # Get duration
    duration = int(input("Enter capture duration in seconds: "))
    rotation = str(input("Rotate images? (y/n): "))
    if rotation == "y":
        rotation = True
    else:
        rotation = False

    return duration, rotation

def rotate_image(image_path):
    """Rotate image by a random angle
    Args:
        image_path: Path to the image file
    Returns:
        PIL Image object
    """
    try:
        with Image.open(image_path) as image:
            random_angle = random.randint(0, 360)  # Random rotation between 0-360 degrees
            rotated = image.rotate(random_angle, expand=True)
            return rotated
    except Exception as e:
        print(f"Error rotating image {image_path}: {str(e)}")
        return None

def capture_frames(camera, duration, fps=30):
    """Capture frames from the camera"""

    print(f"Starting rapid frame capture for {duration} seconds at {fps} FPS")
    # create temp directory
    temp_dir = "temp_frames"
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)
    os.makedirs(temp_dir)
    print(f"Created temporary directory: {temp_dir}")
    
    # calculate total frames and time per frame
    total_frames = duration * fps
    time_per_frame = 1 / fps

    # for each frame, capture the preview image and save it to the temp directory, and sleep until the next frame
    for i in range(total_frames):
        if i % 30 == 0:
            print(f"{i/30} seconds captured")
        try:
            file = gp.check_result(gp.gp_camera_capture_preview(camera))
        except gp.GPhoto2Error as e:
            continue

        temp_filename = os.path.join(temp_dir, f"frame_{time.time()}.jpg")
        # Save preview image to temp file
        file.save(temp_filename)

        time.sleep(time_per_frame)
    

    print(f"Captured {total_frames} frames in {duration} seconds")

def create_video_from_images(image_folder, output_video_path, fps=30):
    # Get all images and extract timestamps for sorting
    images = []
    for img in os.listdir(image_folder):
        if img.endswith((".png", ".jpg", ".jpeg")):
            # Extract timestamp from filename (frame_timestamp.jpg)
            try:
                timestamp = float(img.split('_')[1].split('.jpg')[0])
                images.append((timestamp, img))
            except:
                print(f"Skipping file with invalid format: {img}")
    
    # Sort by timestamp
    images.sort()  # Will sort by timestamp since it's the first element of tuple
    image_files = [img[1] for img in images]  # Get just the filenames
    
    if not image_files:
        print("No images found in the specified folder.")
        return
    
    print(f"Found {len(image_files)} images to process")
    
    first_image = cv2.imread(os.path.join(image_folder, image_files[0]))
    if first_image is None:
        print(f"Error reading first image: {image_files[0]}")
        return
        
    height, width, _ = first_image.shape
    print(f"Video dimensions will be {width}x{height}")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    frames_written = 0
    for image in image_files:
        img_path = os.path.join(image_folder, image)
        frame = cv2.imread(img_path)
        if frame is not None:
            video_writer.write(frame)
            frames_written += 1
        else:
            print(f"Error reading frame: {image}")
    
    video_writer.release()
    print(f"Video created successfully at {output_video_path}")
    print(f"Wrote {frames_written} frames at {fps} FPS")
    print(f"Video duration: {frames_written/fps:.2f} seconds")

def main():
    setup()
    camera = connect_to_cam()
    global rotate
    duration, rotate = prompt()
    try:
        capture_frames(camera, duration)
        print("Captured frames")
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    

    if rotate:
        print("Rotating images...")
        for filename in os.listdir("temp_frames"):
            image_path = os.path.join("temp_frames", filename)
            rotated_image = rotate_image(image_path)
            if rotated_image:
                rotated_image.save(image_path)
            else:
                print(f"Skipping rotation for {filename} due to error")
    
    # create video from images
    create_video_from_images("temp_frames", "output_video.mp4", 30)

    print("Exiting program...")

if __name__ == "__main__":
    main()
