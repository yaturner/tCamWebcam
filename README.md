# tCam Webcam

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

`tCamWebcam` is a Python utility designed to interface with **tCam** and **tCam-Mini** thermal imaging cameras. It captures raw radiometric thermal streams over local network sockets and bridges them to a web page.

This allows you to seamlessly integrate your thermal camera feed into any web browser. For example this can be used to monitor your 3D printer to verify print bed and nozzle temperatures during printing

<img width="1266" height="1037" alt="image" src="https://github.com/user-attachments/assets/a38100c1-a6bd-49fa-a55d-f1ef0363529b" />


## Features

- **Network-to-Web Page Bridge:** Real-time capture and decoding of radiometric thermal data streams via TCP/IP.
- **Webcam Output:** Exposes the processed stream on a web page in a web browser (e.g. Chrome) 
- **Color Palette Mapping:** Real-time application of thermal colormaps (e.g., Ironbow, Rainbow, Jet, Magma).
- **Lightweight & Modular:** Built with Python for easy integration into custom automation or analysis workflows.

## Prerequisites

### Hardware
- A **tCam** or **tCam-Mini** thermal camera.
- A local network connection between your host computer and the camera.

### Software (Linux/Ubuntu)
To expose the stream as a virtual webcam, you need the V4L2 loopback kernel module:

```bash
sudo apt update
sudo apt install v4l2loopback-dkms v4l2loopback-utils
# Load the module to create /dev/video9
sudo modprobe v4l2loopback video_nr=9 card_label="tCam Virtual Webcam" exclusive_caps=1
```


## Installation

### Clone the repository


git clone [https://github.com/yaturner/tCamWebcam.git](https://github.com/yaturner/tCamWebcam.git)
cd tCamWebcam

## Usage

Run the primary application by specifying your camera's IP address:

```Bash
python webcam.py --ip <CAMERA_IP_ADDRESS>
```


## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
Built for use with tCam/tCam-Mini thermal imaging hardware and software from [Dan Julio Designs](https://danjuliodesigns.com/products/tcam_mini.html)
