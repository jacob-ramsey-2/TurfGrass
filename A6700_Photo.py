import time
import os
from google.cloud import storage
import gphoto2 as gp #type: ignore
import logging
import locale
import subprocess
import sys
import mimetypes
import datetime
import platform  # To detect the operating system
import traceback
from pathlib import Path

# set up logging and global variables
def setup():
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=logging.WARNING)
    callback_obj = gp.check_result(gp.use_python_logging())


    global APERTURE_SETTINGS 
    APERTURE_SETTINGS = ['f/1.4', 'f/2.0', 'f/2.8', 'f/4.0', 'f/5.6', 'f/8.0', 'f/11.0', 'f/16.0', 'f/22.0', 'f/32.0']
    global SHUTTER_SPEED_SETTINGS
    SHUTTER_SPEED_SETTINGS = ['1/8000', '1/6400', '1/5000', '1/4000', '1/3200', '1/2500', '1/2000', '1/1600', '1/1250', '1/1000', '1/800', '1/640', '1/500', '1/400', '1/320', '1/250', '1/200', '1/160', '1/125', '1/100', '1/80', '1/60', '1/50', '1/40', '1/30', '1/25', '1/20', '1/15', '1/13', '1/10', '1/8', '1/6', '1/5', '1/4', '0.3"', '0.4"', '0.5"', '0.6"', '0.8"', '1"', '1.3"', '1.6"', '2"', '2.5"', '3.2"', '4"', '5"', '6"', '8"', '10"', '13"', '15"', '20"', '25"', '30"']
    global ISO_SETTINGS
    ISO_SETTINGS = ['100', '200', '400', '800', '1600', '3200', '6400', '12800', '25600', '51200', '102400']
    global WHITE_BALANCE_SETTINGS
    WHITE_BALANCE_SETTINGS = ['Auto', 'Daylight', 'Cloudy', 'Shade', 'Tungsten', 'Fluorescent', 'Flash', 'Custom']  
    global FOCUS_SETTINGS
    FOCUS_SETTINGS = ['Manual', 'Auto']
    global EXPOSURE_MODE_SETTINGS
    EXPOSURE_MODE_SETTINGS = ['Manual', 'Aperture Priority', 'Shutter Priority', 'Program', 'Bulb']

    global SETTINGS
    SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS, WHITE_BALANCE_SETTINGS, FOCUS_SETTINGS, EXPOSURE_MODE_SETTINGS]
    global SETTINGS_NAMES  
    SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso', 'white_balance', 'focus', 'exposure_mode']

