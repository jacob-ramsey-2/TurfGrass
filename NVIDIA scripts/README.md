# NVIDIA Jetson Orin NX Setup Guide

This guide provides step-by-step instructions for setting up and configuring your NVIDIA Jetson Orin NX development kit, made by Seeed and sold as the reComputer J4012.


## Understanding AI Environments
Typically, open-source AI models are available via Docker containers. Containerization allows a consistancy of operating system and application environment on runtime. Watch this [video](https://www.youtube.com/watch?v=rIrNIzy6U_g) to understand the basics.

## Hardware Reset

1. To reset the operating system of the kit, you will need a linux host machine 
2. Follow the instructions [here](https://wiki.seeedstudio.com/reComputer_J4012_Flash_Jetpack/)

## Software Requirements
When settting up your NVIDIA developer kit, you are goint to want to have a couple of things installed:

Follow this [video](https://www.youtube.com/watch?v=-KAyUHzRxHc) to install the required dependencies and get started using AI models.

## Docker 
Docker containers are extremely powerful and allow you to create an isolated environment on yuor jetson to run machine learning models. This ensures continuity between environments you are running the model in.

Here are some resources to learn about Docker:
1. https://www.youtube.com/watch?v=0K-I1jOxBL0&list=PLXYLzZ3XzIbhLxc2SA5JjL_ggJ3aMxuX-&index=1&pp=iAQB
2. https://www.youtube.com/watch?v=HlH3QkS1F5Y&list=PLXYLzZ3XzIbhLxc2SA5JjL_ggJ3aMxuX-&index=2&pp=iAQB 

# To run SAM Pipeline

1. If you haven't built a local docker SAM image, do so by following the system setup and build commands for https://github.com/dusty-nv/jetson-containers

2. Run the docker image in a container that has USB passthrough access:

    ``` bash
    jetson-containers run --device=/dev/bus -i -t --runtime nvidia --entrypoint / bin/bash sam:36.4.0
    ```
3. Once inside the container, run Jupyter Labs
    ```bash
    jupyter lab --allow-root
    ```
4. Navigate to the SAM folder inside of /opt and then to Notebooks


5. Open up a terminal in this directory and clone this repostiory and install gphoto2
    ```bash
    git clone https://github.com/jacob-ramsey-2/TurfGrass.git
    apt-get update
    apt-get install libgphoto2-dev
    pip install gphoto2
    ```

6. Run SAM Pipeline


## Additional Resources

- [Official NVIDIA Jetson Documentation]()
- [Jetson Developer Forums]()
- [SDK Manager Download]()



## Contributing

Feel free to add your own notes and solutions to common problems you encounter during setup.


