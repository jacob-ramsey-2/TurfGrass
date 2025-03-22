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
    APERTURE_SETTINGS = ['f/2.8', 'f/3.2', 'f/3.5',  'f/4.0', 'f/4.5', 'f/5.0', 'f/5.6', 'f/6.3', 'f/7.1', 'f/8.0', 'f/9.0', 'f/10.0', 'f/11.0', 'f/13.0', 'f/14.0', 'f/16.0', 'f/18.0', 'f/20', 'f/22.0',]
    global SHUTTER_SPEED_SETTINGS
    SHUTTER_SPEED_SETTINGS = ['1/8000', '1/6400', '1/5000', '1/4000', '1/3200', '1/2500', '1/2000', '1/1600', '1/1250', '1/1000', '1/800', '1/640', '1/500', '1/400', '1/320', '1/250', '1/200', '1/160', '1/125', '1/100', '1/80', '1/60', '1/50', '1/40', '1/30', '1/25', '1/20', '1/15', '1/13', '1/10', '1/8', '1/6', '1/5', '1/4', '0.3"', '0.4"', '0.5"', '0.6"', '0.8"', '1"', '1.3"', '1.6"', '2"', '2.5"', '3.2"', '4"', '5"', '6"', '8"', '10"', '13"', '15"', '20"', '25"', '30"']
    global ISO_SETTINGS
    ISO_SETTINGS = ['100', '200', '400', '800', '1600', '3200', '6400', '12800', '25600', '51200', '102400']

    global SETTINGS
    SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS]
    global SETTINGS_NAMES  
    SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso']

# Add this function after the setup() function but before the connect_to_cam() function
def initialize_camera_settings(camera):
    # No need to query camera - use hardcoded values from setup()
    global APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS, SETTINGS, SETTINGS_NAMES
    
    # These values are already set in setup(), no need to modify them
    # Just ensure SETTINGS list is properly populated
    SETTINGS = [APERTURE_SETTINGS, SHUTTER_SPEED_SETTINGS, ISO_SETTINGS]
    SETTINGS_NAMES = ['aperture', 'shutter_speed', 'iso']

# connect to camera establish basic settings
def connect_to_cam():
    global camera
    camera = gp.check_result(gp.gp_camera_new())
    
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            camera.init()
            initialize_camera_settings(camera)
            return
        except gp.GPhoto2Error as ex:
            if attempt >= max_attempts:
                if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
                    print("No camera detected. Please check connection and power.")
                elif ex.code == gp.GP_ERROR_IO_USB_CLAIM:
                    print("Camera is in use by another application.")
                else:
                    print("Error connecting to camera. Please check connection and settings.")
                sys.exit(1)
            time.sleep(2)
        except Exception as e:
            if attempt >= max_attempts:
                print("Failed to connect to camera. Please check connection and try again.")
                sys.exit(1)
            time.sleep(2)

# take single photo
def take_photo():
    global camera
    camera.trigger_capture()

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
    global camera

    # Ask if user wants default settings
    use_defaults = input("Use default/auto settings? (yes/no): ").lower()
    
    # camera settings questions
    def prompt_settings():
        # Now prompt for each setting
        for i in range(len(SETTINGS)):
            setting_name = SETTINGS_NAMES[i]
            available_settings = SETTINGS[i]
            
            print(f"\n{setting_name.replace('_', ' ').title()} Options:")
            print(", ".join(available_settings))
            
            setting = input(f"Enter {setting_name.replace('_', ' ')}: ")
            
            if setting_name == 'iso' and setting.isdigit():
                pass
            else:
                while setting not in available_settings:
                    setting = input(f"Invalid. Enter {setting_name.replace('_', ' ')}: ")
            
            set_camera_setting(camera, setting_name, setting)
        
    global first    
    if first:
        if use_defaults == "yes" or use_defaults == "y":
            try:
                config = gp.check_result(gp.gp_camera_get_config(camera))
                expprogram = gp.check_result(gp.gp_widget_get_child_by_name(config, "expprogram"))
                gp.check_result(gp.gp_widget_set_value(expprogram, "Auto"))
                gp.check_result(gp.gp_camera_set_config(camera, config))
            except:
                prompt_settings()
        else:
            prompt_settings()
    else:
        change_settings = input("Change previous settings? (yes/no): ").lower()
        if change_settings in ["y", "yes"]:
            if use_defaults == "yes" or use_defaults == "y":
                try:
                    config = gp.check_result(gp.gp_camera_get_config(camera))
                    expprogram = gp.check_result(gp.gp_widget_get_child_by_name(config, "expprogram"))
                    gp.check_result(gp.gp_widget_set_value(expprogram, "Auto"))
                    gp.check_result(gp.gp_camera_set_config(camera, config))
                except:
                    prompt_settings()
            else:
                prompt_settings()

    while True:
        try:
            num_pics = int(input("Number of pictures to take (max 40): "))
            if num_pics <= 40:
                break
        except ValueError:
            continue

    if num_pics == 1:
        take_photo()
    else:
        for i in range(num_pics):
            print("hi")
            take_photo()
            time.sleep(1)
        
        

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