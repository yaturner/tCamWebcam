#!/usr/bin/env python3

'''
webcam demonstrates streaming the frames from a tCam-Mini
to a web page in real time.

author: bitreaper
author: AhJim
'''

import base64
import argparse
import numpy as np
from tcam import TCam
from tkinter import *
from array import array
from PIL import Image, ImageTk, ImageDraw
from threading import Event
import time
import io
import os
import threading
from flask import Flask, Response, render_template_string, send_file, jsonify, Response, request
import queue
import sys
import argparse
import json
from palettes import *
import logging
import socket

# 1. Suppress the startup warning banner
cli = sys.modules.get('flask.cli')
if cli:
    cli.show_server_banner = lambda *x: None

# 2. Disable the Werkzeug logger to stop HTTP request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log.disabled = True

app = Flask(__name__)


# Shared global variables for thread safety
frame_image = None
frame_lock = threading.Lock()
tcam = None
DEBUG_ENABLED = False
CURRENT_PALETTE = black_hot.black_hot_palette
IMAGE_PATH="./thermalImage.jpg"
IP_ADDRESS = "192.168.4.1"
ROTATE_IMAGE = 0
SLEEP_TIME = 0.3
IMAGE_MIN = 0.0
IMAGE_MAX = 0.0
T_LINEAR_RES = 0.01
PALETTE_DATA = {
    "black_hot":black_hot.black_hot_palette,
    "blue_red":blue_red.blue_red_palette,
    "coldest":coldest.coldest_palette,
    "double_rainbow":double_rainbow.double_rainbow_palette,
    "fusion":fusion.fusion_palette,
    "glowbow":glowbow.glowbow_palette,
    "gray":gray.gray_palette,
    "gray_red":gray_red.gray_red_palette,
    "hottest":hottest.hottest_palette,
    "ironblack":ironblack.ironblack_palette,
    "lava":lava.lava_palette,
    "medical":medical.medical_palette,
    "rainbow":rainbow.rainbow_palette,
    "wheel2":wheel2.wheel2_palette
}

chosen = "black_hot" # initial palette - matches spinner
# Frontend HTML Framework, read from disk
HTML_TEMPLATE = ""

#
# Centralized configuration in Python
#
COLORBAR_CONFIG = {
    "min_val": "0 °C",
    "max_val": "85 °C",
    # CSS gradient format: list of hex colors from TOP (max) to BOTTOM (min)
    "current_palette": ["#ff0000", "#ffaa00", "#00ff00", "#00aaff", "#0000ff"],
    "palette_colors" : [palettes],
    "all_palettes": [palettes.keys()]
}

