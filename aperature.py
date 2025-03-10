#!/usr/bin/env python3
import subprocess
import sys
import gphoto2 as gp

def camerainit():
    """Initialize and find the camera."""
    try:
        # Create camera object
        camera = gp.Camera()
        
        # Initialize the camera
        print("Initializing camera...")
        camera.init()
        
        # Get camera information
        camera_info = camera.get_summary()
        print(f"Found camera: {camera_info.text.split('Model:')[1].split('\n')[0].strip()}")
        
        return camera
    except gp.GPhoto2Error as e:
        print(f"Error initializing camera: {e}")
        sys.exit(1)

def list_config_options(camera):
    """List all available configuration options for the camera."""
    try:
        # Get camera configuration
        config = camera.get_config()
        
        # Get all configuration names
        config_names = []
        
        # Function to recursively get all config names
        def get_config_names(config_item):
            count = config_item.count_children()
            if count == 0:
                # This is a leaf node
                name = config_item.get_name()
                if name:
                    config_names.append(name)
            else:
                # This is a section with children
                for i in range(count):
                    child = config_item.get_child(i)
                    get_config_names(child)
        
        # Get all config names
        get_config_names(config)
        return config_names, config
    except gp.GPhoto2Error as e:
        print(f"Error listing configuration options: {e}")
        return [], None

def find_aperture_config(camera):
    """Find the correct aperture configuration option for the camera."""
    config_names, config = list_config_options(camera)
    
    # Common names for aperture settings in different camera models
    aperture_names = ['aperture', 'f-number', 'fnumber', 'f-stop', 'fstop', 'shutterspeed', 'aperture-value']
    
    # Find the first matching aperture config
    aperture_config_name = None
    for name in aperture_names:
        if name in config_names:
            aperture_config_name = name
            print(f"Found aperture configuration as '{name}'")
            break
    
    if not aperture_config_name:
        print("Could not find aperture configuration. Available options are:")
        for name in config_names:
            print(f"- {name}")
        return None, None
    
    # Get the aperture config
    aperture_config = config.get_child_by_name(aperture_config_name)
    return aperture_config, config

def get_available_apertures(camera):
    """Get available aperture settings for the camera."""
    try:
        # Find aperture configuration
        aperture_config, config = find_aperture_config(camera)
        
        if not aperture_config:
            print("Could not find aperture configuration. Make sure your camera is in a mode that allows aperture control.")
            return [], None, None
        
        # Check if this config has choices
        try:
            # Get available choices
            apertures = [choice for choice in aperture_config.get_choices()]
            
            # Get current value
            current_aperture = aperture_config.get_value()
            print(f"Current aperture: {current_aperture}")
            
            return apertures, aperture_config, config
        except gp.GPhoto2Error:
            # This config might not have choices
            print(f"The '{aperture_config.get_name()}' setting doesn't have selectable choices.")
            return [], None, None
            
    except gp.GPhoto2Error as e:
        print(f"Error getting aperture settings: {e}")
        return [], None, None

def set_aperture(camera, aperture_value, aperture_config, config):
    """Set the aperture of the camera."""
    try:
        # Set the new aperture value
        aperture_config.set_value(aperture_value)
        
        # Apply the configuration to the camera
        camera.set_config(config)
        
        print(f"Successfully set aperture to {aperture_value}")
        return True
    except gp.GPhoto2Error as e:
        print(f"Error setting aperture: {e}")
        return False

def main():
    # Initialize and find the camera
    camera = camerainit()
    
    # Get available aperture settings
    available_apertures, aperture_config, config = get_available_apertures(camera)
    
    if not available_apertures:
        print("Could not retrieve aperture settings. Make sure your camera is in the right mode.")
        camera.exit()
        sys.exit(1)
    
    # Display available aperture settings
    print("\nAvailable aperture settings:")
    for i, aperture in enumerate(available_apertures, 1):
        print(f"{i}. {aperture}")
    
    # Prompt user for aperture setting
    while True:
        try:
            choice_idx = int(input("\nEnter the number of your chosen aperture setting: ")) - 1
            
            # Check if the input is valid
            if 0 <= choice_idx < len(available_apertures):
                choice = available_apertures[choice_idx]
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(available_apertures)}.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Set the aperture
    set_aperture(camera, choice, aperture_config, config)
    
    # Clean up
    camera.exit()
    print("Camera connection closed.")

if __name__ == "__main__":
    main()
