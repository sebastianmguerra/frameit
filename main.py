import os
# MUST be set before cv2 is imported anywhere
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

import sys
import logging
from gui import SnapCamGUI

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    print("Starting SnapCam Virtual Camera App...")
    app = SnapCamGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