# Add this function after the setup() function but before the connect_to_cam() function
def initialize_camera_settings(camera):
    """
    Initialize the global settings variables with values actually supported by the camera.
    This ensures we only offer options that the camera can accept.
    """
    global APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS
    global WHITE_BALANCE_SETTINGS, FOCUS_SETTINGS, EXPOSURE_MODE_SETTINGS
    global SETTINGS, SETTINGS_NAMES
    
    # Default fallback values in case we can't get settings from camera
    default_settings = {
        'aperture': ['f/1.4', 'f/2.0', 'f/2.8', 'f/4.0', 'f/5.6', 'f/8.0', 'f/11.0', 'f/16.0', 'f/22.0', 'f/32.0'],
        'shutterspeed': ['1/8000', '1/6400', '1/5000', '1/4000', '1/3200', '1/2500', '1/2000', '1/1600', '1/1250', '1/1000', 
                         '1/800', '1/640', '1/500', '1/400', '1/320', '1/250', '1/200', '1/160', '1/125', '1/100'],
        'iso': ['100', '200', '400', '800', '1600', '3200', '6400', '12800', '25600', '51200', '102400'],
        'whitebalance': ['Auto', 'Daylight', 'Cloudy', 'Shade', 'Tungsten', 'Fluorescent', 'Flash', 'Custom'],
        'focusmode': ['Manual', 'Auto'],
        'expprogram': ['Manual', 'Aperture Priority', 'Shutter Priority', 'Program', 'Bulb']
    }
    
    # Mapping from our setting names to actual camera config names
    setting_map = {
        'shutter_speed': 'shutterspeed',
        'iso': 'iso',
        'white_balance': 'whitebalance',
        'focus': 'focusmode',
        'exposure_mode': 'expprogram'
    }
    
    # Get camera configuration
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera))
        
        # Set camera to Aperture Priority mode first to ensure aperture settings can be accessed
        try:
            # Find the exposure program widget
            exp_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, 'expprogram'))
            
            # Get current exposure mode
            current_exp_mode = gp.check_result(gp.gp_widget_get_value(exp_widget))
            print(f"Current exposure mode: {current_exp_mode}")
            
            # Get available exposure modes
            exp_choices = []
            for i in range(gp.check_result(gp.gp_widget_count_choices(exp_widget))):
                exp_choices.append(gp.check_result(gp.gp_widget_get_choice(exp_widget, i)))
            
            print(f"Available exposure modes: {exp_choices}")
            
            # Find an appropriate aperture priority mode
            ap_mode = None
            for mode in ['Aperture Priority', 'A', 'Av', 'aperture-priority']:
                if mode in exp_choices:
                    ap_mode = mode
                    break
            
            # If we found an aperture priority mode and we're not already in it
            if ap_mode and current_exp_mode != ap_mode:
                print(f"Setting camera to {ap_mode} mode for aperture control...")
                gp.check_result(gp.gp_widget_set_value(exp_widget, ap_mode))
                gp.check_result(gp.gp_camera_set_config(camera, config))
                print(f"Camera set to {ap_mode} mode")
                
                # Get a fresh config after changing the mode
                config = gp.check_result(gp.gp_camera_get_config(camera))
            elif not ap_mode:
                print("Could not find Aperture Priority mode in available choices.")
                print("Aperture settings may not work correctly.")
        except Exception as e:
            print(f"Error setting exposure mode: {str(e)}")
            print("Continuing with initialization...")
        
        # Initialize settings with values from camera
        camera_settings = {}
        
        # Find the aperture configuration using our new function
        aperture_config, _ = find_aperture_config(camera)
        if aperture_config:
            aperture_property_name = aperture_config.get_name()
            setting_map['aperture'] = aperture_property_name
            print(f"Found aperture property with name: {aperture_property_name}")
        else:
            print("Could not find aperture property with any known name")
        
        # Print all available config options to help with debugging
        print("\nAll available camera config options:")
        for i in range(gp.check_result(gp.gp_widget_count_children(config))):
            child = gp.check_result(gp.gp_widget_get_child(config, i))
            name = gp.check_result(gp.gp_widget_get_name(child))
            print(f"  - {name}")
        
        # Now get settings using the updated mapping
        for setting_name, camera_setting_name in setting_map.items():
            try:
                setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, camera_setting_name))
                widget_type = gp.check_result(gp.gp_widget_get_type(setting_widget))
                
                # For menu or radio widgets, get available choices
                if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                    choices = []
                    for i in range(gp.check_result(gp.gp_widget_count_choices(setting_widget))):
                        choice = gp.check_result(gp.gp_widget_get_choice(setting_widget, i))
                        choices.append(choice)
                    
                    if choices:  # Only update if we got some choices
                        # For aperture, check if values already have 'f/' prefix
                        if setting_name == 'aperture':
                            # Check if the values already have the 'f/' prefix
                            has_prefix = any(str(choice).startswith('f/') for choice in choices)
                            
                            if has_prefix:
                                # Values already have 'f/' prefix, use them as is
                                print(f"Aperture values already have 'f/' prefix, using as is")
                            else:
                                # Add 'f/' prefix to make it more user-friendly
                                choices = [f"f/{choice}" for choice in choices]
                        
                        camera_settings[setting_name] = choices
                        print(f"Found {len(choices)} options for {setting_name}: {choices[:5]}...")
            except Exception as e:
                print(f"Could not get choices for {setting_name}: {str(e)}")
        
        # Update global variables with camera settings or fallback to defaults
        APERTURE_SETTINGS = camera_settings.get('aperture', default_settings['aperture'])
        SHUTTER_SPEED_SETTINGS = camera_settings.get('shutter_speed', default_settings['shutterspeed'])
        ISO_SETTINGS = camera_settings.get('iso', default_settings['iso'])
        WHITE_BALANCE_SETTINGS = camera_settings.get('white_balance', default_settings['whitebalance'])
        FOCUS_SETTINGS = camera_settings.get('focus', default_settings['focusmode'])
        EXPOSURE_MODE_SETTINGS = camera_settings.get('exposure_mode', default_settings['expprogram'])
        
        # Update the SETTINGS list with the new values - removing saturation, contrast, and sharpness
        SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS, WHITE_BALANCE_SETTINGS, 
                   FOCUS_SETTINGS, EXPOSURE_MODE_SETTINGS]
        
        # Update SETTINGS_NAMES to match SETTINGS - removing saturation, contrast, and sharpness
        SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso', 'white_balance', 'focus', 'exposure_mode']
        
        print("Camera settings initialized successfully")
    except Exception as e:
        print(f"Error initializing camera settings: {str(e)}")
        print("Using default settings")
        
        # Use default settings if we couldn't get them from the camera
        APERTURE_SETTINGS = default_settings['aperture']
        SHUTTER_SPEED_SETTINGS = default_settings['shutterspeed']
        ISO_SETTINGS = default_settings['iso']
        WHITE_BALANCE_SETTINGS = default_settings['whitebalance']
        FOCUS_SETTINGS = default_settings['focusmode']
        EXPOSURE_MODE_SETTINGS = default_settings['expprogram']
        
        # Update the SETTINGS list with the default values - removing saturation, contrast, and sharpness
        SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS, WHITE_BALANCE_SETTINGS, 
                   FOCUS_SETTINGS, EXPOSURE_MODE_SETTINGS]
        
        # Update SETTINGS_NAMES to match SETTINGS - removing saturation, contrast, and sharpness
        SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso', 'white_balance', 'focus', 'exposure_mode']

