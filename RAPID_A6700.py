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
            try:
                timestamp = float(img.split('_')[1].split('.jpg')[0])
                images.append((timestamp, img))
            except:
                print(f"Skipping file with invalid format: {img}")
    
    # Sort by timestamp
    images.sort()
    image_files = [img[1] for img in images]
    
    if not image_files:
        print("No images found in the specified folder.")
        return False
    
    print(f"Found {len(image_files)} images to process")
    
    first_image = cv2.imread(os.path.join(image_folder, image_files[0]))
    if first_image is None:
        print(f"Error reading first image: {image_files[0]}")
        return False
        
    height, width, _ = first_image.shape
    print(f"Image dimensions: {width}x{height}")
    
    # Create a temporary AVI file first (more reliable encoding)
    temp_avi = os.path.splitext(output_video_path)[0] + '_temp.avi'
    
    # Use MJPG codec for temporary AVI - most compatible
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    video_writer = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))
    
    if not video_writer.isOpened():
        print("Error: Could not initialize VideoWriter")
        return False
    
    frames_written = 0
    for image in image_files:
        img_path = os.path.join(image_folder, image)
        frame = cv2.imread(img_path)
        if frame is not None:
            video_writer.write(frame)
            frames_written += 1
            if frames_written % 30 == 0:
                print(f"Processed {frames_written} frames...")
        else:
            print(f"Error reading frame: {image}")
    
    video_writer.release()
    
    if frames_written == 0:
        print("No frames were written to the video")
        if os.path.exists(temp_avi):
            os.remove(temp_avi)
        return False
        
    if not os.path.exists(temp_avi) or os.path.getsize(temp_avi) == 0:
        print("Error: Temporary video file is empty or does not exist")
        return False
    
    
    # Convert to MP4 using FFmpeg with specific encoding parameters
    try:
        ffmpeg_cmd = [
            'ffmpeg', '-y',  # Overwrite output file if it exists
            '-i', temp_avi,  # Input file
            '-c:v', 'libx264',  # Use H.264 codec
            '-preset', 'medium',  # Encoding preset (balance between speed and quality)
            '-crf', '23',  # Constant Rate Factor (lower = better quality, 23 is default)
            '-movflags', '+faststart',  # Enable fast start for web playback
            '-pix_fmt', 'yuv420p',  # Pixel format for better compatibility
            output_video_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg conversion failed: {result.stderr}")
            return False
            
        # Verify the output file
        if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
            print("Error: Final MP4 file is empty or does not exist")
            return False
            
        
        # Clean up temporary AVI file
        os.remove(temp_avi)
        return True
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        if os.path.exists(temp_avi):
            os.remove(temp_avi)
        return False

def download_from_gcs(source_blob_name):
    """Downloads a blob from the bucket to tmp directory."""
    try:
        # Create tmp directory if it doesn't exist
        tmp_dir = "/tmp"
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
            
        # Generate a unique filename
        tmp_filename = os.path.join(tmp_dir, f"temp_video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        
        # Download to tmp file
        with open(tmp_filename, "wb") as file_obj:
            blob.download_to_file(file_obj)
            
        print(f"Downloaded {source_blob_name} to {tmp_filename}")
        return tmp_filename
    except Exception as e:
        print(f"Error downloading from GCS: {str(e)}")
        traceback.print_exc()
        return None

def upload_video_to_gcs(video_path):
    """Upload video to Google Cloud Storage"""
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} does not exist")
        return False
        
    if os.path.getsize(video_path) == 0:
        print(f"Error: Video file {video_path} is empty")
        return False
        
    try:
        # Verify the video file is readable
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print("Error: Cannot open video file for verification")
                return False
            ret, frame = cap.read()
            if not ret:
                print("Error: Cannot read frames from video file")
                return False
            cap.release()
        except Exception as e:
            print(f"Error verifying video file: {str(e)}")
            return False
            
        # Find first json file in directory to use as credentials
        json_files = [f for f in os.listdir() if f.endswith('.json')]
        if not json_files:
            raise Exception("No JSON credential file found in directory")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_files[0]
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Generate a unique filename using timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_blob_name = f"{GCS_FOLDER}/video_{timestamp}.mp4"
        
        blob = bucket.blob(destination_blob_name)
        
        # Set content type and cache control before upload
        blob.content_type = 'video/mp4'
        blob.cache_control = 'public, max-age=3600'  # Cache for 1 hour
        
        # Upload the file with explicit content type
        with open(video_path, 'rb') as file_obj:
            blob.upload_from_file(
                file_obj,
                content_type='video/mp4',
                timeout=600  # 10 minute timeout
            )
        
        # Verify the upload
        if not blob.exists():
            print("Error: Blob does not exist after upload")
            return False
            
        # Generate a signed URL that will work for 1 hour
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(hours=1),
            method="GET"
        )
        
        
        return True
    except Exception as e:
        print(f"Error uploading to GCS: {str(e)}")
        traceback.print_exc()
        return False

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
                
    # Use tmp directory for video processing
    tmp_dir = "/tmp"
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    
    output_video = os.path.join(tmp_dir, "output_video.mp4")
    
    # Delete existing output video if it exists
    if os.path.exists(output_video):
        os.remove(output_video)
        print(f"Deleted existing output video: {output_video}")
        
    # create video from images
    if not create_video_from_images("temp_frames", output_video, 30):
        print("Failed to create video file")
        return
    
    # upload video to gcs
    if not upload_video_to_gcs(output_video):
        print("Failed to upload video to GCS")
        return
        
    # Clean up tmp file
    try:
        os.remove(output_video)
    except:
        pass
        
    print("Successfully completed video creation and upload")
    print("Exiting program...")

if __name__ == "__main__":
    main()
