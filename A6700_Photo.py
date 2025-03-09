import time
import os
from google.cloud import storage
import gphoto2 as gp 
import logging
import locale
import subprocess
import sys
import mimetypes

# set up logging and global variables
def setup():
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    callback_obj = gp.check_result(gp.use_python_logging())


    global APERTURE_SETTINGS 
    APERTURE_SETTINGS = ['f/1.4', 'f/2.0', 'f/2.8', 'f/4.0', 'f/5.6', 'f/8.0', 'f/11.0', 'f/16.0', 'f/22.0', 'f/32.0']
    global SHUTTER_SPEED_SETTINGS
    SHUTTER_SPEED_SETTINGS = ['1/8000', '1/6400', '1/5000', '1/4000', '1/3200', '1/2500', '1/2000', '1/1600', '1/1250', '1/1000', '1/800', '1/640', '1/500', '1/400', '1/320', '1/250', '1/200', '1/160', '1/125', '1/100', '1/80', '1/60', '1/50', '1/40', '1/30', '1/25', '1/20', '1/15', '1/13', '1/10', '1/8', '1/6', '1/5', '1/4', '0.3', '0.4', '0.5', '0.6', '0.8', '1', '1.3', '1.6', '2', '2.5', '3.2', '4', '5', '6', '8', '10', '13', '15', '20', '25', '30']
    global ISO_SETTINGS
    ISO_SETTINGS = ['100', '200', '400', '800', '1600', '3200', '6400', '12800', '25600', '51200', '102400']
    global WHITE_BALANCE_SETTINGS
    WHITE_BALANCE_SETTINGS = ['Auto', 'Daylight', 'Cloudy', 'Shade', 'Tungsten', 'Fluorescent', 'Flash', 'Custom']  
    global FOCUS_SETTINGS
    FOCUS_SETTINGS = ['Manual', 'Auto']
    global EXPOSURE_MODE_SETTINGS
    EXPOSURE_MODE_SETTINGS = ['Manual', 'Aperture Priority', 'Shutter Priority', 'Program', 'Bulb']
    global SATURATION_SETTINGS
    SATURATION_SETTINGS = ['Normal', 'Medium Low', 'Low', 'Medium High', 'High']
    global CONTRAST_SETTINGS
    CONTRAST_SETTINGS = ['Normal', 'Medium Low', 'Low', 'Medium High', 'High']
    global SHARPNESS_SETTINGS
    SHARPNESS_SETTINGS = ['Normal', 'Medium Low', 'Low', 'Medium High', 'High']
    global SETTINGS
    SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS, WHITE_BALANCE_SETTINGS, FOCUS_SETTINGS, EXPOSURE_MODE_SETTINGS, SATURATION_SETTINGS, CONTRAST_SETTINGS, SHARPNESS_SETTINGS]
    global SETTINGS_NAMES  
    SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso', 'white_balance', 'focus', 'exposure_mode', 'saturation', 'contrast', 'sharpness']

# connect to camera establish basic settings
def connect_to_cam():
    print('Please connect and switch on your camera')
    global camera
    camera = gp.check_result(gp.gp_camera_new())
    while True:
        try:
            camera.init()
        except gp.GPhoto2Error as ex:
            if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                # no camera, try again in 2 seconds
                time.sleep(2)
                continue
            # some other error we can't handle here
            raise
        # operation completed successfully so exit loop
        break
    
    print("Camera connected")
    # continue with rest of program
    text = gp.check_result(gp.gp_camera_get_summary(camera))
    print('Summary')
    print('=======')
    print(text.text)

# save to Google Cloud Storage    
def save_to_gcs(image_file):

    global file_path

    # Set your bucket name
    bucket_name = "turfgrass"  # Replace with your actual bucket name
    
    # set image name to be saved in GCS
    destination_name = file_path.name  

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
    try:
        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()

        # Get the bucket object
        bucket = storage_client.bucket(bucket_name)

        # Create a blob object
        blob = bucket.blob(destination_name)

        # Get the image data as bytes
        try:
            # First try to get data as bytes
            image_data = image_file.get_data_and_size()
            # Check if image_data is bytes
            if not isinstance(image_data, bytes):
                # If not bytes, try to convert to bytes
                image_data = bytes(image_file.get_data_and_size())
        except Exception as e:
            print(f"Error getting image data: {str(e)}")
            # Alternative approach: save to temporary file first
            temp_file = f"temp_{destination_name}"
            image_file.save(temp_file)
            with open(temp_file, 'rb') as f:
                image_data = f.read()
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(destination_name)
        if mime_type is None:
            mime_type = 'application/octet-stream'  # Default MIME type if unknown

        # Upload the image file to GCS
        blob.upload_from_string(image_data, content_type=mime_type)
        print(f"Image uploaded to {destination_name} in bucket {bucket_name}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# take single photo
def take_photo():
    try:
        global file_path
        # Capture a single image
        file_path = camera.capture(gp.GP_CAPTURE_IMAGE)

        # print Camera file path
        print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))

        try:
            # getting image from file path
            camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
            
            print("Saving image to GCS")
            save_to_gcs(camera_file)
        except Exception as e:
            print(f"Error retrieving or saving image: {str(e)}")
            
            # Try an alternative approach - download to local file first
            try:
                print("Trying alternative approach...")
                target_path = os.path.join('.', file_path.name)
                camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
                camera_file.save(target_path)
                print(f"Image saved locally to {target_path}")
                
                # Now try to upload the local file to GCS
                with open(target_path, 'rb') as f:
                    storage_client = storage.Client()
                    bucket = storage_client.bucket("turfgrass")
                    blob = bucket.blob(file_path.name)
                    blob.upload_from_file(f)
                    print(f"Image uploaded to GCS from local file")
                
                # Clean up local file
                try:
                    os.remove(target_path)
                except:
                    pass
            except Exception as inner_e:
                print(f"Alternative approach also failed: {str(inner_e)}")
    except Exception as e:
        print(f"Error taking photo: {str(e)}")

    return