# connect to camera establish basic settings
def connect_to_cam():
    print('Please connect and switch on your camera')
    print('Checking for camera connection...')
    
    global camera
    camera = gp.check_result(gp.gp_camera_new())
    
    # Set a timeout for camera connection attempts (in seconds)
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            print(f"Connection attempt {attempt}/{max_attempts}...")
            camera.init()
            print("Camera connected successfully!")
            # Print camera model information if available
            try:
                config = gp.check_result(gp.gp_camera_get_config(camera))
                camera_model = gp.check_result(gp.gp_widget_get_child_by_name(config, "cameramodel"))
                model_value = gp.check_result(gp.gp_widget_get_value(camera_model))
                print(f"Connected to: {model_value}")
            except:
                print("Connected to camera (model information unavailable)")
            
            # Initialize camera settings after successful connection
            print("Initializing camera settings...")
            initialize_camera_settings(camera)
            
            break
        except gp.GPhoto2Error as ex:
            if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                # No camera detected
                print("No camera detected. Please check that:")
                print("1. Your camera is connected to the computer")
                print("2. Your camera is powered on")
                print("3. Your camera is in the correct mode (usually PC Connection or similar)")
                print("Waiting 2 seconds before trying again...")
                time.sleep(2)
                continue
            elif ex.code == gp.GP_ERROR_IO_USB_CLAIM:
                print("Camera is in use by another application. Please close any other programs using the camera.")
                print("Waiting 2 seconds before trying again...")
                time.sleep(2)
                continue
            else:
                # Some other error we can't handle here
                print(f"Error connecting to camera: {ex}")
                print(f"Error code: {ex.code}")
                print("Please ensure your camera is:")
                print("1. Properly connected via USB")
                print("2. Powered on")
                print("3. Set to the correct connection mode")
                print("4. Not being used by another application")
                
                if attempt >= max_attempts:
                    print("\nFailed to connect after multiple attempts.")
                    print("You may need to:")
                    print("1. Disconnect and reconnect your camera")
                    print("2. Restart your camera")
                    print("3. Check your USB cable")
                    print("4. Ensure you have the correct permissions to access the camera")
                    raise
                
                print(f"Trying again in 2 seconds... (Attempt {attempt}/{max_attempts})")
                time.sleep(2)
                continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if attempt >= max_attempts:
                print("Failed to connect after multiple attempts due to unexpected errors.")
                raise
            print(f"Trying again in 2 seconds... (Attempt {attempt}/{max_attempts})")
            time.sleep(2)
            continue
    
    if attempt >= max_attempts:
        print("Failed to connect to camera after maximum attempts.")
        print("Please check your camera connection and try running the program again.")
        sys.exit(1)
    
    # Operation completed successfully
    return

# take single photo
def take_photo():
    try:
        global camera
        
        # Generate a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        local_filename = f"capture_{timestamp}.jpg"
        
        # Minimal output during interval shooting
        is_interval_shooting = 'num_pics' in globals() and globals().get('num_pics', 1) > 1
        
        if not is_interval_shooting:
            print(f"Attempting to capture image...")
        
        # Use a different approach to capture the image
        # Instead of using camera.capture which returns a CameraFilePath,
        # we'll use camera_capture_preview which returns the image data directly
        try:
            # First try to capture a preview
            preview_file = camera.capture_preview()
            preview_file.save(local_filename)
            
            if not is_interval_shooting:
                print(f"Saved preview image to {local_filename}")
            
            # Upload to Google Cloud Storage
            try:
                # Set your bucket name
                bucket_name = "turfgrass"
                destination_name = f"image_{timestamp}.jpg"
                
                # Find first json file in directory to use as credentials
                json_files = [f for f in os.listdir() if f.endswith('.json')]
                if not json_files:
                    raise Exception("No JSON credential file found in directory")
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_files[0]
                
                # Upload the file
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(destination_name)
                
                with open(local_filename, 'rb') as f:
                    # Add content_type to ensure browser displays the image properly
                    blob.upload_from_file(f, content_type="image/jpeg")
                
                if not is_interval_shooting:
                    print(f"Image successfully uploaded to {destination_name} in bucket {bucket_name}")
                
                # Clean up local file
                if os.path.exists(local_filename):
                    os.remove(local_filename)
                    if not is_interval_shooting:
                        print(f"Temporary file {local_filename} removed")
                
                return True
                
            except Exception as upload_error:
                if not is_interval_shooting:
                    print(f"Error uploading to GCS: {str(upload_error)}")
                return False
                
        except Exception as preview_error:
            if not is_interval_shooting:
                print(f"Error capturing preview: {str(preview_error)}")
            
            # Try an alternative approach - trigger capture and download
            try:
                if not is_interval_shooting:
                    print("Trying alternative capture method...")
                
                # Trigger capture
                camera.trigger_capture()
                time.sleep(2)  # Wait for capture to complete
                
                # List files on camera
                folder = "/"
                for name, value in camera.folder_list_files(folder):
                    if not is_interval_shooting:
                        print(f"Found file on camera: {folder}/{name}")
                    
                    # Get the most recent file
                    camera_file = camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL)
                    camera_file.save(local_filename)
                    
                    if not is_interval_shooting:
                        print(f"Saved image to {local_filename}")
                    
                    # Upload to Google Cloud Storage
                    try:
                        # Set your bucket name
                        bucket_name = "turfgrass"
                        destination_name = f"image_{timestamp}.jpg"
                        
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
                        
                        # Upload the file
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(destination_name)
                        
                        with open(local_filename, 'rb') as f:
                            # Add content_type to ensure browser displays the image properly
                            blob.upload_from_file(f, content_type="image/jpeg")
                        
                        if not is_interval_shooting:
                            print(f"Image successfully uploaded to {destination_name} in bucket {bucket_name}")
                        
                        # Clean up local file
                        if os.path.exists(local_filename):
                            os.remove(local_filename)
                            if not is_interval_shooting:
                                print(f"Temporary file {local_filename} removed")
                        
                        # Try to delete from camera
                        try:
                            camera.file_delete(folder, name)
                            if not is_interval_shooting:
                                print(f"Deleted file from camera")
                        except:
                            pass
                        
                        return True
                        
                    except Exception as upload_error:
                        if not is_interval_shooting:
                            print(f"Error uploading to GCS: {str(upload_error)}")
                        return False
                    
                    # Only process the first file
                    break
                    
            except Exception as alt_error:
                if not is_interval_shooting:
                    print(f"Alternative capture method failed: {str(alt_error)}")
                return False
    
    except Exception as e:
        print(f"Error in take_photo: {str(e)}")
        
    # Force garbage collection to free memory
    import gc
    gc.collect()
    
    return False

