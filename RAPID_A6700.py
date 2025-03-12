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



def setup():
    """Initialize logging and basic setup"""
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    callback_obj = gp.check_result(gp.use_python_logging())
    
    # Define global settings variables
    global APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS
    global SETTINGS, SETTINGS_NAMES
    
    # Default settings (will be updated with actual camera values)
    APERTURE_SETTINGS = ['f/2.8', 'f/3.2', 'f/3.5', 'f/4.0', 'f/4.5', 'f/5.0', 'f/5.6', 'f/6.3', 'f/7.1', 'f/8.0', 'f/9.0', 'f/10.0', 'f/11.0', 'f/13.0', 'f/14.0', 'f/16.0', 'f/18.0', 'f/20.0', 'f/22.0']
    SHUTTER_SPEED_SETTINGS = ['1/8000', '1/4000', '1/2000', '1/1000', '1/500', '1/250', '1/125', '1/60', '1/30', '1/15']
    ISO_SETTINGS = ['100', '200', '400', '800', '1600', '3200', '6400', '12800']
    
    SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS]
    SETTINGS_NAMES = ['aperture', 'shutterspeed', 'iso']
    
    # Google Cloud Storage configuration
    global bucket_name, GCS_FOLDER
    bucket_name = "turfgrass"
    GCS_FOLDER = "a6700_frames"  # Folder in the bucket to store frames     
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
        
    global storage_client
    storage_client = storage.Client()
    global bucket
    bucket = storage_client.bucket(bucket_name)

def connect_to_cam():
    """Connect to the camera"""
    global camera
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

def initialize_camera_settings(camera):
    """Initialize the global settings variables with values actually supported by the camera."""
    global APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS
    global SETTINGS, SETTINGS_NAMES
    
    # Store default values to use as fallback
    DEFAULT_APERTURE = ['f/2.8', 'f/3.2', 'f/3.5', 'f/4.0', 'f/4.5', 'f/5.0', 'f/5.6', 'f/6.3', 'f/7.1', 'f/8.0', 'f/9.0', 'f/10.0', 'f/11.0', 'f/13.0', 'f/14.0', 'f/16.0', 'f/18.0', 'f/20.0', 'f/22.0']
    DEFAULT_SHUTTER = ['1/8000', '1/4000', '1/2000', '1/1000', '1/500', '1/250', '1/125', '1/60', '1/30', '1/15']
    DEFAULT_ISO = ['100', '200', '400', '800', '1600', '3200', '6400', '12800']
    
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera))
        
        # Update settings lists with actual camera values
        for i, setting_name in enumerate(SETTINGS_NAMES):
            try:
                setting = gp.check_result(gp.gp_widget_get_child_by_name(config, setting_name))
                choices = []
                for j in range(gp.check_result(gp.gp_widget_count_choices(setting))):
                    choice = gp.check_result(gp.gp_widget_get_choice(setting, j))
                    choices.append(choice)
                
                # If we got choices from the camera, use them; otherwise use defaults
                if choices:
                    if setting_name == 'aperture':
                        # Ensure aperture values have f/ prefix
                        choices = [f"f/{c}" if not str(c).startswith('f/') else c for c in choices]
                        APERTURE_SETTINGS = choices
                    elif setting_name == 'shutterspeed':
                        SHUTTER_SPEED_SETTINGS = choices
                    elif setting_name == 'iso':
                        ISO_SETTINGS = choices
                else:
                    if setting_name == 'aperture':
                        APERTURE_SETTINGS = DEFAULT_APERTURE
                    elif setting_name == 'shutterspeed':
                        SHUTTER_SPEED_SETTINGS = DEFAULT_SHUTTER
                    elif setting_name == 'iso':
                        ISO_SETTINGS = DEFAULT_ISO
                
                # Update the SETTINGS list
                if setting_name == 'aperture':
                    SETTINGS[0] = APERTURE_SETTINGS
                elif setting_name == 'shutterspeed':
                    SETTINGS[1] = SHUTTER_SPEED_SETTINGS
                elif setting_name == 'iso':
                    SETTINGS[2] = ISO_SETTINGS
                    
            except Exception as e:
                # Use defaults if there's an error
                if setting_name == 'aperture':
                    APERTURE_SETTINGS = DEFAULT_APERTURE
                    SETTINGS[0] = DEFAULT_APERTURE
                elif setting_name == 'shutterspeed':
                    SHUTTER_SPEED_SETTINGS = DEFAULT_SHUTTER
                    SETTINGS[1] = DEFAULT_SHUTTER
                elif setting_name == 'iso':
                    ISO_SETTINGS = DEFAULT_ISO
                    SETTINGS[2] = DEFAULT_ISO
        
        return config
    except Exception as e:
        print(f"Error initializing camera settings: {str(e)}")
        # In case of complete failure, ensure we at least have the default values
        APERTURE_SETTINGS = DEFAULT_APERTURE
        SHUTTER_SPEED_SETTINGS = DEFAULT_SHUTTER
        ISO_SETTINGS = DEFAULT_ISO
        SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS]
        return None