# set camera settings
def set_camera_setting(camera, setting_name, value):
    # Get the camera configuration
    config = gp.check_result(gp.gp_camera_get_config(camera))
    
    # Map our setting names to actual camera config names
    setting_map = {
        'aperture': 'aperture',
        'shutter_speed': 'shutterspeed',
        'iso': 'iso',
        'white_balance': 'whitebalance',
        'focus': 'focusmode',
        'exposure_mode': 'expprogram',
        'saturation': 'saturation',
        'contrast': 'contrast',
        'sharpness': 'sharpness'
    }
    
    # Get the actual camera setting name
    camera_setting_name = setting_map.get(setting_name, setting_name)
    
    try:
        # Try to find the setting widget
        setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, camera_setting_name))
        
        # Set the value for the setting
        gp.check_result(gp.gp_widget_set_value(setting_widget, value))
        
        # Apply the configuration back to the camera
        gp.check_result(gp.gp_camera_set_config(camera, config))
        print(f"Successfully set {setting_name} to {value}")
    except Exception as e:
        print(f"Could not set {setting_name} to {value}: {str(e)}")
        print("Available settings:")
        list_camera_settings(camera)

# Add a helper function to list available camera settings
def list_camera_settings(camera):
    config = gp.check_result(gp.gp_camera_get_config(camera))
    for i in range(gp.check_result(gp.gp_widget_count_children(config))):
        child = gp.check_result(gp.gp_widget_get_child(config, i))
        name = gp.check_result(gp.gp_widget_get_name(child))
        print(f"Setting: {name}")

# prompt user to enter settings and take picture
def prompt():

    # Ask if user wants default settings
    print("Do you want to use default/auto settings? (yes/no)")
    use_defaults = input().lower()
    
    # camera settings questions
    def prompt_settings():
        for i in range(len(SETTINGS)):
            print(f"Please enter the {SETTINGS_NAMES[i]} setting: {SETTINGS[i]}")
            setting = input()
            while setting not in SETTINGS[i]:
                print(f"Invalid setting. Please enter a valid {SETTINGS_NAMES[i]} setting: {SETTINGS[i]}")
                setting = input()
            set_camera_setting(camera, SETTINGS_NAMES[i], setting)
        
        # print summary of settings
        print("Camera settings")
        print('===============')
        config = gp.check_result(gp.gp_camera_get_config(camera))
        for i in range(len(SETTINGS)):
            try:
                setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, SETTINGS_NAMES[i]))
                print(f"{SETTINGS_NAMES[i]}: {gp.check_result(gp.gp_widget_get_value(setting_widget))}")
            except Exception as e:
                print(f"Could not get value for {SETTINGS_NAMES[i]}: {str(e)}")
    
    global first    
    # if first time or user wants default settings
    if first:
        if use_defaults == "yes" or use_defaults == "y":
            try:
                # Set camera to auto mode
                config = gp.check_result(gp.gp_camera_get_config(camera))
                
                # Try to set camera to auto/program mode
                try:
                    expprogram = gp.check_result(gp.gp_widget_get_child_by_name(config, "expprogram"))
                    gp.check_result(gp.gp_widget_set_value(expprogram, "Auto"))
                    gp.check_result(gp.gp_camera_set_config(camera, config))
                    print("Camera set to Auto mode")
                except Exception as e:
                    print(f"Could not set camera to Auto mode: {str(e)}")
                
                print("Using default/auto settings")
            except Exception as e:
                print(f"Error setting default settings: {str(e)}")
                print("Falling back to manual settings")
                prompt_settings()
        else:
            prompt_settings()
    else:
        print("Do you want to change the previous settings? (y/n)")
        change_settings = input().lower()
        if change_settings == "y" or change_settings == "yes":
            if use_defaults == "yes" or use_defaults == "y":
                try:
                    # Set camera to auto mode
                    config = gp.check_result(gp.gp_camera_get_config(camera))
                    
                    # Try to set camera to auto/program mode
                    try:
                        expprogram = gp.check_result(gp.gp_widget_get_child_by_name(config, "expprogram"))
                        gp.check_result(gp.gp_widget_set_value(expprogram, "Auto"))
                        gp.check_result(gp.gp_camera_set_config(camera, config))
                        print("Camera set to Auto mode")
                    except Exception as e:
                        print(f"Could not set camera to Auto mode: {str(e)}")
                    
                    print("Using default/auto settings")
                except Exception as e:
                    print(f"Error setting default settings: {str(e)}")
                    print("Falling back to manual settings")
                    prompt_settings()
            else:
                prompt_settings()
    
    print("How many pictures do you want to take?")
    num_pics = int(input())
    while num_pics > 40:
        print("Please enter a number less than 40")
        print("How many pictures do you want to take?")
        num_pics = input()

    if num_pics == 1:

        print('Capturing 1 image')
        take_photo()
    
    else:
        print("How many seconds inbetween each picture?")
        interval = int(input())
        for i in range(num_pics):
            print(f"Capturing image {i+1}")
            take_photo()
            time.sleep(int(interval))    

# main function
def main():
    setup()
    connect_to_cam()
    global first
    first = True
    continue_prompt = True
    while continue_prompt:
        prompt()
        print("Do you want to continue? (y/n)")
        if input() == "n" or "N":
            continue_prompt = False

if __name__ == "__main__":
    main()