# Function to upload a file to Google Cloud Storage with proper MIME type
def upload_file_to_gcs(file_path, bucket_name):
    """
    Uploads an image file to Google Cloud Storage with proper MIME type
    
    Parameters:
    file_path (str): Local path to the image file to upload
    bucket_name (str): Name of your GCS bucket
    """
    try:
        # Generate a destination name based on timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_name = f"image_{timestamp}.jpg"
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
        
        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()
        
        # Get the bucket object
        bucket = storage_client.bucket(bucket_name)
        
        # Create a blob object
        blob = bucket.blob(destination_name)
        
        # Set content type based on image extension (default to JPEG)
        _, ext = os.path.splitext(file_path.lower())
        image_extensions = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        content_type = image_extensions.get(ext, 'image/jpeg')
        
        # Upload the file with the appropriate content type
        blob.upload_from_filename(file_path, content_type=content_type)
        
        print(f"Image {file_path} uploaded to {destination_name} in bucket {bucket_name}")
        return True
        
    except Exception as e:
        print(f"Error uploading to GCS: {str(e)}")
        return False

# set camera settings
def set_camera_setting(camera, setting_name, value):
    # Special handling for aperture setting
    if setting_name == 'aperture':
        return set_aperture(camera, value)
    
    # Get the camera configuration
    config = gp.check_result(gp.gp_camera_get_config(camera))
    
    # Map our setting names to actual camera config names
    setting_map = {
        'shutter_speed': 'shutterspeed',
        'iso': 'iso',
        'white_balance': 'whitebalance',
        'focus': 'focusmode',
        'exposure_mode': 'expprogram'
    }
    
    # Get the actual camera setting name
    camera_setting_name = setting_map.get(setting_name, setting_name)
    
    # Process value based on setting type
    processed_value = value
    
    # Try multiple times to set the value
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            # Try to find the setting widget
            setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, camera_setting_name))
            
            # Get the widget type to handle it appropriately
            widget_type = gp.check_result(gp.gp_widget_get_type(setting_widget))
            
            # For radio or menu widgets, check if the value is in the choices
            if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                choices = []
                try:
                    for i in range(gp.check_result(gp.gp_widget_count_choices(setting_widget))):
                        choices.append(gp.check_result(gp.gp_widget_get_choice(setting_widget, i)))
                except Exception as e:
                    print(f"Error getting choices for {setting_name}: {str(e)}")
                
                if not choices:
                    print(f"Warning: No choices available for {setting_name}. This might be a camera limitation.")
                    print(f"Attempting to set {setting_name} to {processed_value} anyway...")
                elif processed_value not in choices:
                    print(f"Value '{processed_value}' not in available choices for {setting_name}.")
                    print(f"Available choices: {choices}")
                    
                    # Special handling for ISO - try to find the closest available ISO value
                    if setting_name == 'iso' and processed_value.isdigit():
                        numeric_choices = [int(c) for c in choices if c.isdigit()]
                        if numeric_choices:
                            target_iso = int(processed_value)
                            closest_iso = min(numeric_choices, key=lambda x: abs(x - target_iso))
                            print(f"Using closest available ISO value: {closest_iso}")
                            processed_value = str(closest_iso)
                        else:
                            return
                    else:
                        return
            
            # Set the value for the setting
            gp.check_result(gp.gp_widget_set_value(setting_widget, processed_value))
            
            # Apply the configuration back to the camera
            gp.check_result(gp.gp_camera_set_config(camera, config))
            print(f"Successfully set {setting_name} to {value} (processed as {processed_value})")
            
            # If we got here, the setting was successful
            break
            
        except Exception as e:
            print(f"Could not set {setting_name} to {value}: {str(e)}")
            if attempt < max_attempts:
                print(f"Retrying (attempt {attempt+1}/{max_attempts})...")
                # Wait a moment before retrying
                time.sleep(1)
                # Get a fresh config for the next attempt
                config = gp.check_result(gp.gp_camera_get_config(camera))
            else:
                print("Available settings:")
                list_camera_settings(camera)
                
                # If this is the ISO setting, let's debug it specifically
                if setting_name == 'iso':
                    print("\nDebugging ISO setting specifically:")
                    debug_camera_setting(camera, 'iso')
                break