def list_camera_settings(camera):
    """List all available camera settings and their current values."""
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera))
        print("\nCurrent Camera Settings:")
        print("=======================")
        for i in range(gp.check_result(gp.gp_widget_count_children(config))):
            child = gp.check_result(gp.gp_widget_get_child(config, i))
            name = gp.check_result(gp.gp_widget_get_name(child))
            widget_type = gp.check_result(gp.gp_widget_get_type(child))
            
            # Get current value if possible
            try:
                value = gp.check_result(gp.gp_widget_get_value(child))
                value_str = f"Current value: {value}"
            except:
                value_str = "Value not available"
            
            # For menu or radio widgets, list available choices
            choices = []
            if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                try:
                    for j in range(gp.check_result(gp.gp_widget_count_choices(child))):
                        choices.append(gp.check_result(gp.gp_widget_get_choice(child, j)))
                    choices_str = f"\n  Available options: {choices}"
                except:
                    choices_str = ""
            else:
                choices_str = ""
            
            print(f"\n{name}:")
            print(f"  {value_str}{choices_str}")
    except Exception as e:
        print(f"Error listing camera settings: {str(e)}")

def set_camera_setting(camera, setting_name, value):
    """Set a camera setting to the specified value."""
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera))
        setting = gp.check_result(gp.gp_widget_get_child_by_name(config, setting_name))
        
        # Get default values for validation fallback
        DEFAULT_APERTURE = ['f/2.8', 'f/3.2', 'f/3.5', 'f/4.0', 'f/4.5', 'f/5.0', 'f/5.6', 'f/6.3', 'f/7.1', 'f/8.0', 'f/9.0', 'f/10.0', 'f/11.0', 'f/13.0', 'f/14.0', 'f/16.0', 'f/18.0', 'f/20.0', 'f/22.0']
        DEFAULT_SHUTTER = ['1/8000', '1/4000', '1/2000', '1/1000', '1/500', '1/250', '1/125', '1/60', '1/30', '1/15']
        DEFAULT_ISO = ['100', '200', '400', '800', '1600', '3200', '6400', '12800']
        
        # Verify the value is valid for this setting
        if gp.check_result(gp.gp_widget_get_type(setting)) in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
            choices = []
            try:
                for i in range(gp.check_result(gp.gp_widget_count_choices(setting))):
                    choice = gp.check_result(gp.gp_widget_get_choice(setting, i))
                    choices.append(choice)
            except:
                # If we can't get choices from camera, use defaults
                if setting_name == 'aperture':
                    choices = DEFAULT_APERTURE
                elif setting_name == 'shutterspeed':
                    choices = DEFAULT_SHUTTER
                elif setting_name == 'iso':
                    choices = DEFAULT_ISO
            
            # If still no choices, use defaults
            if not choices:
                if setting_name == 'aperture':
                    choices = DEFAULT_APERTURE
                elif setting_name == 'shutterspeed':
                    choices = DEFAULT_SHUTTER
                elif setting_name == 'iso':
                    choices = DEFAULT_ISO
            
            if value not in choices:
                print(f"Warning: {value} is not in available choices for {setting_name}")
                print(f"Using default choices: {choices}")
                return False
        
        # Set the value
        gp.check_result(gp.gp_widget_set_value(setting, value))
        gp.check_result(gp.gp_camera_set_config(camera, config))
        print(f"Successfully set {setting_name} to {value}")
        return True
    except Exception as e:
        print(f"Error setting {setting_name}: {str(e)}")
        return False

