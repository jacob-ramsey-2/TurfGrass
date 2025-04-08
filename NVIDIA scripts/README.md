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

# Jupyter Labs
Jupyter labs allows you to run notebooks on the local machine.
 
```Bash
pip install jupyterlab // install

jupyter lab // run
```



## Additional Resources

- [Official NVIDIA Jetson Documentation]()
- [Jetson Developer Forums]()
- [SDK Manager Download]()



## Contributing

Feel free to add your own notes and solutions to common problems you encounter during setup.