def set_aperture(camera, aperture_value):
    """Set the aperture of the camera using the approach from aperature.py."""
    try:
        # First, ensure the camera is in a mode that allows aperture control
        config = gp.check_result(gp.gp_camera_get_config(camera))
        
        # Try to set the exposure mode to Aperture Priority or Manual
        try:
            exp_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, 'expprogram'))
            exp_mode = gp.check_result(gp.gp_widget_get_value(exp_widget))
            
            # Aperture can typically only be set in Manual or Aperture Priority modes
            if exp_mode not in ['Manual', 'Aperture Priority', 'M', 'A', 'Av']:
                print(f"Current exposure mode is: {exp_mode}")
                print("Setting exposure mode to 'Aperture Priority'...")
                
                # Get available choices
                choices = []
                for i in range(gp.check_result(gp.gp_widget_count_choices(exp_widget))):
                    choices.append(gp.check_result(gp.gp_widget_get_choice(exp_widget, i)))
                
                # Find an appropriate aperture priority mode
                ap_mode = None
                for mode in ['Aperture Priority', 'A', 'Av', 'aperture-priority']:
                    if mode in choices:
                        ap_mode = mode
                        break
                
                if ap_mode:
                    gp.check_result(gp.gp_widget_set_value(exp_widget, ap_mode))
                    gp.check_result(gp.gp_camera_set_config(camera, config))
                    print(f"Set exposure mode to {ap_mode}")
                    
                    # Wait a moment for the camera to process the mode change
                    time.sleep(1)
                    
                    # Get a fresh config after changing the mode
                    config = gp.check_result(gp.gp_camera_get_config(camera))
                else:
                    print("Could not find Aperture Priority mode in available choices.")
                    print(f"Available modes: {choices}")
        except Exception as e:
            print(f"Could not check/set exposure mode: {str(e)}")
        
        # Find the aperture configuration
        aperture_config, config = find_aperture_config(camera)
        
        if not aperture_config:
            print("Could not find aperture configuration.")
            return False
        
        # Get available aperture choices
        available_apertures = []
        for i in range(gp.check_result(gp.gp_widget_count_choices(aperture_config))):
            available_apertures.append(gp.check_result(gp.gp_widget_get_choice(aperture_config, i)))
        
        print(f"Available aperture settings: {available_apertures}")
        
        # Process the aperture value to match camera's format
        processed_value = aperture_value
        
        # Check if the camera's aperture values have 'f/' prefix
        camera_values_have_prefix = any(str(choice).startswith('f/') for choice in available_apertures)
        
        # Handle different aperture value formats based on what the camera expects
        if camera_values_have_prefix:
            # Camera expects values with 'f/' prefix
            if not processed_value.startswith('f/'):
                processed_value = f"f/{processed_value}"
        else:
            # Camera expects values without 'f/' prefix
            if processed_value.startswith('f/'):
                processed_value = processed_value[2:]
        
        print(f"Processing aperture value: '{aperture_value}' -> '{processed_value}'")
        
        # Check if the processed value is in available choices
        if processed_value not in available_apertures:
            print(f"Value '{processed_value}' not in available aperture choices.")
            
            # Try to find the closest available aperture value
            try:
                # Remove 'f/' prefix if present for comparison
                target_value = processed_value
                if target_value.startswith('f/'):
                    target_value = target_value[2:]
                
                target_aperture = float(target_value)
                
                # Process choices to get numeric values for comparison
                numeric_choices = []
                choice_mapping = {}  # Map numeric values back to original choices
                
                for c in available_apertures:
                    try:
                        # Remove 'f/' prefix if present for comparison
                        numeric_value = c
                        if isinstance(c, str) and c.startswith('f/'):
                            numeric_value = c[2:]
                        
                        float_value = float(numeric_value)
                        numeric_choices.append(float_value)
                        choice_mapping[float_value] = c  # Map back to original choice
                    except (ValueError, TypeError):
                        continue
                
                if numeric_choices:
                    closest_aperture_value = min(numeric_choices, key=lambda x: abs(x - target_aperture))
                    closest_aperture = choice_mapping[closest_aperture_value]  # Get original choice
                    print(f"Using closest available aperture value: {closest_aperture}")
                    processed_value = closest_aperture
                else:
                    print("Could not find a suitable aperture value.")
                    return False
            except (ValueError, TypeError) as e:
                print(f"Error processing aperture value: {str(e)}")
                return False
        
        # Set the aperture value
        gp.check_result(gp.gp_widget_set_value(aperture_config, processed_value))
        
        # Apply the configuration to the camera
        gp.check_result(gp.gp_camera_set_config(camera, config))
        
        print(f"Successfully set aperture to {processed_value}")
        
        # Verify the setting was applied
        time.sleep(0.5)
        verify_config = gp.check_result(gp.gp_camera_get_config(camera))
        verify_widget, _ = find_aperture_config(camera)
        if verify_widget:
            current_value = gp.check_result(gp.gp_widget_get_value(verify_widget))
            print(f"Verified aperture value: {current_value}")
            
            if current_value != processed_value:
                print(f"Warning: Aperture value mismatch. Set to {processed_value} but camera reports {current_value}")
                print("This may indicate that the camera is not in the correct mode for aperture adjustments.")
        
        return True
    except gp.GPhoto2Error as e:
        print(f"Error setting aperture: {e}")
        return False

def find_aperture_config(camera):
    """Find the correct aperture configuration option for the camera."""
    try:
        # Get camera configuration
        config = gp.check_result(gp.gp_camera_get_config(camera))
        
        # Common names for aperture settings in different camera models
        aperture_names = ['aperture', 'f-number', 'fnumber', 'f-stop', 'fstop', 'shutterspeed', 'aperture-value']
        
        # Find the first matching aperture config
        aperture_config = None
        aperture_config_name = None
        
        for name in aperture_names:
            try:
                aperture_config = gp.check_result(gp.gp_widget_get_child_by_name(config, name))
                aperture_config_name = name
                print(f"Found aperture configuration as '{name}'")
                break
            except gp.GPhoto2Error:
                continue
        
        if not aperture_config:
            print("Could not find aperture configuration. Available options are:")
            list_camera_settings(camera)
            return None, None
        
        return aperture_config, config
    except gp.GPhoto2Error as e:
        print(f"Error finding aperture configuration: {e}")
        return None, None

def get_available_apertures(camera):
    """Get available aperture settings for the camera."""
    try:
        # Find aperture configuration
        aperture_config, config = find_aperture_config(camera)
        
        if not aperture_config:
            print("Could not find aperture configuration. Make sure your camera is in a mode that allows aperture control.")
            return []
        
        # Check if this config has choices
        try:
            # Get available choices
            apertures = []
            for i in range(gp.check_result(gp.gp_widget_count_choices(aperture_config))):
                apertures.append(gp.check_result(gp.gp_widget_get_choice(aperture_config, i)))
            
            # Get current value
            current_aperture = gp.check_result(gp.gp_widget_get_value(aperture_config))
            print(f"Current aperture: {current_aperture}")
            
            return apertures
        except gp.GPhoto2Error:
            # This config might not have choices
            print(f"The '{aperture_config.get_name()}' setting doesn't have selectable choices.")
            return []
            
    except gp.GPhoto2Error as e:
        print(f"Error getting aperture settings: {e}")
        return []

