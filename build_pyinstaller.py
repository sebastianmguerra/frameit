import os
import subprocess
import sys
import customtkinter

def build():
    # Find customtkinter path for the --add-data argument
    ctk_path = os.path.dirname(customtkinter.__file__)
    
    # We must format the path for pyinstaller's add-data separator (';' on Windows)
    ctk_data = f"{ctk_path};customtkinter"
    unity_capture_data = f"UnityCapture-master;UnityCapture-master"
    bat_data = f"install_vcam_driver.bat;."
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir", 
        "--windowed", # Don't open a console window
        "--icon=snapcam.ico",
        "--name=SnapCam",
        f"--add-data={ctk_data}",
        f"--add-data={unity_capture_data}",
        f"--add-data={bat_data}",
        "main.py"
    ]
    
    print("Running PyInstaller...")
    print(" ".join(cmd))
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\nBuild successful! The executable is located in dist/SnapCam/SnapCam.exe")
    else:
        print("\nBuild failed!")

if __name__ == "__main__":
    build()