def set_aperture(camera, aperture_value):
    """Set the aperture of the camera."""
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera))
        
        # Try to find the aperture setting
        aperture_names = ['aperture', 'f-number', 'fnumber']
        aperture_widget = None
        
        for name in aperture_names:
            try:
                aperture_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, name))
                if aperture_widget:
                    break
            except:
                continue
        
        if not aperture_widget:
            print("Could not find aperture setting")
            return False
        
        # Get available choices
        choices = []
        for i in range(gp.check_result(gp.gp_widget_count_choices(aperture_widget))):
            choice = gp.check_result(gp.gp_widget_get_choice(aperture_widget, i))
            choices.append(choice)
        
        # Remove 'f/' prefix if the camera doesn't expect it
        if not any(str(c).startswith('f/') for c in choices):
            aperture_value = aperture_value.replace('f/', '')
        
        # Set the value
        gp.check_result(gp.gp_widget_set_value(aperture_widget, aperture_value))
        gp.check_result(gp.gp_camera_set_config(camera, config))
        print(f"Successfully set aperture to {aperture_value}")
        return True
    except Exception as e:
        print(f"Error setting aperture: {str(e)}")
        return False

def prompt():
    """Get user input for capture parameters with enhanced settings control."""
    print("Welcome to the A6700 Rapid Frame Capture Script")
    
    # Initialize camera settings
    config = initialize_camera_settings(camera)
    if not config:
        print("Warning: Could not initialize camera settings. Some features may be limited.")
    
    # Ask if user wants to use default settings
    print("\nDo you want to use default/auto settings? (yes/no)")
    use_defaults = input().lower()
    
    if use_defaults.startswith('y'):
        try:
            # Try to set a moderate ISO for better brightness
            try:
                if '400' in ISO_SETTINGS:
                    set_camera_setting(camera, "iso", "400")
            except:
                pass
            print("Using current camera settings with ISO 400")
        except Exception as e:
            print(f"Error setting default settings: {str(e)}")
    else:
        # Walk through each setting
        for i, setting_name in enumerate(SETTINGS_NAMES):
            print(f"\nCurrent {setting_name}:")
            try:
                current = gp.check_result(gp.gp_widget_get_value(
                    gp.check_result(gp.gp_widget_get_child_by_name(config, setting_name))))
                print(f"Current value: {current}")
            except:
                print("Current value not available")
            
            print(f"\nAvailable {setting_name} options:")
            for j, option in enumerate(SETTINGS[i]):
                print(f"{j+1}. {option}")
            
            print("\nEnter the number of your choice (or press Enter to keep current):")
            choice = input().strip()
            
            if choice:
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(SETTINGS[i]):
                        value = SETTINGS[i][choice_idx]
                        if setting_name == 'aperture':
                            set_aperture(camera, value)
                        else:
                            set_camera_setting(camera, setting_name, value)
                    else:
                        print("Invalid choice. Keeping current setting.")
                except ValueError:
                    print("Invalid input. Keeping current setting.")
    
    # Get duration
    while True:
        try:
            print("\nEnter capture duration in seconds:")
            duration = int(input())
            if duration > 0:
                break
            print("Duration must be positive.")
        except ValueError:
            print("Please enter a valid number.")
    
    
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
