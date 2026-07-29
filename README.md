# SnapCam

SnapCam is a Python-based virtual camera application that lets you instantly freeze your webcam feed (perfect for Discord, Zoom, or Teams). It captures your physical webcam and broadcasts it out as a virtual camera. 

With a single click or spacebar press, you can lock your camera frame while you step away, sneeze, or just take a break, without anyone noticing on the other end!

## Features

- **Instant Frame Freeze:** Right-click to freeze, Left-click to resume, or toggle with the Spacebar.
- **Virtual Camera Output:** Uses `pyvirtualcam` and Unity Capture to create a seamless virtual camera that Discord and Zoom recognize natively.
- **Custom Image Broadcasting:** Load any image from your computer to broadcast it as your camera feed.
- **Photo Save:** Save your currently broadcasted frame to disk.
- **Auto-Camera Discovery:** Automatically scans and connects to the correct physical webcam, even when virtual drivers shuffle the indices.

## Requirements

- **OS:** Windows 10/11
- **Virtual Camera Driver:** [Unity Capture](https://github.com/schellingb/UnityCapture) (SnapCam includes a built-in setup button for this!)

## Installation

### Method 1: Windows Installer (Recommended)

The easiest way to get started is to use the standalone installer wizard:
1. Download `SnapCam_Setup_v1.0.exe` from the latest release.
2. Double-click to run the setup wizard.
3. Once installed, launch SnapCam from your Start Menu or Desktop!

### Method 2: Run from Source (For Developers)

If you prefer to run the raw Python code:
1. Clone or download this repository.
2. Ensure you have Python 3.8+ installed.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python main.py
   ```

## Virtual Camera Setup

For Discord or Zoom to see SnapCam, you need a virtual camera driver installed. SnapCam provides a built-in helper for this:

1. Launch SnapCam.
2. Click the **"⚡ Register VCam Driver..."** button in the sidebar.
3. Accept the Administrator prompt (required to register the DirectShow filter).
4. Wait for the installer to finish, then click **"🔄 Re-check VCam"**.
5. You should now see "Active (Unity Video Capture)" at the top right!

In Discord/Zoom, simply select **"Unity Video Capture"** as your webcam.

## Usage

- **Freeze Frame:** Right-click the video preview (or press `Spacebar`).
- **Resume Live Feed:** Left-click the video preview (or press `Spacebar` again).
- **Change Camera:** Use the dropdown menu in the sidebar to switch between connected physical webcams.
- **Load Image:** Click "Broadcast Image File" to replace your camera feed with a static picture.

## Troubleshooting (Discord Flickering)

SnapCam is explicitly optimized to prevent WebRTC frame jitter in Discord. It uses lock-free frame building and native high-precision C++ timers to guarantee a steady 30fps stream. If you experience flickering in Discord, ensure that no other virtual camera software (like OBS Virtual Camera) is actively fighting for the feed.
