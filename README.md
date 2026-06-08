# tCamWebcam

An optimized, low-latency utility bridge that transforms raw radiometric data from the **tCam-mini** thermal imaging camera into a standard MJPEG webcam stream and web dashboard. Built using a multi-threaded Python architecture, it is designed for high-frame-rate performance on single-board computers and embedded Linux environments.

<img width="977" height="1019" alt="image" src="https://github.com/user-attachments/assets/8d72fe4e-8605-4fd0-b2d8-3191db53c014" />



## 🚀 Key Features in `webcam.py`

* **Multi-Threaded Frame Pipeline:** Separates the Flask web server from the camera data acquisition loop. Frame processing and network streaming run on independent threads to eliminate blocking and minimize latency.
* **NumPy-Accelerated Radiometric Processing:** Replaces slow Python loops with vectorized NumPy operations for per-pixel temperature mapping, scaling, and color-mapping.
* **High-Speed Image Manipulations:** Utilizes native NumPy space operations for rapid image rotations and applies high-performance `NEAREST` or `BOX` resampling filters for low-overhead image scaling.
* **Optimized JSON Parsing:** Integrates `orjson` to handle high-throughput command parsing and metadata processing with minimal CPU overhead.
* **Low-Latency Networking:** Leverages tuned TCP socket configurations, including `TCP_NODELAY`, to ensure immediate frame dispatch over the network.
* **Integrated Flask Web Interface:** Serves a lightweight web dashboard that provides a real-time MJPEG live feed alongside camera telemetry.

---

## 🛠️ Architecture Overview

The core of `webcam.py` relies on an asynchronous producer-consumer model:

```
[ tCam-mini Hardware ] 
          │ (Radiometric Data via Sockets / Serial)
          ▼
┌────────────────────────────────────────────────────────┐
│ webcam.py (Data Acquisition Thread)                   │
│  ├── orjson parsing                                   │
│  └── NumPy Vectorized Operations (Scaling/Rotation)   │
└─────────────────────────┬──────────────────────────────┘
                          │ (Thread-Safe Frame Buffer)
                          ▼
┌────────────────────────────────────────────────────────┐
│ Flask Web Server (Streaming Thread)                    │
│  ├── MJPEG Video Stream Generator                      │
│  └── Telemetry & Web UI Endpoints                      │
└─────────────────────────┬──────────────────────────────┘
                          │ (TCP_NODELAY Optimized)
                          ▼
                 [ Web Browser / Client ]

```

---

## 📦 Prerequisites & Installation

### 1. System Dependencies

Ensure your environment is ready for building C-based Python extensions (required for high-performance libraries like `orjson`):

```bash
sudo apt-get update
sudo apt-get install python3-dev build-essential

```

### 2. Python Dependencies

Install the highly optimized pipeline dependencies:

```bash
pip install flask numpy orjson pillow

depending on your local python configuration, addition library installations may be required

```

---

## 🔧 Configuration & Usage

Launch the bridge utility directly by executing the primary script:

```bash
python3 webcam.py --ip <camera ip address> --palette <initial palette name> --rotate_image <degrees

```

### Command Line Arguments

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--ip` | `string` | `192.168.4.1` | The ip address of the camera. |
| `--palette` | `string` | `black_hot` | Inital palette for the camera image. |
| `--rotate_image` | `int` | `0` | Image rotation in degrees (`0`, `90`, `180`, `270`). |
| `--debug_enabled` | `boolean` | false | print useless debugging info (true, false). |

These may also be specified in a **config.json** file, a example of which is included in the repo

Once webcam is running go to your browser and navigate to **hostname:5000**, where **hostname** is the name (or ip address) of the computer where **webcam** is running

---

### Features

- A drop down spinner which allows the user to select the palette used to display the image
- Hotspot feedback, clicking anywhere in the displayed image will report the temperature at that coordinate in the image


## 📈 Performance Engineering Highlights

To maintain a consistent, real-time thermal video stream, the following performance strategies are embedded directly into `webcam.py`:

* **Vectorization over Loops:** Pure Python loops for pixel-by-pixel color lookup or temperature conversion are strictly avoided. Arrays are explicitly cast to NumPy structures, maximizing CPU cache efficiency via `astype()` and vectorized math.
* **Zero-Copy Memory Considerations:** Image data is kept in standard byte/array buffers for as long as possible before being encoded to JPEG, reducing memory allocation thrashing.
* **Non-Blocking Flask Handlers:** The MJPEG stream generator yields frames from a thread-safe global ring buffer, ensuring that sluggish network clients do not slow down the camera's ingestion thread.

---

## 🤝 Contributing

Contributions optimized for speed and efficiency are always welcome. If you find type-casting bugs, race conditions, or further vectorization opportunities, please open an issue or submit a pull request.

---


