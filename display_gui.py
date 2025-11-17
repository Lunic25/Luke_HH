#!/usr/bin/env python3
"""
HydroHalo GUI v2 (single-file)
- tkinter-safe (no blocking in main thread)
- countdown uses root.after()
- MotorController abstraction (placeholder + serial/VESC hook)
- Settings persisted to settings.json
- Session logging to session_log.txt
- Safe shutdown and thread cleanup

Save as display_gui_v2.py (or replace your display_gui.py)
Run: python3 display_gui_v2.py
"""

import os
import sys
import json
import threading
import time
import traceback
from datetime import datetime
import platform
import tkinter as tk
from tkinter import messagebox

# Optional imports (only used if available)
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

# --------- Configuration / Defaults ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # ensure relative files load from repo dir

SETTINGS_PATH = os.path.join(SCRIPT_DIR, "settings.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "session_log.txt")

DEFAULT_SETTINGS = {
    "use_gpio": False,        # disabled while nothing is wired
    "use_sound": True,
    "default_duration": 10,   # seconds (for quick testing)
    "motor_mode": "placeholder"  # "placeholder" or "vesc_serial"
}

# --------- Utility: detect Raspberry Pi ----------
def is_raspberry_pi():
    try:
        # fast heuristic
        if sys.platform.startswith("linux"):
            try:
                with open("/proc/device-tree/model", "r") as f:
                    model = f.read().lower()
                    if "raspberry" in model:
                        return True
            except Exception:
                pass
        # fallback to uname hostname check
        return "raspberrypi" in platform.uname().node.lower()
    except Exception:
        return False

ON_PI = is_raspberry_pi()

# --------- Settings management ----------
def load_settings():
    try:
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ensure keys
                for k, v in DEFAULT_SETTINGS.items():
                    data.setdefault(k, v)
                return data
    except Exception as e:
        print("⚠️ Failed to load settings:", e)
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print("⚠️ Failed to save settings:", e)

# --------- Session logging ----------
def log_session(level, duration):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"{ts} | Level:{level} | Duration:{duration}s\n"
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        print("📝", entry.strip())
    except Exception as e:
        print("⚠️ Logging error:", e)

# --------- MotorController abstraction ----------
class MotorController:
    """
    Controls motor-based resistance.
    Modes:
      - placeholder: no hardware, simulates output (safe for dev)
      - vesc_serial: outline to send serial commands to a VESC (you'll supply port and protocol)
    """

    def __init__(self, settings):
        self.settings = settings
        self.mode = settings.get("motor_mode", "placeholder")
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        # placeholder motor state
        self.current_level = None
        # serial attributes (if you implement)
        self.serial_port = None
        self.serial_baud = 115200

    # Public API
    def start(self, level):
        """Start continuous resistance at a given level (Low/Medium/High/custom %)"""
        with self._lock:
            self.current_level = level
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
        print(f"MotorController: start({level})")

    def stop(self):
        """Stop resistance"""
        with self._lock:
            self._running = False
        # join briefly for cleanliness
        if self._thread:
            self._thread.join(timeout=0.5)
            self._thread = None
        # ensure hardware off
        self._hw_set_off()
        print("MotorController: stop()")

    def _run_loop(self):
        """Background loop that issues motor commands at a safe rate"""
        try:
            while True:
                with self._lock:
                    if not self._running:
                        break
                    level = self.current_level
                # issue a single-control call (non-blocking, short)
                self._hw_set_level(level)
                # sleep a bit but responsive
                time.sleep(0.25)
        except Exception as e:
            print("⚠️ MotorController loop error:", e)
        finally:
            self._hw_set_off()

    # Hardware-level implementations (edit when wiring)
    def _hw_set_level(self, level):
        """Map level string to hardware command. Placeholder prints; implement serial or GPIO here."""
        # Example mapping (you can change to percentages or currents)
        if self.mode == "placeholder":
            # simulate output — for debug only
            print(f"[SIM] Motor set to {level}")
            return

        if self.mode == "vesc_serial":
            # Example skeleton: send packet to VESC via serial
            # TODO: implement proper vesc protocol (pyvesc or custom)
            try:
                # Example: self._send_serial(f"SET_LEVEL {level}\n".encode())
                pass
            except Exception as e:
                print("⚠️ Serial write failed:", e)
            return

        # Add other modes/hardware as needed

    def _hw_set_off(self):
        if self.mode == "placeholder":
            print("[SIM] Motor OFF")
            return
        if self.mode == "vesc_serial":
            try:
                # TODO: send stop command
                pass
            except Exception as e:
                print("⚠️ Serial stop failed:", e)

    # If using serial - a helper (not implemented fully)
    def _send_serial(self, data_bytes):
        # Example: open serial port and write (you may want persistent open)
        # import serial
        # with serial.Serial(self.serial_port, self.serial_baud, timeout=0.5) as ser:
        #     ser.write(data_bytes)
        raise NotImplementedError("Serial sending is not implemented; fill _send_serial with your protocol.")

# --------- GUI class (tkinter) ----------
class HydroHaloGUI:
    def __init__(self, root, settings):
        self.root = root
        self.settings = settings
        self.motor = MotorController(settings)
        self._countdown_job = None
        self._countdown_remaining = 0

        # build UI
        self._setup_root()
        self._build_widgets()

    def _setup_root(self):
        self.root.title("HydroHalo")
        self.root.configure(bg="black")
        # scaling fix for Pi
        try:
            if ON_PI:
                self.root.tk.call('tk', 'scaling', 1.0)
        except Exception:
            pass
        # ensure working dir
        self.root.geometry("800x480")
        self.root.minsize(600, 360)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self):
        # Logo (optional)
        if Image and os.path.exists(os.path.join(SCRIPT_DIR, "hydrohalo_logo.png")):
            try:
                img = Image.open(os.path.join(SCRIPT_DIR, "hydrohalo_logo.png"))
                img = img.resize((140, 140))
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(self.root, image=photo, bg="black")
                lbl.image = photo
                lbl.pack(pady=6)
            except Exception as e:
                print("⚠️ Logo load:", e)
        else:
            tk.Label(self.root, text="HYDROHALO", fg="#45FFFF", bg="black",
                     font=("Helvetica", 28, "bold")).pack(pady=8)

        tk.Label(self.root, text="Select Resistance Level:", fg="white", bg="black",
                 font=("Helvetica", 16)).pack(pady=8)

        self.level_frame = tk.Frame(self.root, bg="black")
        self.level_frame.pack(pady=6)

        self.levels = ["Low", "Medium", "High", "Custom"]
        for i, lvl in enumerate(self.levels):
            b = tk.Button(self.level_frame, text=lvl, width=12, height=2,
                          command=lambda l=lvl: self.open_duration_dialog(l),
                          bg="#45FFFF", fg="black", font=("Helvetica", 12, "bold"))
            b.grid(row=i//2, column=i%2, padx=8, pady=8)

        # Controls
        self.status_var = tk.StringVar()
        platform_info = "Raspberry Pi" if ON_PI else "PC/Mac"
        self.status_var.set(f"{platform_info} | GPIO: {'Enabled' if self.settings.get('use_gpio') else 'Disabled'}")
        status_bar = tk.Label(self.root, textvariable=self.status_var, fg="gray", bg="black",
                              font=("Helvetica", 10), anchor="w")
        status_bar.pack(side="bottom", fill="x", padx=6, pady=4)

        self.extra_frame = tk.Frame(self.root, bg="black")
        self.extra_frame.pack(pady=8)

        tk.Button(self.extra_frame, text="View Session History", command=self.open_history,
                  width=18, bg="#AAAAFF", fg="black").grid(row=0, column=0, padx=5)
        tk.Button(self.extra_frame, text="Settings", command=self.open_settings,
                  width=12, bg="#FFD700", fg="black").grid(row=0, column=1, padx=5)

    # ---------- Dialogs ----------
    def open_duration_dialog(self, level):
        dlg = tk.Toplevel(self.root)
        dlg.title(f"{level} duration")
        dlg.configure(bg="black")
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text=f"Set duration for {level}:", fg="white", bg="black",
                 font=("Helvetica", 12)).pack(pady=8)
        # Options
        options = [5, 10, 12, 15]
        var = tk.IntVar(value=self.settings.get("default_duration", 10))
        menu = tk.OptionMenu(dlg, var, *options)
        menu.config(bg="black", fg="white")
        menu.pack(pady=6)

        countdown_label = tk.Label(dlg, text="", fg="#00BFFF", bg="black", font=("Helvetica", 12))
        countdown_label.pack(pady=8)

        def on_start():
            duration = int(var.get())
            countdown_label.config(text=f"{level} engaged for {duration}s")
            # start motor & countdown
            self.start_resistance_cycle(level, duration, countdown_label, confirm_btn)
            confirm_btn.config(state="disabled")
            dlg.after(duration*1000 + 2000, lambda: (confirm_btn.config(state="normal") if confirm_btn.winfo_exists() else None, dlg.destroy()))
        confirm_btn = tk.Button(dlg, text="Start", command=on_start, bg="#45FFFF", fg="black")
        confirm_btn.pack(pady=6)
        tk.Button(dlg, text="Cancel", command=dlg.destroy, bg="#FF6B6B", fg="white").pack(pady=4)

    def open_history(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Session History")
        dlg.configure(bg="black")
        dlg.geometry("600x400")

        label = tk.Label(dlg, text="HydroHalo Session Log", fg="#45FFFF", bg="black", font=("Helvetica", 14))
        label.pack(pady=8)

        frame = tk.Frame(dlg, bg="black")
        frame.pack(expand=True, fill="both", padx=10, pady=6)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(frame, bg="black", fg="white", wrap="word", yscrollcommand=scrollbar.set)
        text.pack(expand=True, fill="both")
        scrollbar.config(command=text.yview)

        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
                    text.insert("1.0", content if content.strip() else "No sessions recorded yet.")
            else:
                text.insert("1.0", "No sessions recorded yet.")
        except Exception as e:
            text.insert("1.0", f"Error reading log: {e}")
        text.config(state="disabled")

        def clear_log():
            if messagebox.askyesno("Clear Log", "Clear all session history?"):
                try:
                    with open(LOG_PATH, "w", encoding="utf-8") as f:
                        f.write("")
                    text.config(state="normal")
                    text.delete("1.0", tk.END)
                    text.insert("1.0", "Log cleared.")
                    text.config(state="disabled")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to clear log: {e}")
        tk.Button(dlg, text="Clear Log", command=clear_log, bg="#FF6B6B", fg="white").pack(pady=6)

    def open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.configure(bg="black")
        dlg.transient(self.root)
        dlg.grab_set()
        tk.Label(dlg, text="HydroHalo Settings", fg="#45FFFF", bg="black", font=("Helvetica", 14)).pack(pady=8)

        gpio_var = tk.BooleanVar(value=self.settings.get("use_gpio", False))
        sound_var = tk.BooleanVar(value=self.settings.get("use_sound", True))
        motor_mode_var = tk.StringVar(value=self.settings.get("motor_mode", "placeholder"))
        tk.Checkbutton(dlg, text="Enable GPIO (Raspberry Pi)", variable=gpio_var, bg="black", fg="white").pack(pady=4)
        tk.Checkbutton(dlg, text="Enable Sound Alerts", variable=sound_var, bg="black", fg="white").pack(pady=4)
        tk.Label(dlg, text="Motor Mode:", fg="white", bg="black").pack(pady=4)
        tk.OptionMenu(dlg, motor_mode_var, "placeholder", "vesc_serial").pack(pady=2)

        def save():
            self.settings["use_gpio"] = bool(gpio_var.get())
            self.settings["use_sound"] = bool(sound_var.get())
            self.settings["motor_mode"] = motor_mode_var.get()
            save_settings(self.settings)
            messagebox.showinfo("Settings", "Settings saved")
            # reconfigure motor if mode changed
            self.motor.mode = self.settings.get("motor_mode", "placeholder")
            dlg.destroy()
        tk.Button(dlg, text="Save", command=save, bg="#45FFFF", fg="black").pack(pady=6)
        tk.Button(dlg, text="Cancel", command=dlg.destroy, bg="#FF6B6B", fg="white").pack(pady=4)

    # ---------- Resistance cycle ----------
    def start_resistance_cycle(self, level, duration_seconds, status_label, control_button):
        """
        Starts motor and countdown. Non-blocking.
        - level: "Low"/"Medium"/"High"/"Custom"
        - duration_seconds: int
        - status_label: Label to show remaining time
        - control_button: will be disabled until done
        """
        # Safety: stop any running cycle first
        self.stop_resistance_cycle()  # ensures single cycle at a time

        # start motor (background thread inside MotorController)
        self.motor.start(level)
        log_session(level, duration_seconds)

        # prepare countdown state
        self._countdown_remaining = duration_seconds
        status_label.config(text=f"Time remaining: {self._format_time(self._countdown_remaining)}")
        control_button_ref = control_button  # keep ref for closure

        def tick():
            # each second update
            if self._countdown_remaining <= 0:
                status_label.config(text="✅ Resistance cycle complete!")
                self.motor.stop()
                # optional sound
                self._play_sound()
                # re-enable control button if still present
                if control_button_ref and control_button_ref.winfo_exists():
                    control_button_ref.config(state="normal")
                return
            self._countdown_remaining -= 1
            status_label.config(text=f"Time remaining: {self._format_time(self._countdown_remaining)}")
            # schedule next tick in 1 second
            self._countdown_job = self.root.after(1000, tick)

        # start ticking immediately (1s resolution)
        self._countdown_job = self.root.after(1000, tick)

    def stop_resistance_cycle(self):
        # cancel countdown job
        if self._countdown_job:
            try:
                self.root.after_cancel(self._countdown_job)
            except Exception:
                pass
            self._countdown_job = None
        # stop motor
        self.motor.stop()

    @staticmethod
    def _format_time(seconds):
        m, s = divmod(max(0, int(seconds)), 60)
        return f"{m:02d}:{s:02d}"

    # ---------- Audio ----------
    def _play_sound(self):
        if not self.settings.get("use_sound", True):
            return
        try:
            if ON_PI:
                # try aplay
                os.system("aplay /usr/share/sounds/alsa/Front_Center.wav >/dev/null 2>&1 &")
            else:
                # simple beep on desktop (may not work on all OS)
                if sys.platform.startswith("win"):
                    import winsound
                    winsound.Beep(1000, 400)
                else:
                    print("\a", end="", flush=True)
        except Exception as e:
            print("🔇 Sound failed:", e)

    # ---------- Shutdown ----------
    def _on_close(self):
        # Stop everything then destroy
        try:
            self.stop_resistance_cycle()
        except Exception:
            pass
        try:
            # short wait to let motor thread stop gracefully
            time.sleep(0.05)
        except Exception:
            pass
        self.root.destroy()

# --------- Main entrypoint ----------
def main():
    settings = load_settings()
    # show warning if on Pi but GPIO disabled
    if ON_PI and not settings.get("use_gpio", False):
        print("ℹ️ Running on Pi with GPIO disabled in settings (safe default).")

    root = tk.Tk()
    app = HydroHaloGUI(root, settings)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception:
        traceback.print_exc()
    finally:
        # ensure motor stopped on exit
        try:
            app.motor.stop()
        except Exception:
            pass
        print("Shutdown complete")

if __name__ == "__main__":
    main()