#
# read config from a file if present
#
def load_config(config_path="config.json"):
    """Loads configuration from a JSON file if it exists."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse {config_path}: {e}")
    return {}

#
# read html template from a file if present
#
def load_template(html_path="template.html"):
    """Loads template from a file if it exists."""
    if os.path.exists(html_path):
        try:
            with open(html_path, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Failed to load {html_path}: {e}")
            os._exit()

            
#
# get the min/max values from the camera
#
def get_linear_res():
    global tcam
    
    # OEM Mask 
    #
    COMMAND_OEM_MASK = 0x4000
    
    #
    # Request the RAD T-Linear resolution (RAD 0x0EC4)
    #    Response is 0 for 0.1 C (Low Gain), 1 for 0.01 C (High Gain)
    # 
    rsp = tcam.get_lep_cci(COMMAND_OEM_MASK | 0x0EC4, 2)
    
    #
    # Convert the json response into an array of 2 16-bit words
    #  Index  : Value
    #    0    : Response[15:0]
    #    1    : Response[31:16]
    #
    rsp_vals = rsp["cci_reg"]
    dec_data = base64.b64decode(rsp_vals["data"])
    reg_array = array('H', dec_data)
    if reg_array[0] == 0:
        res = 0.1
    else:
        res = 0.01

    if DEBUG_ENABLED:
        print(f"T-Linear resolution = {res}")
    
    #
    # Request the RAD Spotmeter Value (RAD 0xED0)
    #
    rsp = tcam.get_lep_cci(COMMAND_OEM_MASK | 0x0ED0, 4)

    #
    # Convert the json response into an array of 4 16-bit words
    #  Index  : Value
    #    0    : Spotmeter Value
    #    1    : Spotmeter Max Value
    #    2    : Spotmeter Min Value
    #    3    : Spotmeter Population
    #
    rsp_vals = rsp["cci_reg"]
    dec_data = base64.b64decode(rsp_vals["data"])
    reg_array = array('H', dec_data)
    T_LINEAR_RES = res
    

#
# Generator function that continuously reads the image file
#
def generate_stream():
    global frame_image
    
    if DEBUG_ENABLED:
        print(f"Entering generate_stream")
    while True:
        with frame_lock:
            if not frame_image is None:
                buf = io.BytesIO()
                frame_image.save(buf, format="PNG")
                image_bytes = buf.getvalue()
                # Format the data as a multipart/x-mixed-replace frame
                yield (b'--frame\r\n'
                        b'Content-Type: image/jpg\r\n\r\n' + image_bytes + b'\r\n')
                
        # Adjust sleep time to control the refresh rate (e.g., 0.1s = 10 FPS)
        time.sleep(SLEEP_TIME)

#
# Convert the raw camera data into an array of (r, g, b) values
#
def convert(img):
    global IMAGE_MIN, IMAGE_MAX

    if DEBUG_ENABLED:
        print(f"Enetering convert - CURRENT_PALETTE={CURRENT_PALETTE}")
    
    dimg = base64.b64decode(img["radiometric"])
    nra = np.array(array('H', dimg), dtype=np.uint16)
    
    imgmin = nra.min()
    imgmax = nra.max()
    delta = imgmax - imgmin

    # Create an array of your chosen colors (e.g., 256 colors mapped out)
    palette_lut = np.array(CURRENT_PALETTE, dtype=np.uint8)
    # breakpoint()
    # Normalize your raw radiometric values directly into indices [0-255] 
    # instead of looping through each pixel.
    normalized_frame = (((nra - imgmin) / delta * 255)).astype(np.uint8)

    # 🚀 Instantly apply the palette to the entire frame at once
    rgb_image_array = palette_lut[normalized_frame]

    # Convert the min/max Values into degrees C
    #   Temp = ( Value / (1 / T-Linear Resolution)) - 273.15
    IMAGE_MIN = ( imgmin / (1/T_LINEAR_RES)) - 273.15
    IMAGE_MAX = ( imgmax / (1/T_LINEAR_RES)) - 273.15
    if DEBUG_ENABLED:
        print(f"setting min/max to {IMAGE_MIN}, {IMAGE_MAX}")
    return rgb_image_array

#
# Thread to:
# 1. obtain a frame from the camera
# 2. call convert to make an RGB array
# 3. save the image for Flask to display
#
def camera_thread():
    """Background thread that continuously reads from the camera."""
    global frame_image, tcam, IP_ADDRESS, ROTATE_IMAGE, cam_t

    if DEBUG_ENABLED:
        print("Entering camera_thread")
    # Create the tCam object and connect to it    
    tcam = TCam()
    if DEBUG_ENABLED:
        print(f"connecting to {IP_ADDRESS}")
    stat = tcam.connect(IP_ADDRESS)

    if stat["status"] != "connected":
        print(f"Could not connect to {IP_ADDRESS}")
        print(f"connect returned {stat}")
        tcam.shutdown()
        tcam.disconnect()
        os._exit()
    else:
         get_linear_res()
         ret = tcam.start_stream(delay_msec=0, num_frames=0)
         if DEBUG_ENABLED:
             print(f"Return from start_stream is '{ret}'")
         
    while(True):
        tcam_json = None
        try:
            tcam_json = tcam.get_frame()
            # tcam_json = tcam.get_image()
            if tcam.frameQueue.empty():
                time.sleep(SLEEP_TIME)
                pass
        except queue.Empty:
            if DEBUG_ENABLED:
                print("frameQueue is empty")
            time.sleep(SLEEP_TIME)
            pass
        
        # breakpoint()
        if not tcam_json:  
            if DEBUG_ENABLED:
                print(f"empty response from camera {tcam_json}")
            time.sleep(SLEEP_TIME)
            pass
        else:
            with frame_lock:
                image = convert(tcam_json)
                rgb_array = np.array(image, dtype=np.uint8)
                rgb_grid = rgb_array.reshape(120, 160,3)
                # 1. Rotate instantly in NumPy space before making a PIL image
                # k=1 is 90°, k=2 is 180°, k=3 is 270°. (Pass axes=(0,1) for counter-clockwise)
                if ROTATE_IMAGE == 90:
                    rgb_grid = np.rot90(rgb_grid, k=3) 
                elif ROTATE_IMAGE == 180:
                 rgb_grid = np.rot90(rgb_grid, k=2)
                elif ROTATE_IMAGE == 270:
                    rgb_grid = np.rot90(rgb_grid, k=1)
                    
                # 2. Build the image directly from the pre-rotated NumPy matrix
                frame_image = Image.fromarray(rgb_grid, mode='RGB')
                    
                # 3. Scale using NEAREST or BOX (Dramatically faster than LANCZOS)
                # It completely drops processing time and keeps thermal pixel values intact
                new_size = (frame_image.width * 4, frame_image.height * 4)
                frame_image = frame_image.resize(new_size, resample=Image.Resampling.NEAREST)


@app.route('/')
def index():
    if DEBUG_ENABLED:
        print("/ called")
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    if DEBUG_ENABLED:
        print("/video/feed called")
    # Return a continuous response wrapper with the correct multipart headers
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame")

# DYNAMIC ENDPOINT: This generates new values on every API hit
@app.route('/colorbar_config')
def colorbar_config():
    global IMAGE_MIN, IMAGE_MAX, chosen
    
    if DEBUG_ENABLED:
        print(f"Entering colorbar_config- {IMAGE_MIN}, {IMAGE_MAX}")
    COLORBAR_CONFIG["min_val"] = f"{IMAGE_MIN:2.1f}°C"
    COLORBAR_CONFIG["max_val"] = f"{IMAGE_MAX:2.1f}°C"
    # Convert using list comprehension
    if DEBUG_ENABLED:
        print(f"chosen palette is {chosen}")
    hex_palette = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in PALETTE_DATA[chosen]]
    COLORBAR_CONFIG["current_palette"] = hex_palette
    COLORBAR_CONFIG["palette_colors"] = hex_palette
    COLORBAR_CONFIG["all_palettes"] = list(palettes.keys())
    return jsonify(COLORBAR_CONFIG)


# NEW ENDPOINT: Receives the chosen palette from the UI
@app.route('/select_palette', methods=['POST'])
def select_palette():
    global CURRENT_PALETTE, chosen
    
    data = request.get_json()
    chosen = data.get('palette')
    
    if chosen in list(palettes.keys()):
        CURRENT_PALETTE = PALETTE_DATA[chosen]
        if DEBUG_ENABLED:
            print(f"Python: Palette changed to {chosen}") # Tracks it in your terminal
        hex_palette = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in PALETTE_DATA[chosen]]
        COLORBAR_CONFIG["current_palette"] = hex_palette

        return jsonify({"status": "success", "palette": CURRENT_PALETTE})
    
    
    return jsonify({"status": "error", "message": "Invalid palette"}), 400


########### Main Program ############

if __name__ == '__main__':

    # read the template html
    HTML_TEMPLATE = load_template()
    
    parser = argparse.ArgumentParser()

    parser.prog = "webcam"
    parser.description = f"{parser.prog} - a program to stream images from tCam-mini and display on a web page\n"

    # 1. Load configuration from file first
    config = load_config("config.json")
    
    # 2. Get the IP from config if available, otherwise set a default fallback
    default_ip = config.get("ip", "192.168.4.1")
    ROTATE_IMAGE = config.get("rotate_image", 0)
    chosen="rainbow"
    
    # Passing default_ip here allows CLI args to override the JSON file if explicitly provided
    parser.add_argument(
        "--ip", 
        type=str, 
        default=default_ip, 
        help=f"IP address of the tCam (default: {default_ip})"
    )
    parser.add_argument(
        "--palette", 
        type=str, 
        default=chosen, 
        help="Thermal color palette"
    )

    parser.add_argument(
        "--rotate_image", 
        type=int, 
        default=ROTATE_IMAGE, 
        help="Image Rotation in degrees"
    )


    args = parser.parse_args()

    
    if not args.ip:
        args.ip = "192.168.4.1"
        if DEBUG_ENABLED:
            print(f"Using default of {IP_ADDRESS}")
    else:
        IP_ADDRESS = args.ip

    evt = Event()

    try:
        # 1. Start the camera capture thread in the background
        if DEBUG_ENABLED:
            print("Starting camera thread")
        cam_t = threading.Thread(target=camera_thread, daemon=True)
        cam_t.start()
        
        # 2. Start Flask in the main thread
        # Use threaded=True so Flask can handle multiple browser connections simultaneously
        if DEBUG_ENABLED:
            print("Start Flask in debug mode")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        evt.set()
        root.destroy()
        tcam.shutdown()
