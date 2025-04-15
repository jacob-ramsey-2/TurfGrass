# NVIDIA Jetson Orin NX Setup Guide

This guide provides step-by-step instructions for setting up and configuring your NVIDIA Jetson Orin NX development kit, made by Seeed and sold as the reComputer J4012.


## Understanding AI Environments
Typically, open-source AI models are available via Docker containers. Containerization allows a consistancy of operating system and application environment on runtime. Watch this [video](https://www.youtube.com/watch?v=rIrNIzy6U_g) to understand the basics.

## Hardware Reset

1. To reset the operating system of the kit, you will need a linux host machine 
2. Follow the instructions [here](https://wiki.seeedstudio.com/reComputer_J4012_Flash_Jetpack/)
3. Once booted up on the ReComputer, execute these commands in the terminal:
    ```bash
    sudo apt-get install python3-pip
    sudo apt-mark hold nvidia-l4t-bootloader nvidia-l4t-kernel nvidia-l4t-kernel-dtbs nvidia-l4t-kernel-headers
    sudo pip3 install jetson-stats
    // now restart the device
    ```
4. Follow the [instructions](https://www.jetson-ai-lab.com/tips_ssd-docker.html) to install docker runtime

## Software Requirements
When settting up your NVIDIA developer kit, you are goint to want to have a couple of things installed:

Follow this [video](https://www.youtube.com/watch?v=-KAyUHzRxHc) to install the required dependencies and get started using AI models.

## Docker 
Docker containers are extremely powerful and allow you to create an isolated environment on yuor jetson to run machine learning models. This ensures continuity between environments you are running the model in.

Here are some resources to learn about Docker:
1. https://www.youtube.com/watch?v=0K-I1jOxBL0&list=PLXYLzZ3XzIbhLxc2SA5JjL_ggJ3aMxuX-&index=1&pp=iAQB
2. https://www.youtube.com/watch?v=HlH3QkS1F5Y&list=PLXYLzZ3XzIbhLxc2SA5JjL_ggJ3aMxuX-&index=2&pp=iAQB 

# Run SAM Pipeline

1. Install jetson-containers
    ```bash
    git clone https://github.com/dusty-nv/jetson-containers
    bash jetson-containers/install.sh
    ```

2. Build the SAM image by following the [system setup](https://github.com/dusty-nv/jetson-containers/blob/master/docs/setup.md) and build:
    ```bash
    cd jetson-containers
    jetson-containers build sam
    ```

3. Run the docker image in a container that has USB passthrough access:

    ``` bash
    jetson-containers run --device=/dev/bus -i -t --runtime nvidia --entrypoint  bin/bash sam:r36.4.0
    ```
4. Once inside the container, run Jupyter Labs
    ```bash
    jupyter lab --allow-root
    ```
5. Navigate to the SAM folder inside of /opt and then to Notebooks


6. Open up a terminal in this directory and clone this repostiory and install gphoto2
    ```bash
    git clone https://github.com/jacob-ramsey-2/TurfGrass.git
    apt-get update
    apt-get install libgphoto2-dev
    pip install gphoto2
    ```

7. Run SAM Pipeline

8. OPTIONAL : If you want to monitor GPU usage, in the terminal where you started the docker container, open another tab and run:
    ```bash 
    jtop
    ```
    


## Additional Resources

- [Official NVIDIA Jetson Documentation]()
- [Jetson Developer Forums]()
- [SDK Manager Download]()



## Contributing

Feel free to add your own notes and solutions to common problems you encounter during setup.