# Add a helper function to list available camera settings
def list_camera_settings(camera):
    config = gp.check_result(gp.gp_camera_get_config(camera))
    for i in range(gp.check_result(gp.gp_widget_count_children(config))):
        child = gp.check_result(gp.gp_widget_get_child(config, i))
        name = gp.check_result(gp.gp_widget_get_name(child))
        widget_type = gp.check_result(gp.gp_widget_get_type(child))
        
        # Get current value if possible
        try:
            value = gp.check_result(gp.gp_widget_get_value(child))
            value_str = f", Current value: {value}"
        except:
            value_str = ""
        
        # For menu or radio widgets, list available choices
        choices = []
        if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
            try:
                for j in range(gp.check_result(gp.gp_widget_count_choices(child))):
                    choices.append(gp.check_result(gp.gp_widget_get_choice(child, j)))
                choices_str = f", Choices: {choices}"
            except:
                choices_str = ""
        else:
            choices_str = ""
        
        print(f"Setting: {name}{value_str}{choices_str}")

def debug_camera_setting(camera, setting_name):
    """
    Debug a specific camera setting by showing its type, current value, and available choices.
    
    Args:
        camera: The camera object
        setting_name: The name of the setting to debug
    """
    # Map our setting names to actual camera config names
    setting_map = {
        'shutter_speed': 'shutterspeed',
        'iso': 'iso',
        'white_balance': 'whitebalance',
        'focus': 'focusmode',
        'exposure_mode': 'expprogram'
    }
    
    try:
        # For aperture, use our specialized function
        if setting_name == 'aperture':
            aperture_config, config = find_aperture_config(camera)
            
            if aperture_config is None:
                print("Could not find aperture setting with any known name")
                return
                
            setting_widget = aperture_config
            camera_setting_name = aperture_config.get_name()
            print(f"Found aperture setting with name: {camera_setting_name}")
        else:
            # Get the actual camera setting name
            camera_setting_name = setting_map.get(setting_name, setting_name)
            
            # Get the camera configuration
            config = gp.check_result(gp.gp_camera_get_config(camera))
            
            # Try to find the setting widget
            setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, camera_setting_name))
        
        # Get widget type
        widget_type = gp.check_result(gp.gp_widget_get_type(setting_widget))
        type_names = {
            gp.GP_WIDGET_WINDOW: "Window",
            gp.GP_WIDGET_SECTION: "Section",
            gp.GP_WIDGET_TEXT: "Text",
            gp.GP_WIDGET_RANGE: "Range",
            gp.GP_WIDGET_TOGGLE: "Toggle",
            gp.GP_WIDGET_RADIO: "Radio",
            gp.GP_WIDGET_MENU: "Menu",
            gp.GP_WIDGET_BUTTON: "Button",
            gp.GP_WIDGET_DATE: "Date"
        }
        type_name = type_names.get(widget_type, f"Unknown ({widget_type})")
        
        # Get current value
        try:
            value = gp.check_result(gp.gp_widget_get_value(setting_widget))
            print(f"Setting: {setting_name}")
            print(f"Camera setting name: {camera_setting_name}")
            print(f"Type: {type_name}")
            
            # For aperture, check if it already has f/ prefix
            if setting_name == 'aperture':
                if isinstance(value, str) and value.startswith('f/'):
                    # Value already has f/ prefix
                    print(f"Current value: {value}")
                else:
                    # Add f/ prefix for display
                    print(f"Current value: {value} (displayed as f/{value})")
            else:
                print(f"Current value: {value}")
            
            # For range widgets, show min, max, and step
            if widget_type == gp.GP_WIDGET_RANGE:
                min_val, max_val, step_val = gp.check_result(gp.gp_widget_get_range(setting_widget))
                print(f"Range: min={min_val}, max={max_val}, step={step_val}")
            
            # For menu or radio widgets, list available choices
            if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                print("Available choices:")
                choices = []
                try:
                    for i in range(gp.check_result(gp.gp_widget_count_choices(setting_widget))):
                        choice = gp.check_result(gp.gp_widget_get_choice(setting_widget, i))
                        choices.append(choice)
                        
                        # For aperture, check if it already has f/ prefix
                        if setting_name == 'aperture':
                            if isinstance(choice, str) and choice.startswith('f/'):
                                # Choice already has f/ prefix
                                print(f"  - {choice}")
                            else:
                                # Add f/ prefix for display
                                print(f"  - {choice} (displayed as f/{choice})")
                        else:
                            print(f"  - {choice}")
                    
                    if not choices:
                        print("  No choices available (empty list)")
                except Exception as e:
                    print(f"  Error getting choices: {str(e)}")
                
                # For aperture, provide additional help
                if setting_name == 'aperture':
                    print("\nAperture setting help:")
                    
                    # Check if values already have f/ prefix
                    values_have_prefix = any(isinstance(c, str) and c.startswith('f/') for c in choices)
                    
                    if values_have_prefix:
                        print("- The camera expects aperture values WITH the 'f/' prefix")
                        print("- Your camera returns values like 'f/4.0', so use them exactly as shown")
                    else:
                        print("- The camera expects aperture values WITHOUT the 'f/' prefix")
                        print("- When you enter 'f/4.0', the program will send '4.0' to the camera")
                    
                    print("- If your value isn't in the list, the program will try to find the closest match")
                    
                    # Check the current exposure mode
                    try:
                        exp_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, 'expprogram'))
                        exp_mode = gp.check_result(gp.gp_widget_get_value(exp_widget))
                        print(f"\nCurrent exposure mode: {exp_mode}")
                        
                        # Get available exposure modes
                        print("Available exposure modes:")
                        for i in range(gp.check_result(gp.gp_widget_count_choices(exp_widget))):
                            choice = gp.check_result(gp.gp_widget_get_choice(exp_widget, i))
                            print(f"  - {choice}")
                        
                        print("\nNote: Aperture can typically only be set in Manual or Aperture Priority modes.")
                        if exp_mode not in ['Manual', 'Aperture Priority', 'M', 'A']:
                            print(f"Current mode '{exp_mode}' may not allow aperture adjustments.")
                            print("Try setting the exposure mode to 'Manual' or 'Aperture Priority' first.")
                    except Exception as e:
                        print(f"Could not check exposure mode: {str(e)}")
                
                # For ISO, provide additional help
                if setting_name == 'iso':
                    print("\nISO setting help:")
                    print("- You can enter any numeric ISO value")
                    print("- If your value isn't in the list, the program will try to find the closest match")
        except Exception as e:
            print(f"Could not get value: {str(e)}")
    except Exception as e:
        print(f"Could not find setting '{setting_name}': {str(e)}")
        print(f"Camera setting name tried: '{camera_setting_name}'")
        
        # For aperture, try to find the aperture configuration
        if setting_name == 'aperture':
            print("\nAttempting to find aperture configuration using find_aperture_config:")
            aperture_config, _ = find_aperture_config(camera)
            if aperture_config:
                print(f"Found aperture configuration as '{aperture_config.get_name()}'")
            else:
                print("Could not find aperture configuration with any known name")
        
        # List all available settings to help troubleshoot
        print("\nAll available camera settings:")
        list_camera_settings(camera)

