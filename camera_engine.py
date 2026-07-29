import os
import cv2
import time
import threading
import numpy as np
from PIL import Image, ImageDraw
import logging

try:
    import pyvirtualcam
    PYVIRTUALCAM_AVAILABLE = True
except ImportError:
    PYVIRTUALCAM_AVAILABLE = False

logger = logging.getLogger("SnapCam.Engine")
logging.basicConfig(level=logging.INFO)

class CameraEngine:
    MODE_LIVE = "LIVE"
    MODE_FROZEN = "FROZEN"
    MODE_CUSTOM_IMAGE = "CUSTOM_IMAGE"

    def __init__(self, camera_index=0, target_width=1280, target_height=720, fps=30):
        self.camera_index = camera_index
        self.target_width = target_width
        self.target_height = target_height
        self.fps = fps

        self.mode = self.MODE_LIVE
        self.cap = None
        self.vcam = None
        self.vcam_status = "Not Initialized"
        self.vcam_error_msg = ""
        self.camera_status = "Scanning..."

        # Frame stores (BGR format for OpenCV/PyVirtualCam compatibility)
        self.current_live_frame = None
        self.frozen_frame = None
        self.custom_image_frame = None
        self.synthetic_frame = self._generate_synthetic_frame()
        self.lock = threading.Lock()

        # Threading flags
        self.running = False
        self.capture_thread = None
        self.vcam_thread = None

        # Stats
        self.actual_fps = 0.0
        self.vcam_active = False

    def list_available_cameras(self, max_tested=8):
        """Scans system for accessible OpenCV camera indices safely.
        Tests actual frame reads to filter out phantom/broken devices.
        Scans up to 8 indices since virtual camera driver installs can shift indices."""
        available = []
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]
        
        for idx in range(max_tested):
            found = False
            for backend in backends:
                if found:
                    break
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            available.append(idx)
                            found = True
                        cap.release()
                except Exception:
                    pass
        return available if available else [0]

    def start(self):
        """Starts physical camera capture and virtual camera output threads."""
        if self.running:
            return

        self.running = True
        self._init_physical_camera()
        self._init_virtual_camera()

        # Launch background threads
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        if self.vcam_active:
            self.vcam_thread = threading.Thread(target=self._vcam_loop, daemon=True)
            self.vcam_thread.start()

    def stop(self):
        """Stops all background threads and releases camera devices."""
        self.running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        if self.vcam_thread and self.vcam_thread.is_alive():
            self.vcam_thread.join(timeout=1.0)

        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

        if self.vcam:
            try:
                self.vcam.close()
            except Exception as e:
                logger.error(f"Error closing virtual camera: {e}")
            self.vcam = None

        self.vcam_active = False
        logger.info("Camera Engine stopped.")

    def _try_open_camera_at_index(self, idx):
        """Tries to open a camera at a specific index across all backends.
        Returns the opened cv2.VideoCapture on success, or None."""
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if os.name == 'nt' else [cv2.CAP_ANY]

        # Pass 1: Open with NATIVE resolution (avoids MF_E_INVALIDMEDIATYPE)
        for backend in backends:
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        native_h, native_w = test_frame.shape[:2]
                        self.camera_status = f"Connected (Cam #{idx}, {native_w}x{native_h})"
                        logger.info(f"Opened camera #{idx} via backend {backend} at native {native_w}x{native_h}")
                        return cap
                    else:
                        cap.release()
            except Exception:
                pass

        # Pass 2: Try forcing target resolution
        for backend in backends:
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.camera_status = f"Connected (Cam #{idx})"
                        logger.info(f"Opened camera #{idx} via backend {backend} at forced {self.target_width}x{self.target_height}")
                        return cap
                    else:
                        cap.release()
            except Exception:
                pass

        return None

    def _init_physical_camera(self):
        """Tries opening the physical camera. If the requested index fails,
        auto-scans all indices 0-7 to find any working camera.
        This handles index shifts caused by virtual camera driver installs."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

        # First: try the specifically requested camera index
        cap = self._try_open_camera_at_index(self.camera_index)
        if cap is not None:
            self.cap = cap
            return

        # Fallback: auto-scan all other indices to find a working camera
        logger.info(f"Camera #{self.camera_index} unavailable, auto-scanning other indices...")
        for idx in range(8):
            if idx == self.camera_index:
                continue
            cap = self._try_open_camera_at_index(idx)
            if cap is not None:
                self.camera_index = idx  # Update to the working index
                self.cap = cap
                logger.info(f"Auto-selected working camera at index #{idx}")
                return

        self.camera_status = "No Working Camera Found"
        logger.warning("Could not open any physical camera. Using synthetic canvas.")
        self.cap = None

    def _init_virtual_camera(self):
        """Initializes pyvirtualcam safely, ensuring existing handles are closed first."""
        if self.vcam is not None:
            try:
                self.vcam.close()
            except Exception:
                pass
            self.vcam = None

        if not PYVIRTUALCAM_AVAILABLE:
            self.vcam_status = "pyvirtualcam missing"
            self.vcam_error_msg = "Python pyvirtualcam library is not installed."
            self.vcam_active = False
            return

        try:
            self.vcam = pyvirtualcam.Camera(
                width=self.target_width,
                height=self.target_height,
                fps=self.fps,
                fmt=pyvirtualcam.PixelFormat.BGR
            )
            device_name = getattr(self.vcam, 'device', 'Virtual Camera')
            backend_name = getattr(self.vcam, 'backend', '')
            self.vcam_status = f"Active ({device_name})"
            self.vcam_error_msg = ""
            self.vcam_active = True
            logger.info(f"Virtual camera initialized: {self.vcam_status} via {backend_name}")
        except Exception as e:
            self.vcam_status = "Driver Setup Needed"
            self.vcam_error_msg = str(e)
            self.vcam_active = False
            logger.warning(f"Virtual camera launch warning: {e}")

    def retry_vcam_connection(self):
        """Attempts to re-initialize Virtual Camera if driver was installed."""
        self._init_virtual_camera()
        if self.vcam_active and (self.vcam_thread is None or not self.vcam_thread.is_alive()):
            self.vcam_thread = threading.Thread(target=self._vcam_loop, daemon=True)
            self.vcam_thread.start()
        return self.vcam_active

    def switch_camera(self, camera_index):
        """Switches physical camera source on the fly."""
        with self.lock:
            self.camera_index = camera_index
            self._init_physical_camera()

    def _generate_synthetic_frame(self):
        """Generates a high-quality test card frame if no webcam is connected."""
        img = Image.new("RGB", (self.target_width, self.target_height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        # Grid lines
        for y in range(0, self.target_height, 40):
            draw.line([(0, y), (self.target_width, y)], fill=(30, 41, 59), width=1)
        for x in range(0, self.target_width, 40):
            draw.line([(x, 0), (x, self.target_height)], fill=(30, 41, 59), width=1)

        # Center card box
        box = [(self.target_width//2 - 280, self.target_height//2 - 100),
               (self.target_width//2 + 280, self.target_height//2 + 100)]
        draw.rectangle(box, fill=(30, 41, 59), outline=(59, 130, 246), width=2)
        
        draw.text((self.target_width//2 - 180, self.target_height//2 - 40), 
                  "📷 SnapCam Canvas Active", fill=(248, 250, 252))
        draw.text((self.target_width//2 - 240, self.target_height//2 + 10), 
                  "Load an Image or Connect Webcam to Broadcast", fill=(148, 163, 184))

        rgb_arr = np.array(img)
        return cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

    def _capture_loop(self):
        """Background thread grabbing webcam frames and building the output frame.
        Pre-builds the final output_frame at target dimensions so the vcam loop
        and GUI can read it with zero locking."""
        last_time = time.time()
        frame_count = 0

        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    if frame.shape[1] != self.target_width or frame.shape[0] != self.target_height:
                        frame = cv2.resize(frame, (self.target_width, self.target_height))
                    # Atomic reference swap (safe under CPython GIL)
                    self.current_live_frame = frame
                else:
                    self.current_live_frame = self.synthetic_frame
            else:
                self.current_live_frame = self.synthetic_frame

            # Build the output frame based on current mode
            self._rebuild_output_frame()

            frame_count += 1
            now = time.time()
            if now - last_time >= 1.0:
                self.actual_fps = frame_count / (now - last_time)
                frame_count = 0
                last_time = now

            time.sleep(1.0 / (self.fps * 1.2))

    def _rebuild_output_frame(self):
        """Builds the ready-to-send output frame based on current mode.
        Called by capture loop. Result is read lock-free by vcam and GUI."""
        mode = self.mode  # Read once (atomic)
        if mode == self.MODE_FROZEN and self.frozen_frame is not None:
            frame = self.frozen_frame
        elif mode == self.MODE_CUSTOM_IMAGE and self.custom_image_frame is not None:
            frame = self.custom_image_frame
        elif self.current_live_frame is not None:
            frame = self.current_live_frame
        else:
            frame = self.synthetic_frame

        # Ensure exact target dimensions for vcam
        if frame.shape[1] != self.target_width or frame.shape[0] != self.target_height:
            frame = cv2.resize(frame, (self.target_width, self.target_height))

        # Atomic reference swap — vcam loop and GUI read this lock-free
        self._output_frame = frame

    def _vcam_loop(self):
        """Background thread pushing output frame to pyvirtualcam.
        Reads self._output_frame lock-free (atomic reference read under GIL).
        Guarantees a frame is sent every cycle — no gaps for Unity Capture."""
        fallback = np.zeros((self.target_height, self.target_width, 3), dtype=np.uint8)

        while self.running and self.vcam_active and self.vcam:
            # Lock-free read of pre-built output frame
            frame = getattr(self, '_output_frame', None)
            if frame is None:
                frame = fallback
            
            # Ensure C-contiguous memory for pyvirtualcam (crucial to prevent silent drops/flickering)
            if not frame.flags['C_CONTIGUOUS']:
                frame = np.ascontiguousarray(frame)

            try:
                self.vcam.send(frame)
                # Use native high-precision sleep (fixes Windows 15.6ms jitter issue for Discord WebRTC)
                self.vcam.sleep_until_next_frame()
            except Exception as e:
                logger.error(f"VCam send error: {e}")
                time.sleep(1.0 / self.fps)

    def get_output_frame_bgr(self):
        """Returns current output frame in BGR format. Lock-free read."""
        frame = getattr(self, '_output_frame', None)
        if frame is not None:
            return frame.copy()
        return self.synthetic_frame.copy()

    def get_output_frame_rgb(self):
        """Returns current output frame converted to RGB for GUI rendering."""
        frame = getattr(self, '_output_frame', None)
        if frame is not None:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return cv2.cvtColor(self.synthetic_frame, cv2.COLOR_BGR2RGB)

    def capture_frame(self):
        """Captures current live frame and switches mode to frozen."""
        live = self.current_live_frame
        if live is not None:
            self.frozen_frame = live.copy()
        else:
            self.frozen_frame = self.synthetic_frame.copy()
        self.mode = self.MODE_FROZEN
        self._rebuild_output_frame()
        logger.info("Frame captured and feed frozen.")
        return True

    def resume_live(self):
        """Resumes live webcam streaming to virtual camera."""
        self.mode = self.MODE_LIVE
        self._rebuild_output_frame()
        logger.info("Resumed live feed.")

    def load_custom_image(self, file_path):
        """Loads a static image from disk to broadcast as camera feed."""
        try:
            pil_img = Image.open(file_path).convert("RGB")
            pil_img = pil_img.resize((self.target_width, self.target_height), Image.Resampling.LANCZOS)
            rgb_arr = np.array(pil_img)
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            self.custom_image_frame = bgr_arr
            self.mode = self.MODE_CUSTOM_IMAGE
            self._rebuild_output_frame()
            logger.info(f"Loaded custom image: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load custom image {file_path}: {e}")
            return False

    def save_current_frame(self, file_path):
        """Saves current broadcast frame to disk as photo."""
        frame = self.get_output_frame_bgr()
        if frame is not None:
            cv2.imwrite(file_path, frame)
            return True
        return False

