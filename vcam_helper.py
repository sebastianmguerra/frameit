import pyvirtualcam
import logging

logger = logging.getLogger("SnapCam.VCamHelper")

def check_virtual_cam_available(width=1280, height=720, fps=30):
    """
    Checks if a virtual camera backend is available on the system.
    Returns (available: bool, info_str: str)
    """
    try:
        # Attempt a dry-run instantiation of PyVirtualCam
        with pyvirtualcam.Camera(width=width, height=height, fps=fps, fmt=pyvirtualcam.PixelFormat.BGR) as cam:
            device_name = getattr(cam, 'device', 'Virtual Camera')
            backend_name = getattr(cam, 'backend', 'Default Backend')
            return True, f"Virtual Camera Ready: {device_name} ({backend_name})"
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Virtual camera initialization failed: {error_msg}")
        return False, f"Virtual Camera Not Found: {error_msg}"

def get_virtual_cam_troubleshooting_instructions():
    """
    Returns markdown/text instructions for enabling OBS Virtual Camera on Windows.
    """
    return """
### Virtual Camera Driver Required (Windows)

To broadcast video to Discord, Zoom, or Web Browsers:

1. **If OBS Studio is installed:**
   - Open OBS Studio once to register its virtual camera driver.
   - Or click "Start Virtual Camera" inside OBS once to initialize the driver.
   - Restart **SnapCam**.

2. **If OBS Studio is NOT installed:**
   - Download & install [OBS Studio](https://obsproject.com/) (Free & Open Source).
   - Alternatively, install [Unity Capture](https://github.com/vrm-c/UnityCapture) DirectShow filter.

3. **In Discord / Zoom Settings:**
   - Go to **Settings -> Voice & Video -> Camera**.
   - Select **OBS Virtual Camera** as your input camera.
"""