# prompt user to enter settings and take picture
def prompt():
    global camera  # Add this line to access the global camera variable

    # Ask if user wants to debug camera settings
    print("Do you want to debug camera settings? (yes/no)")
    debug_mode = input().lower()
    
    if debug_mode == "yes" or debug_mode == "y":
        print("\n--- Camera Settings Debug Mode ---")
        print("1. List all camera settings")
        print("2. Debug specific setting")
        print("3. Debug problematic settings (aperture, saturation, contrast, sharpness)")
        print("4. Exit debug mode")
        
        debug_choice = input("Enter your choice (1-4): ")
        
        if debug_choice == "1":
            print("\nListing all camera settings:")
            list_camera_settings(camera)
            return prompt()  # Restart prompt after debugging
        
        elif debug_choice == "2":
            setting_name = input("Enter the setting name to debug: ")
            print(f"\nDebugging setting: {setting_name}")
            debug_camera_setting(camera, setting_name)
            return prompt()  # Restart prompt after debugging
        
        elif debug_choice == "3":
            print("\nDebugging problematic settings:")
            problematic_settings = ["aperture", "saturation", "contrast", "sharpness"]
            for setting in problematic_settings:
                print(f"\n--- {setting.upper()} ---")
                debug_camera_setting(camera, setting)
            return prompt()  # Restart prompt after debugging
        
        elif debug_choice == "4":
            print("Exiting debug mode")
        
        else:
            print("Invalid choice. Exiting debug mode.")
    
    # Ask if user wants default settings
    print("Do you want to use default/auto settings? (yes/no)")
    use_defaults = input().lower()
    
    # camera settings questions
    def prompt_settings():
        # First, set the exposure mode to ensure aperture settings will work
        try:
            config = gp.check_result(gp.gp_camera_get_config(camera))
            
            # Find the exposure program widget
            exp_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, 'expprogram'))
            
            # Get available exposure modes
            exp_choices = []
            for i in range(gp.check_result(gp.gp_widget_count_choices(exp_widget))):
                exp_choices.append(gp.check_result(gp.gp_widget_get_choice(exp_widget, i)))
            
            # Find an appropriate aperture priority mode
            ap_mode = None
            for mode in ['Aperture Priority', 'A', 'Av', 'aperture-priority']:
                if mode in exp_choices:
                    ap_mode = mode
                    break
            
            if ap_mode:
                print(f"\nSetting camera to {ap_mode} mode for aperture control...")
                gp.check_result(gp.gp_widget_set_value(exp_widget, ap_mode))
                gp.check_result(gp.gp_camera_set_config(camera, config))
                print(f"Camera set to {ap_mode} mode")
                
                # Update the exposure mode in our settings
                for i, setting_name in enumerate(SETTINGS_NAMES):
                    if setting_name == 'exposure_mode':
                        # Find the index of the aperture priority mode in the exposure mode settings
                        for j, mode in enumerate(EXPOSURE_MODE_SETTINGS):
                            if mode == ap_mode or (mode == 'Aperture Priority' and ap_mode in ['A', 'Av']):
                                # Skip asking for exposure mode since we've already set it
                                print(f"\nExposure mode automatically set to {ap_mode} for aperture control")
                                break
            else:
                print("Could not find Aperture Priority mode in available choices.")
                print("Aperture settings may not work correctly.")
        except Exception as e:
            print(f"Error setting exposure mode: {str(e)}")
        
        # Get the latest available aperture settings from the camera
        available_apertures = get_available_apertures(camera)
        if available_apertures:
            # Update the global aperture settings with the actual values from the camera
            global APERTURE_SETTINGS
            APERTURE_SETTINGS = available_apertures
            # Update the SETTINGS list with the new aperture settings
            for i, setting_name in enumerate(SETTINGS_NAMES):
                if setting_name == 'aperture':
                    SETTINGS[i] = available_apertures
                    break
        
        # Now prompt for each setting
        for i in range(len(SETTINGS)):
            setting_name = SETTINGS_NAMES[i]
            
            # Skip exposure mode if we've already set it to aperture priority
            if setting_name == 'exposure_mode' and 'ap_mode' in locals() and ap_mode:
                continue
                
            available_settings = SETTINGS[i]
            
            # Show available options with more context
            print(f"\nPlease enter the {setting_name} setting:")
            
            # For ISO, show a note about available values
            if setting_name == 'iso':
                print("Note: If the camera doesn't accept your ISO value, it will try to use the closest available value.")
            
            # For aperture, show a note about aperture priority mode
            if setting_name == 'aperture':
                print("Note: Camera has been set to Aperture Priority mode to enable aperture control.")
                print(f"Available aperture values from camera: {', '.join(available_apertures) if available_apertures else 'None detected'}")
            
            # Display available options in a more readable format
            if len(available_settings) > 10:
                # If there are many options, show them in groups
                print("Available options:")
                for j in range(0, len(available_settings), 5):
                    print(", ".join(available_settings[j:j+5]))
            else:
                # If there are few options, show them on one line
                print(f"Available options: {', '.join(available_settings)}")
            
            setting = input("> ")
            
            # Special handling for ISO - allow any numeric value
            if setting_name == 'iso' and setting.isdigit():
                # Allow any numeric ISO value, the set_camera_setting function will handle finding the closest match
                pass
            else:
                # For other settings, validate against the available options
                while setting not in available_settings:
                    print(f"Invalid setting. Please enter a valid {setting_name} setting from the options above.")
                    setting = input("> ")
            
            # Set the camera setting
            set_camera_setting(camera, setting_name, setting)
        
        # print summary of settings
        print("\nCamera settings summary")
        print('=====================')
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
        print("How many seconds inbetween each picture? (You can use decimal values like 0.1)")
        while True:
            try:
                interval = float(input())
                break
            except ValueError:
                print("Please enter a valid number for the interval")
                print("How many seconds inbetween each picture? (You can use decimal values like 0.1)")
        
        # Remove interval restrictions
        # User can set any interval they want
        
        successful_captures = 0
        captured_filenames = []  # Store filenames for summary
        
        for i in range(num_pics):
            print(f"\nCapturing image {i+1} of {num_pics}")
            
            # If this is not the first image and there's an interval, wait silently
            if i > 0 and interval > 0:
                time.sleep(interval)
            
            # Take photo and check result
            result = False
            try:
                result = take_photo()
                # Store the filename if successful
                if result:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"image_{timestamp}.jpg"
                    captured_filenames.append(filename)
            except Exception as e:
                # Minimal error output
                print(f"Error during capture {i+1}")
                result = False
                
            # Update success counter
            if result:
                successful_captures += 1
            else:
                print(f"Failed to capture image {i+1}")
            
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
                    print("Could not reset camera. You may need to restart the program")
                    break
        
        # Print summary
        print("\n--- Capture Session Summary ---")
        print(f"Successfully captured {successful_captures} of {num_pics} images.")
        print("All images were saved to Google Cloud Storage bucket: turfgrass")
        if captured_filenames:
            print("\nCaptured files:")
            for filename in captured_filenames:
                print(f"- {filename}")
        print("-------------------------------")

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

