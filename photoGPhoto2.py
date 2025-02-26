import time
import os
from google.cloud import storage
import gphoto2 as gp  # type: ignore
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
    text = gp.gp_camera_get_summary(camera)
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

        # Get the image data and MIME type
        image_data = image_file.get_data_and_size()
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

    global file_path
    # Capture a single image
    file_path = camera.capture(gp.GP_CAPTURE_IMAGE)

    # print Camera file path
    print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))

    # getting image from file path
    camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)

    print("Saving image to GCS")
    save_to_gcs(camera_file)

    return

# set camera settings
def set_camera_setting(camera, setting_name, value):
    # Get the camera configuration
    config = gp.check_result(gp.gp_camera_get_config(camera))

    # Find the setting widget
    setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, setting_name))

    # Set the value for the setting
    gp.check_result(gp.gp_widget_set_value(setting_widget, value))

    # Apply the configuration back to the camera
    gp.check_result(gp.gp_camera_set_config(camera, config))

# prompt user to enter settings and take picture
def prompt():

    # camera settings questions
    def prompt_settings():
        for i in range(len(SETTINGS)):
            print(f"Please enter the {SETTINGS_NAMES[i]} setting: {SETTINGS[i]}")
            setting = input()
            set_camera_setting(camera, SETTINGS_NAMES[i], setting)
        
        # print summary of settings
        print("Camera settings")
        print('===============')
        config = gp.check_result(gp.gp_camera_get_config(camera))
        for i in range(len(SETTINGS)):
            setting_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, SETTINGS_NAMES[i]))
            print(f"{SETTINGS_NAMES[i]}: {gp.check_result(gp.gp_widget_get_value(setting_widget).value)}")
    
    global first    
    # if first time, set camera settings
    if first:
        prompt_settings()

    else:
        print("Do you want to change the previous settings? (y/n)")
        if input() == "y" or "Y":
            prompt_settings()
        
        print("How many pictures do you want to take?")
        num_pics = input()
        if input() == 1:

            print('Capturing 1 image')
            take_photo()
        
        else:
            print("How many seconds inbetween each picture?")
            interval = input()
            for i in range(num_pics):
                print(f"Capturing image {i+1}")
                take_photo()
                time.sleep(int(interval))    

# main function
def main():
    setup()
    global first
    first = True
    while True:
        prompt()

if __name__ == "__main__":
    main()

