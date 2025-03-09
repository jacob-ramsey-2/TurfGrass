import time
import os
from google.cloud import storage
import gphoto2 as gp 
import logging
import locale
import subprocess
import sys
import mimetypes
import datetime

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
    
# save to Google Cloud Storage    
def save_to_gcs(image_file):
    global file_path

    # Set your bucket name
    bucket_name = "turfgrass"  # Replace with your actual bucket name
    
    # Create a unique name with timestamp for GCS
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Make sure file_path is valid
        if not hasattr(file_path, 'name') or not file_path.name:
            print("Error: Invalid file_path object")
            return None
            
        original_name = file_path.name
        file_extension = original_name.split('.')[-1] if '.' in original_name else 'jpg'
        destination_name = f"{original_name.split('.')[0]}_{timestamp}.{file_extension}"
    except Exception as e:
        print(f"Error creating filename: {str(e)}")
        destination_name = f"image_{timestamp}.jpg"  # Fallback filename

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
    
    try:
        print(f"Uploading to Google Cloud Storage as {destination_name}...")
        
        # Save to local file first (safer approach)
        target_path = os.path.join('.', f"temp_{timestamp}.{file_extension}")
        image_file.save(target_path)
        print(f"Image saved locally to {target_path}")
        
        # Now upload to GCS from the local file
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_name)
        
        with open(target_path, 'rb') as f:
            blob.upload_from_file(f)
        
        print(f"Image successfully uploaded to {destination_name} in bucket {bucket_name}")
        
        # Clean up local file
        if os.path.exists(target_path):
            os.remove(target_path)
            print(f"Temporary file {target_path} removed")

    except Exception as e:
        print(f"Error in save_to_gcs: {str(e)}")
        # If there was an error, try to clean up any temporary files
        try:
            if 'target_path' in locals() and os.path.exists(target_path):
                os.remove(target_path)
        except:
            pass
        return None
    
    return destination_name

# take single photo
def take_photo():
    try:
        global file_path
        global camera
        
        # Generate a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Capture a single image
        try:
            file_path = gp.check_result(camera.capture(gp.GP_CAPTURE_IMAGE))
            print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
        except Exception as capture_error:
            print(f"Error capturing image: {str(capture_error)}")
            return False

        # Wait a moment for the camera to process the image
        time.sleep(1.0)  # Increased wait time
        
        try:
            # Getting image from file path
            camera_file = gp.check_result(camera.file_get(
                file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
            
            # Save to Google Cloud Storage
            result = save_to_gcs(camera_file)
            if result is None:
                print("Failed to save to Google Cloud Storage")
                return False
                
            # Delete the file from camera to free up memory
            try:
                camera.file_delete(file_path.folder, file_path.name)
                print(f"Deleted file from camera")
            except Exception as del_error:
                print(f"Warning: Could not delete file from camera: {str(del_error)}")
            
            return True
                
        except Exception as e:
            print(f"Error retrieving or saving image: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error in take_photo: {str(e)}")
        return False
        
    # Force garbage collection to free memory
    import gc
    gc.collect()

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
    global camera  # Add this line to access the global camera variable

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
                
                # Increase brightness by setting exposure compensation
                try:
                    # Get a fresh config after setting auto mode
                    config = gp.check_result(gp.gp_camera_get_config(camera))
                    
                    # Try different possible names for exposure compensation
                    exposure_comp_names = ["exposurecompensation", "exposurecomp", "exposure-compensation", "expcomp"]
                    
                    for name in exposure_comp_names:
                        try:
                            exp_comp = gp.check_result(gp.gp_widget_get_child_by_name(config, name))
                            # Get current choices
                            choice_count = gp.check_result(gp.gp_widget_count_choices(exp_comp))
                            choices = [gp.check_result(gp.gp_widget_get_choice(exp_comp, i)) for i in range(choice_count)]
                            
                            # Find a positive exposure compensation value
                            # Typically exposure compensation values are like: -2, -1.7, -1.3, -1, -0.7, -0.3, 0, 0.3, 0.7, 1, 1.3, 1.7, 2
                            positive_values = [c for c in choices if isinstance(c, str) and (c.startswith("+") or (c[0].isdigit() and c != "0"))]
                            
                            if positive_values:
                                # Choose a moderate positive value (around +1 if available)
                                target_value = next((v for v in positive_values if v in ["1", "+1", "1.0", "+1.0"]), positive_values[0])
                                gp.check_result(gp.gp_widget_set_value(exp_comp, target_value))
                                gp.check_result(gp.gp_camera_set_config(camera, config))
                                print(f"Increased brightness: set {name} to {target_value}")
                                break
                            else:
                                print(f"No positive exposure compensation values found")
                        except Exception as inner_e:
                            continue
                    
                    # Try to increase ISO as an alternative way to increase brightness
                    try:
                        iso = gp.check_result(gp.gp_widget_get_child_by_name(config, "iso"))
                        choice_count = gp.check_result(gp.gp_widget_count_choices(iso))
                        choices = [gp.check_result(gp.gp_widget_get_choice(iso, i)) for i in range(choice_count)]
                        
                        # Find a higher ISO value (400 is a good balance for brightness without too much noise)
                        if "400" in choices:
                            gp.check_result(gp.gp_widget_set_value(iso, "400"))
                            gp.check_result(gp.gp_camera_set_config(camera, config))
                            print("Increased brightness: set ISO to 400")
                    except Exception as iso_e:
                        print(f"Could not adjust ISO: {str(iso_e)}")
                    
                except Exception as e:
                    print(f"Could not increase brightness: {str(e)}")
                
                print("Using default/auto settings with increased brightness")
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
    while True:
        try:
            num_pics = int(input())
            if num_pics > 40:
                print("Please enter a number less than 40")
                print("How many pictures do you want to take?")
                continue
            break
        except ValueError:
            print("Please enter a valid number")
            print("How many pictures do you want to take?")

    if num_pics == 1:

        print('Capturing 1 image')
        take_photo()
    
    else:
        print("How many seconds inbetween each picture?")
        while True:
            try:
                interval = int(input())
                break
            except ValueError:
                print("Please enter a valid number for the interval")
                print("How many seconds inbetween each picture?")
        
        # Remove interval restrictions
        # User can set any interval they want
        
        successful_captures = 0
        for i in range(num_pics):
            print(f"Capturing image {i+1} of {num_pics}")
            
            # Take photo and check result
            result = False
            try:
                result = take_photo()
            except Exception as e:
                print(f"Exception during capture {i+1}: {str(e)}")
                result = False
                
            # Update success counter
            if result:
                successful_captures += 1
                print(f"Successfully captured image {i+1}")
            else:
                print(f"Failed to capture image {i+1}")
            
            # Sleep between captures if not the last one
            if i < num_pics - 1:
                print(f"Waiting {interval} seconds before next capture...")
                time.sleep(interval)
                
            # If we've had multiple failures, try to reset the camera
            if i > 0 and successful_captures == 0:
                try:
                    print("Attempting to reset camera connection...")
                    camera.exit()
                    time.sleep(2)
                    camera = gp.check_result(gp.gp_camera_new())
                    camera.init()
                    print("Camera connection reset successfully")
                except Exception as reset_error:
                    print(f"Could not reset camera: {str(reset_error)}")
                    print("You may need to restart the program")
                    break
        
        print(f"Capture session complete. Successfully captured {successful_captures} of {num_pics} images.")

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
        user_input = input().lower()
        if user_input == "n" or user_input == "no":
            continue_prompt = False

if __name__ == "__main__":
    main()

