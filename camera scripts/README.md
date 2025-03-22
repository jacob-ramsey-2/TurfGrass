# Sony A6700 Camera Control Scripts

This repository contains Python scripts for controlling a Sony A6700 camera via USB connection, capturing images, and uploading them to Google Cloud Storage. These scripts are designed to run on Windows Subsystem for Linux (WSL).

## Difference between Scripts
A6700_Photo.py:
   Takes "previews" of a number of photos, at a certain interval. Essentially taking a screenshot of the camera image, without engaging the shutter. These photos are saved to the directory you run the script in, and then saved to a Google Cloud Storage Bucket (the bucket api key needs to be in same directory), and then deleted from local directory.

RAPID_A6700.py:
   Takes "preivews" of a duration of photos (in seconds), and then stitches these images together into a mp3, and saves the mp3 to Google Cloud Storage Bucket (the bucket api key needs to be in same directory).

NoPreview_A6700.py:
   Takes real images at a certain interval. Saves to camera.


## Prerequisites

### 1. WSL Setup (Skip this if on native Linux)
1. Enable WSL on Windows:
   ```powershell
   # Run in PowerShell as Administrator
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```
2. Install Ubuntu (or your preferred Linux distribution) from the Microsoft Store
3. Set WSL 2 as default:
   ```powershell
   wsl --set-default-version 2
   ```

### 2. USB Passthrough Setup
1. Install [USBIPD-WIN](https://github.com/dorssel/usbipd-win/releases) on Windows
2. In your WSL distribution, install the required packages:
   ```bash
   sudo apt update
   sudo apt install linux-tools-generic hwdata
   sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
   ```

### 3. System Dependencies
Install the required system packages in WSL:
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev libgphoto2-dev libgphoto2-port12
```

### 4. Python Environment Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 5. Google Cloud Setup
1. Create a Google Cloud project
2. Enable Google Cloud Storage API
3. Create a service account and download the JSON credentials file
4. Place the credentials file in the project root directory
5. Create a bucket in Google Cloud Storage

## gphoto2 Library Integration

These scripts utilize the powerful gphoto2 library to control the Sony A6700 camera. gphoto2 is an open-source library and command-line utility that provides comprehensive support for digital cameras, including:

- Remote camera control
- Image capture and download
- Camera settings adjustment
- Live view capabilities
- Support for multiple camera models and manufacturers

The Python scripts in this repository use the `gphoto2` Python bindings (`python-gphoto2`) to interface with the camera. This allows for programmatic control of the camera's functions through a clean, Pythonic API.

For more information about gphoto2:
- Official documentation: [http://www.gphoto.org/doc/](http://www.gphoto.org/doc/)
- Supported cameras list: [http://www.gphoto.org/doc/remote/](http://www.gphoto.org/doc/remote/)
- Python bindings documentation: [https://github.com/jim-easterbrook/python-gphoto2](https://github.com/jim-easterbrook/python-gphoto2)

The library is installed as part of the system dependencies (libgphoto2-dev and libgphoto2-port12) mentioned in the Prerequisites section.

## Connecting the Camera

1. Connect the Sony A6700 to your computer via USB
2. In PowerShell (as Administrator), attach the camera to WSL:
   ```powershell
   # List USB devices
   usbipd list

   # Find the Sony camera in the list and note its bus ID
   # Attach the camera to WSL
   usbipd attach --wsl --busid <BUS_ID>
   ```
3. In WSL, verify the camera is detected:
   ```bash
   lsusb | grep Sony
   ```


### For Windows/WSL Users:
1. Connect the Sony A6700 to your computer via USB
2. In PowerShell (as Administrator), attach the camera to WSL:
   ```powershell
   # List USB devices
   usbipd list

   # Find the Sony camera in the list and note its bus ID
   # Attach the camera to WSL
   usbipd attach --wsl --busid <BUS_ID>
   ```
3. In WSL, verify the camera is detected:
   ```bash
   lsusb | grep Sony
   ```

### For Native Linux Users:
1. Connect the Sony A6700 to your computer via USB
2. Verify the camera is detected:
   ```bash
   lsusb | grep Sony
   ```
3. Ensure your user has the necessary permissions:
   ```bash
   sudo usermod -a -G plugdev $USER
   ```
   You may need to log out and back in for the group changes to take effect.

## Camera Settings

The scripts allow control of:
- ISO (100-102400)
- Aperture (f/2.8-f/22.0)
- Shutter Speed (1/8000-30")

## Troubleshooting

1. If the camera isn't detected:
   ```bash
   # Check if gphoto2 can see the camera
   gphoto2 --auto-detect
   ```

2. If you get permission errors:
   ```bash
   # Add your user to the plugdev group
   sudo usermod -a -G plugdev $USER
   ```

3. If the camera connection is unstable:
   - Ensure you're using a high-quality USB cable
   - Try different USB ports
   - Check if the camera is in PC Remote mode

4. If files aren't uploading to Google Cloud:
   - Verify your credentials file is correctly placed
   - Check your Google Cloud Storage bucket permissions
   - Ensure your service account has the necessary permissions

## Common Issues and Solutions

1. "Device Busy" error:
   - Disconnect and reconnect the camera
   - Ensure no other software is accessing the camera
   - Restart the WSL instance:
     ```bash
     wsl --shutdown
     ```

2. Camera not saving images:
   - Verify the camera has a properly formatted memory card
   - Check remaining storage space
   - Ensure the camera is in the correct shooting mode

3. WSL USB connection issues:
   - Reattach the device using usbipd
   - Check if the USB device is properly passed through to WSL
   - Verify USB 3.0 ports are working correctly

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
