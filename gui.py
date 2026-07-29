import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2

from camera_engine import CameraEngine
from vcam_helper import get_virtual_cam_troubleshooting_instructions

# Set CustomTkinter theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SnapCamGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SnapCam - Virtual Camera Frame Capture for Discord")
        self.geometry("1120x760")
        self.minsize(920, 660)

        # Initialize Camera Engine
        self.engine = CameraEngine()
        self.gallery_photos = []

        # Setup UI
        self._build_ui()

        # Start Camera Engine
        self.engine.start()

        # Start Preview Loop
        self.update_preview()

        # Protocol for graceful window closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        # Grid Configuration
        self.grid_columnconfigure(0, weight=3)  # Main Viewport
        self.grid_columnconfigure(1, weight=1)  # Controls Sidebar
        self.grid_rowconfigure(0, weight=0)     # Header Bar
        self.grid_rowconfigure(1, weight=1)     # Main Body
        self.grid_rowconfigure(2, weight=0)     # Gallery Ribbon

        # ---------------------------------------------------------------------
        # 1. HEADER BAR
        # ---------------------------------------------------------------------
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1c23")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text="📸 SnapCam",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#3b82f6"
        )
        title_label.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        subtitle_label = ctk.CTkLabel(
            header,
            text="Virtual Camera Stream & Photo Capture for Discord / Zoom",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#9ca3af"
        )
        subtitle_label.grid(row=0, column=1, padx=5, pady=12, sticky="w")

        # Header Right Controls: Re-check VCam & Status Badge
        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.grid(row=0, column=2, padx=20, pady=8, sticky="e")

        self.btn_recheck_vcam = ctk.CTkButton(
            header_right,
            text="🔄 Re-check VCam",
            font=ctk.CTkFont(size=11),
            fg_color="#334155",
            hover_color="#475569",
            width=110,
            height=30,
            command=self.on_recheck_vcam
        )
        self.btn_recheck_vcam.pack(side="left", padx=(0, 10))

        self.vcam_badge = ctk.CTkLabel(
            header_right,
            text="Checking Virtual Camera...",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=16,
            fg_color="#374151",
            text_color="#ffffff",
            padx=12,
            pady=4
        )
        self.vcam_badge.pack(side="left")

        # ---------------------------------------------------------------------
        # 2. MAIN VIEWPORT (LEFT PANEL)
        # ---------------------------------------------------------------------
        viewport_frame = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=12)
        viewport_frame.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        viewport_frame.grid_rowconfigure(0, weight=1)
        viewport_frame.grid_columnconfigure(0, weight=1)

        # Video Canvas / Label
        self.video_label = ctk.CTkLabel(viewport_frame, text="", fg_color="#090d16", corner_radius=10)
        self.video_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Left click (Button-1) to resume live, Right click (Button-3) to capture frame
        self.video_label.bind("<Button-1>", lambda e: self.on_resume_click())
        self.video_label.bind("<Button-3>", lambda e: self.on_capture_click())

        # Mode Badge Floating on Viewport Top Left
        self.mode_badge = ctk.CTkLabel(
            viewport_frame,
            text="● LIVE STREAMING",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            text_color="#ffffff",
            corner_radius=8,
            padx=10,
            pady=4
        )
        self.mode_badge.place(relx=0.03, rely=0.04, anchor="nw")

        # Keybind Hint Overlay Bottom Right
        self.hint_label = ctk.CTkLabel(
            viewport_frame,
            text="Right-Click to Freeze • Left-Click to Resume • [SPACE] to Toggle",
            font=ctk.CTkFont(size=11),
            fg_color="#1e293b",
            text_color="#d1d5db",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.hint_label.place(relx=0.97, rely=0.96, anchor="se")

        # Global Spacebar binding to capture/unfreeze
        self.bind("<space>", lambda e: self.toggle_freeze())

        # ---------------------------------------------------------------------
        # 3. CONTROLS SIDEBAR (RIGHT PANEL)
        # ---------------------------------------------------------------------
        sidebar = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=12)
        sidebar.grid(row=1, column=1, padx=(0, 15), pady=15, sticky="nsew")

        sidebar_title = ctk.CTkLabel(
            sidebar,
            text="Controls",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc"
        )
        sidebar_title.pack(padx=15, pady=(15, 10), anchor="w")

        # Primary Action Button: CAPTURE & FREEZE
        self.btn_capture = ctk.CTkButton(
            sidebar,
            text="📸 Capture & Freeze Frame",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=48,
            corner_radius=10,
            command=self.on_capture_click
        )
        self.btn_capture.pack(padx=15, pady=(5, 8), fill="x")

        # Secondary Action Button: RESUME LIVE
        self.btn_resume = ctk.CTkButton(
            sidebar,
            text="▶ Resume Live Camera",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=40,
            corner_radius=10,
            command=self.on_resume_click
        )
        self.btn_resume.pack(padx=15, pady=5, fill="x")

        # Separator
        sep1 = ctk.CTkFrame(sidebar, height=2, fg_color="#334155")
        sep1.pack(padx=15, pady=15, fill="x")

        # Media Options: Save Photo & Load Photo
        btn_save = ctk.CTkButton(
            sidebar,
            text="💾 Save Photo to Disk...",
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            corner_radius=8,
            command=self.on_save_photo
        )
        btn_save.pack(padx=15, pady=5, fill="x")

        btn_load = ctk.CTkButton(
            sidebar,
            text="🖼 Broadcast Image File...",
            font=ctk.CTkFont(size=12),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            corner_radius=8,
            command=self.on_load_image
        )
        btn_load.pack(padx=15, pady=5, fill="x")

        # Separator
        sep2 = ctk.CTkFrame(sidebar, height=2, fg_color="#334155")
        sep2.pack(padx=15, pady=15, fill="x")

        # Camera Device Selector
        cam_label = ctk.CTkLabel(sidebar, text="Webcam Source:", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        cam_label.pack(padx=15, pady=(5, 2), anchor="w")

        cams = self.engine.list_available_cameras()
        cam_options = [f"Camera Device #{c}" for c in cams]
        self.cam_dropdown = ctk.CTkOptionMenu(
            sidebar,
            values=cam_options,
            command=self.on_camera_select,
            fg_color="#0f172a",
            button_color="#334155",
            button_hover_color="#475569"
        )
        self.cam_dropdown.pack(padx=15, pady=(0, 10), fill="x")

        # Driver Installer & Help Button
        btn_install_driver = ctk.CTkButton(
            sidebar,
            text="⚡ Register VCam Driver...",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            height=36,
            corner_radius=8,
            command=self.on_install_vcam_driver
        )
        btn_install_driver.pack(padx=15, pady=(10, 5), fill="x")

        btn_help = ctk.CTkButton(
            sidebar,
            text="❓ Virtual Cam Setup Help",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color="#94a3b8",
            hover_color="#334155",
            command=self.show_vcam_help
        )
        btn_help.pack(padx=15, pady=(5, 10), fill="x", side="bottom")

        # Initial VCam badge state check
        self.after(500, self.update_vcam_badge)

    def update_vcam_badge(self):
        if self.engine.vcam_active:
            self.vcam_badge.configure(
                text=f"● Discord VCam {self.engine.vcam_status}",
                fg_color="#16a34a",
                text_color="#ffffff"
            )
        else:
            self.vcam_badge.configure(
                text="⚠️ VCam Driver Setup Needed",
                fg_color="#d97706",
                text_color="#ffffff"
            )

    def on_recheck_vcam(self):
        active = self.engine.retry_vcam_connection()
        self.update_vcam_badge()
        if active:
            messagebox.showinfo("Virtual Camera Active", f"Virtual Camera successfully connected:\n{self.engine.vcam_status}")
        else:
            messagebox.showwarning("Virtual Camera Driver Needed", 
                "Virtual camera is not yet registered.\n\nClick '⚡ Register VCam Driver' or run 'install_vcam_driver.bat' as Administrator.")

    def on_install_vcam_driver(self):
        bat_path = os.path.abspath("install_vcam_driver.bat")
        if os.path.exists(bat_path):
            try:
                subprocess.Popen(['cmd.exe', '/c', 'start', '', bat_path], shell=True)
                messagebox.showinfo("Driver Installer Launched", 
                    "Launched the Virtual Camera Driver Installer window.\n\nAccept the Administrator prompt, let it complete, then click '🔄 Re-check VCam'!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch installer: {e}")
        else:
            messagebox.showerror("File Not Found", f"Could not find install_vcam_driver.bat at:\n{bat_path}")

    def toggle_freeze(self):
        if self.engine.mode == CameraEngine.MODE_LIVE:
            self.on_capture_click()
        else:
            self.on_resume_click()

    def on_capture_click(self):
        success = self.engine.capture_frame()
        if success:
            self.mode_badge.configure(
                text="📷 FRAME FROZEN (DISCORD BROADCAST)",
                fg_color="#2563eb"
            )
            rgb_frame = self.engine.get_output_frame_rgb()
            if rgb_frame is not None:
                self.add_to_gallery(rgb_frame)

    def on_resume_click(self):
        self.engine.resume_live()
        self.mode_badge.configure(
            text="● LIVE STREAMING",
            fg_color="#16a34a"
        )

    def on_camera_select(self, choice_str):
        try:
            idx = int(choice_str.split("#")[-1])
            self.engine.switch_camera(idx)
        except ValueError:
            pass

    def add_to_gallery(self, rgb_array):
        try:
            pil_img = Image.fromarray(rgb_array)
            thumb_pil = pil_img.copy()
            thumb_pil.thumbnail((90, 60), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=thumb_pil, dark_image=thumb_pil, size=(90, 60))

            bgr_saved = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

            def use_snapshot(saved_bgr=bgr_saved):
                with self.engine.lock:
                    self.engine.frozen_frame = saved_bgr.copy()
                    self.engine.mode = CameraEngine.MODE_FROZEN
                self.mode_badge.configure(
                    text="📷 GALLERY PHOTO BROADCASTING",
                    fg_color="#8b5cf6"
                )

            btn = ctk.CTkButton(
                self.gallery_scroll,
                image=ctk_img,
                text="",
                width=95,
                height=65,
                fg_color="#334155",
                hover_color="#2563eb",
                corner_radius=6,
                command=use_snapshot
            )
            btn.pack(side="left", padx=5, pady=2)
        except Exception as e:
            print("Gallery add error:", e)

    def on_save_photo(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*.*")]
        )
        if file_path:
            saved = self.engine.save_current_frame(file_path)
            if saved:
                messagebox.showinfo("Photo Saved", f"Photo successfully saved to:\n{file_path}")

    def on_load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All Files", "*.*")]
        )
        if file_path:
            loaded = self.engine.load_custom_image(file_path)
            if loaded:
                self.mode_badge.configure(
                    text="🖼 CUSTOM IMAGE BROADCASTING",
                    fg_color="#8b5cf6"
                )

    def show_vcam_help(self):
        instructions = get_virtual_cam_troubleshooting_instructions()
        top = ctk.CTkToplevel(self)
        top.title("Virtual Camera Setup Guide")
        top.geometry("550x420")
        top.attributes("-topmost", True)

        txt = ctk.CTkTextbox(top, font=ctk.CTkFont(size=13), wrap="word")
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        txt.insert("0.0", instructions)
        txt.configure(state="disabled")

    def update_preview(self):
        """Renders current frame in the GUI canvas at ~15fps.
        Kept slower than vcam (30fps) to avoid CPU contention."""
        rgb_frame = self.engine.get_output_frame_rgb()

        if rgb_frame is not None:
            lbl_w = max(self.video_label.winfo_width(), 320)
            lbl_h = max(self.video_label.winfo_height(), 240)

            pil_img = Image.fromarray(rgb_frame)
            pil_img.thumbnail((lbl_w, lbl_h), Image.Resampling.BILINEAR)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
            self.video_label.configure(image=ctk_img)

        if self.engine.running:
            self.after(66, self.update_preview)  # ~15fps preview

    def on_closing(self):
        self.engine.stop()
        self.destroy()

if __name__ == "__main__":
    app = SnapCamGUI()
    app.mainloop()