def interval_shooting(interval_seconds, count=None):
    # Initialize variables
    start_time = time.time()
    photo_count = 0
    
    try:
        while True:
            # Check if we've reached the count limit
            if count is not None and photo_count >= count:
                print(f"Completed {count} photos. Exiting.")
                break
                
            # Calculate time until next photo
            current_time = time.time()
            elapsed_time = current_time - start_time
            photos_should_have_taken = int(elapsed_time / interval_seconds)
            
            if photos_should_have_taken > photo_count:
                # Time to take another photo
                print(f"\nTaking photo {photo_count + 1}")
                if count is not None:
                    print(f" of {count}")
                
                # Take the photo
                file_path = take_photo()
                
                if file_path:
                    # Upload to Google Cloud Storage if enabled
                    if upload_to_gcs:
                        upload_file_to_gcs(file_path, bucket_name)
                    
                    photo_count += 1
                    last_photo_time = time.time()
                else:
                    print("Failed to take photo. Retrying at next interval.")
            
            # Calculate time to next photo
            next_photo_time = start_time + ((photo_count + 1) * interval_seconds)
            wait_time = next_photo_time - time.time()
            
            # Only show countdown for waits longer than 3 seconds
            if wait_time > 3:
                # Display a simple countdown
                print(f"\nNext photo in: ", end="", flush=True)
                remaining = int(wait_time)
                
                while remaining > 3:
                    print(f"{remaining}...", end="", flush=True)
                    time.sleep(1)
                    remaining -= 1
                
                # Final 3-second countdown without beeps
                while remaining > 0:
                    print(f"{remaining}...", end="", flush=True)
                    time.sleep(1)
                    remaining -= 1
                
                print("Capturing!")
            else:
                # For short intervals, just wait
                if wait_time > 0:
                    time.sleep(wait_time)
                print("Capturing!")
            
    except KeyboardInterrupt:
        print("\nInterval shooting stopped by user.")
    except Exception as e:
        print(f"\nError during interval shooting: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

