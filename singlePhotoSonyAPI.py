
from libsonyapi.camera import Camera
from libsonyapi.actions import Actions
import PIL.Image
import requests
import PIL.ExifTags
import time
import os
from google.cloud import storage

# connect to camera establish basic settings
'''def connect_to_cam():
    camera = Camera()  # create camera instance
    camera_info = camera.info()  # get camera camera_info
    print(camera_info)
    print(camera.services)
    print(camera.name)  # print name of camera
    print(camera.api_version)  # print api version of camera
'''

# save to Google Cloud Storage    
def save_to_gcs():
    # Set your bucket name
    bucket_name = "turfgrass"  # Replace with your actual bucket name
    
    # Example usage
    image_path = "smile.jpg"  # TODO change image name
    destination_name = "my_image.jpg"  # TODO change image name
    
    # Verify the file exists and is an image
    if not os.path.exists(image_path):
        print(f"Error: Image file {image_path} not found")
        return
    
    # Check if it's actually an image file
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    if not os.path.splitext(image_path.lower())[1] in valid_extensions:
        print(f"Warning: {image_path} may not be a supported image format")
    
    """
    Uploads an image file to Google Cloud Storage
    
    Parameters:
    bucket_name (str): Name of your GCS bucket
    image_path (str): Local path to the image file you want to upload
    destination_blob_name (str): Name the image will have in GCS
    """
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ai-research-451903-6fb81b030f50.json"
    try:
        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()

        # Get the bucket object
        bucket = storage_client.bucket(bucket_name)

        # Create a blob object
        blob = bucket.blob(destination_name)

        # Set content type based on image extension
        image_extensions = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        _, ext = os.path.splitext(image_path.lower())
        content_type = image_extensions.get(ext, 'application/octet-stream')
        
        # Upload the image with appropriate content type
        blob.upload_from_filename(image_path, content_type=content_type)

        print(f"Image {image_path} uploaded to {destination_name} in bucket {bucket_name}")
        

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# take single photo
def take_single_photo():
    return

# take certain number of photos, with certain intervals
def take_multi_photos(NUM_PHOTOS, INTERVAL):
    return

# prompt user to enter settings and take picture
def prompt():

    # camera settings questions
    def prompt_settings():
        print("Focus Setting (): ")
        global focus_setting
        focus_setting = input()
        if focus_setting == "": # TODO
            return
        
        print("Brightness Setting (): ")
        global brightness_setting
        brightness_setting = input()
        if brightness_setting == "": # TODO
            return
    
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
            take_single_photo()
        
        else:
            print("How many seconds inbetween each picture?")
            interval = input()
            take_multi_photos(num_pics, interval)

def main():
    
    global first
    first = True
    while True:
        prompt()

if __name__ == "__main__":
    main()

