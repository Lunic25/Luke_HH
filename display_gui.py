#!/usr/bin/env python3
"""
HydroHalo GUI Application - Raspberry Pi Fixed Version
Fixed Pi-specific issues with countdown threading and window scaling
"""

import tkinter as tk
from tkinter import messagebox, font as tkfont
from PIL import Image, ImageTk
import os
import platform
import threading
import time
from datetime import datetime
import sys
import traceback
import subprocess


def is_raspberry_pi():
    """Detect if running on Raspberry Pi with multiple methods"""
    try:
        # Method 1: Check platform
        if "raspberrypi" in platform.uname().node.lower():
            return True
        
        # Method 2: Check for Pi-specific files
        pi_indicators = [
            '/proc/device-tree/model',
            '/usr/bin/vcgencmd',
            '/sys/firmware/devicetree/base/model'
        ]
        
        for indicator in pi_indicators:
            if os.path.exists(indicator):
                try:
                    with open(indicator, 'r') as f:
                        content = f.read().lower()
                        if 'raspberry pi' in content:
                            return True
                except:
                    pass
        
        return False
    except:
        return False


on_pi = is_raspberry_pi()
print(f"🔍 Running on: {'Raspberry Pi' if on_pi else 'PC/Mac'}")

# GPIO setup with better error handling
use_gpio = on_pi
use_sound = True
GPIO = None
RESISTANCE_PIN = 18

if on_pi:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RESISTANCE_PIN, GPIO.OUT)
        GPIO.output(RESISTANCE_PIN, GPIO.LOW)  # Start with resistance OFF
        print("✅ GPIO initialized successfully")
    except ImportError:
        print("⚠️ RPi.GPIO not available")
        use_gpio = False
        GPIO = None
    except Exception as e:
        print(f"⚠️ GPIO setup failed: {e}")
        use_gpio = False
        GPIO = None
else:
    print("ℹ️ Not on Raspberry Pi - GPIO disabled")


# GUI setup with Pi-specific fixes
root = tk.Tk()
root.title("HydroHalo Startup")
root.configure(bg="black")

# Fix for Pi scaling issues
if on_pi:
    # Force proper DPI and scaling on Pi
    try:
        root.tk.call('tk', 'scaling', 1.0)
    except:
        pass

# Get screen dimensions with fallbacks
try:
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    print(f"📺 Screen detected: {screen_width}x{screen_height}")
except:
    # Fallback dimensions for common Pi setups
    if on_pi:
        screen_width, screen_height = 800, 480  # Common Pi display
        print("📺 Using fallback Pi screen size: 800x480")
    else:
        screen_width, screen_height = 1920, 1080  # Standard fallback
        print("📺 Using fallback screen size: 1920x1080")

# Responsive window setup with Pi fixes
if on_pi:
    # For Pi, use more conservative sizing
    if screen_width <= 800:  # Small Pi displays
        window_width = screen_width
        window_height = screen_height
        x_position = 0
        y_position = 0
        root.attributes("-fullscreen", True)
        print("🖥️ Pi small display detected - using fullscreen")
    else:
        # Larger Pi displays
        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
else:
    # PC/Mac scaling
    window_width = int(screen_width * 0.9)
    window_height = int(screen_height * 0.9)
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 2

# Apply size and position
root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
root.minsize(600, 400)

# Global variables for threading
stop_countdown = False
active_threads = []
thread_lock = threading.Lock()


def cleanup_on_exit():
    """Clean up resources on exit"""
    global stop_countdown
    with thread_lock:
        stop_countdown = True
    
    print("🧹 Cleaning up resources...")
    
    # Wait for threads to finish
    for thread in active_threads:
        if thread.is_alive():
            thread.join(timeout=1.0)
    
    # Cleanup GPIO
    if use_gpio and GPIO:
        try:
            GPIO.output(RESISTANCE_PIN, GPIO.LOW)
            GPIO.cleanup()
            print("✅ GPIO cleanup completed")
        except Exception as e:
            print(f"⚠️ GPIO cleanup failed: {e}")


# Bind cleanup to window close
root.protocol("WM_DELETE_WINDOW", lambda: (cleanup_on_exit(), root.destroy()))


def load_logo():
    """Load logo with multiple fallback paths and Pi-specific handling"""
    try:
        logo_paths = [
            os.path.join(os.path.dirname(__file__), "hydrohalo_logo.png"),
            "hydrohalo_logo.png",
            os.path.join(os.getcwd(), "hydrohalo_logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "hydrohalo_logo.png")
        ]
        
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                # Adjust logo size for Pi
                logo_size = 150 if on_pi and screen_width <= 800 else 250
                logo_img = Image.open(logo_path).resize((logo_size, logo_size))
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(root, image=logo_photo, bg="black")
                logo_label.image = logo_photo  # Keep reference
                logo_label.pack(pady=10 if on_pi else 20)
                print(f"🖼️ Logo loaded from: {logo_path}")
                return True
        
        # Create text logo if image not found
        logo_text = "HYDROHALO" if on_pi else "[Logo Missing]"
        logo_size = 24 if on_pi else 32
        tk.Label(root, text=logo_text, fg="#45FFFF", bg="black", 
                font=("Helvetica", logo_size, "bold")).pack(pady=20)
        print("⚠️ Logo file not found - using text logo")
        return False
    except Exception as e:
        print(f"⚠️ Logo loading failed: {e}")
        tk.Label(root, text="[Logo Error]", fg="red", bg="black", 
                font=("Helvetica", 24)).pack(pady=20)
        return False


load_logo()

# Title & Labels with Pi-responsive fonts
if on_pi and screen_width <= 800:
    title_font = ("Helvetica", 28, "bold")
    label_font = ("Helvetica", 14)
    button_font = ("Helvetica", 12, "bold")
    small_font = ("Helvetica", 10)
else:
    title_font = ("Helvetica", 36, "bold")
    label_font = ("Helvetica", 18)
    button_font = ("Helvetica", 14, "bold")
    small_font = ("Helvetica", 12)

tk.Label(root, text="HydroHalo", fg="#45FFFF", bg="black", 
        font=title_font).pack()
tk.Label(root, text="Select Resistance Level:", fg="white", bg="black", 
        font=label_font).pack(pady=10 if on_pi else 20)


def safe_gui_update(widget, **kwargs):
    """Safely update GUI from any thread with better error handling"""
    try:
        if widget and hasattr(widget, 'winfo_exists') and widget.winfo_exists():
            for key, value in kwargs.items():
                widget.config(**{key: value})
            return True
    except Exception as e:
        print(f"⚠️ GUI update error: {e}")
    return False


def start_countdown(duration_seconds, display_label, level):
    """Start countdown timer with improved Pi threading"""
    global stop_countdown, active_threads
    
    try:
        print(f"⏱️ Starting {level} countdown for {duration_seconds}s")
        log_session(level, duration_seconds)
        
        # Turn on resistance
        if use_gpio and GPIO:
            try:
                GPIO.output(RESISTANCE_PIN, GPIO.HIGH)
                print(f"🔌 Resistance ON for {level}")
            except Exception as e:
                print(f"⚠️ GPIO output failed: {e}")

        # Countdown loop with better thread safety
        for remaining in range(duration_seconds, 0, -1):
            # Check stop flag with lock
            with thread_lock:
                if stop_countdown:
                    print("⏹️ Countdown stopped")
                    break
            
            mins, secs = divmod(remaining, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            
            # Use root.after for thread-safe GUI updates
            root.after(0, lambda t=time_str: safe_gui_update(display_label, text=f"Time remaining: {t}"))
            
            # Sleep with interruption check
            for _ in range(10):  # Check every 0.1 seconds
                with thread_lock:
                    if stop_countdown:
                        break
                time.sleep(0.1)
            
            with thread_lock:
                if stop_countdown:
                    break

        # Completion handling
        with thread_lock:
            if not stop_countdown:
                root.after(0, lambda: safe_gui_update(display_label, text="✅ Resistance cycle complete!"))
                root.after(0, lambda: flash_label(display_label))
                root.after(0, play_sound)

        # Turn off resistance
        if use_gpio and GPIO:
            try:
                GPIO.output(RESISTANCE_PIN, GPIO.LOW)
                print(f"🔌 Resistance OFF for {level}")
            except Exception as e:
                print(f"⚠️ GPIO cleanup failed: {e}")
                
    except Exception as e:
        print(f"⚠️ Countdown error: {e}")
        root.after(0, lambda: safe_gui_update(display_label, text=f"❌ Error: {str(e)}"))
    finally:
        # Clean up thread reference
        current_thread = threading.current_thread()
        with thread_lock:
            if current_thread in active_threads:
                active_threads.remove(current_thread)
        print(f"🧵 Countdown thread finished")


def flash_label(label, count=6):
    """Flash label color using after() method with Pi compatibility"""
    def toggle_color(flash_count):
        if flash_count <= 0 or not label.winfo_exists():
            return
        
        try:
            current_color = label.cget("fg")
            new_color = "red" if current_color == "#00BFFF" else "#00BFFF"
            label.config(fg=new_color)
            root.after(500, lambda: toggle_color(flash_count - 1))
        except Exception as e:
            print(f"⚠️ Flash error: {e}")
    
    root.after(0, lambda: toggle_color(count))


def play_sound():
    """Play completion sound with Pi-specific handling"""
    if not use_sound:
        return
    try:
        if on_pi:
            # Try multiple sound methods on Pi
            sound_commands = [
                'aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null &',
                'aplay /usr/share/sounds/alsa/Front_Left.wav 2>/dev/null &',
                'paplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null &',
                'echo -e "\a"'  # Terminal bell as fallback
            ]
            
            for cmd in sound_commands:
                try:
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("🔊 Pi sound played")
                    break
                except:
                    continue
        else:
            try:
                import winsound
                winsound.Beep(1000, 500)
                print("🔊 PC sound played")
            except ImportError:
                print("🔇 Sound not available")
    except Exception as e:
        print(f"🔇 Sound playback failed: {e}")


def log_session(level, duration_seconds):
    """Log session to file with better error handling"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | Level: {level} | Duration: {duration_seconds} seconds\n"
        
        log_file_path = "session_log.txt"
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
        print(f"📝 Session logged: {log_entry.strip()}")
    except Exception as e:
        print(f"⚠️ Logging failed: {e}")


def select_level(level):
    """Open level selection window with Pi-responsive design"""
    try:
        # Window sizing for Pi
        if on_pi and screen_width <= 800:
            time_window = tk.Toplevel(root)
            time_window.title(f"{level} Timer")
            time_window.geometry("350x250")
        else:
            time_window = tk.Toplevel(root)
            time_window.title(f"{level} Resistance Duration")
            time_window.geometry("400x300")
        
        time_window.configure(bg="black")
        time_window.transient(root)
        time_window.grab_set()
        
        # Center the window
        time_window.update_idletasks()
        ww = time_window.winfo_width()
        wh = time_window.winfo_height()
        wx = (time_window.winfo_screenwidth() // 2) - (ww // 2)
        wy = (time_window.winfo_screenheight() // 2) - (wh // 2)
        time_window.geometry(f"+{wx}+{wy}")

        tk.Label(time_window, text=f"Set duration for {level} resistance:", 
                fg="white", bg="black", font=label_font).pack(pady=15 if on_pi else 20)

        time_options = {"5 seconds": 5, "10 seconds": 10, "12 seconds": 12, "15 seconds": 15}
        
        selected_label = tk.StringVar(time_window)
        selected_label.set(list(time_options.keys())[0])

        option_menu = tk.OptionMenu(time_window, selected_label, *time_options.keys())
        option_menu.config(bg="black", fg="white", font=button_font)
        option_menu.config(highlightbackground="black", highlightthickness=1)
        option_menu.pack(pady=10)

        countdown_label = tk.Label(time_window, text="", fg="#00BFFF", bg="black", 
                                  font=small_font)
        countdown_label.pack(pady=10)

        def confirm_time():
            try:
                label_text = selected_label.get()
                duration = time_options[label_text]
                countdown_label.config(text=f"{level} resistance engaged for {label_text}")

                global stop_countdown, active_threads
                with thread_lock:
                    stop_countdown = False
                
                # Create and start thread
                thread = threading.Thread(
                    target=start_countdown, 
                    args=(duration, countdown_label, level), 
                    daemon=True
                )
                
                with thread_lock:
                    active_threads.append(thread)
                
                thread.start()
                print(f"🚀 Started {level} thread")
                
                # Disable button temporarily
                confirm_btn.config(state="disabled")
                # Re-enable after duration + buffer
                root.after(duration * 1000 + 2000, lambda: confirm_btn.config(state="normal") if confirm_btn.winfo_exists() else None)
                
            except Exception as e:
                print(f"⚠️ Confirm time error: {e}")
                safe_gui_update(countdown_label, text=f"❌ Error: {str(e)}")

        confirm_btn = tk.Button(time_window, text="Start", command=confirm_time, 
                               bg="#45FFFF", fg="black", font=button_font)
        confirm_btn.pack(pady=10)
        
        cancel_btn = tk.Button(time_window, text="Cancel", command=time_window.destroy,
                              bg="#FF6B6B", fg="white", font=button_font)
        cancel_btn.pack(pady=5)
        
    except Exception as e:
        print(f"⚠️ Select level error: {e}")
        messagebox.showerror("Error", f"Failed to open level selection: {str(e)}")


def view_session_history():
    """View session history window with Pi-responsive design"""
    try:
        # Window sizing for Pi
        if on_pi and screen_width <= 800:
            history_window = tk.Toplevel(root)
            history_window.title("Session History")
            history_window.geometry("500x400")
        else:
            history_window = tk.Toplevel(root)
            history_window.title("Session History")
            history_window.geometry("600x500")
        
        history_window.configure(bg="black")

        tk.Label(history_window, text="HydroHalo Session Log", fg="#45FFFF", bg="black", 
                font=label_font).pack(pady=10)
        
        frame = tk.Frame(history_window, bg="black")
        frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        text_area = tk.Text(frame, wrap="word", bg="black", fg="white", 
                           font=small_font, yscrollcommand=scrollbar.set)
        text_area.pack(expand=True, fill="both")
        scrollbar.config(command=text_area.yview)

        try:
            with open("session_log.txt", "r", encoding="utf-8") as log_file:
                content = log_file.read()
                if content.strip():
                    text_area.insert("1.0", content)
                else:
                    text_area.insert("1.0", "No sessions recorded yet.")
        except FileNotFoundError:
            text_area.insert("1.0", "No session history found.")
        except Exception as e:
            text_area.insert("1.0", f"Error reading log file: {str(e)}")
        
        text_area.config(state="disabled")
        
        def clear_log():
            try:
                if messagebox.askyesno("Clear Log", "Clear all session history?"):
                    with open("session_log.txt", "w") as log_file:
                        log_file.write("")
                    text_area.config(state="normal")
                    text_area.delete("1.0", tk.END)
                    text_area.insert("1.0", "Log cleared.")
                    text_area.config(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear log: {str(e)}")
        
        tk.Button(history_window, text="Clear Log", command=clear_log,
                 bg="#FF6B6B", fg="white", font=button_font).pack(pady=5)
        
    except Exception as e:
        print(f"⚠️ History viewer error: {e}")
        messagebox.showerror("Error", f"Failed to open history: {str(e)}")


def open_settings():
    """Open settings window with Pi-responsive design"""
    try:
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.configure(bg="black")
        settings_window.transient(root)
        settings_window.grab_set()

        tk.Label(settings_window, text="HydroHalo Settings", fg="#45FFFF", bg="black", 
                font=label_font).pack(pady=10)

        global use_gpio, use_sound
        
        gpio_var = tk.BooleanVar(value=use_gpio)
        sound_var = tk.BooleanVar(value=use_sound)

        tk.Checkbutton(settings_window, text="Enable GPIO (Raspberry Pi)", variable=gpio_var, 
                      bg="black", fg="white", font=button_font,
                      selectcolor="black").pack(pady=5)
        tk.Checkbutton(settings_window, text="Enable Sound Alerts", variable=sound_var, 
                      bg="black", fg="white", font=button_font,
                      selectcolor="black").pack(pady=5)

        def save_settings():
            global use_gpio, use_sound
            use_gpio = gpio_var.get()
            use_sound = sound_var.get()
            print(f"⚙️ Settings updated: GPIO={use_gpio}, Sound={use_sound}")
            
            success_label = tk.Label(settings_window, text="✅ Settings saved", 
                                   fg="#00FF00", bg="black", font=small_font)
            success_label.pack(pady=10)
            
            settings_window.after(2000, settings_window.destroy)

        tk.Button(settings_window, text="Save", command=save_settings, 
                 bg="#45FFFF", fg="black", font=button_font).pack(pady=10)
        
        tk.Button(settings_window, text="Cancel", command=settings_window.destroy,
                 bg="#FF6B6B", fg="white", font=button_font).pack(pady=5)
        
    except Exception as e:
        print(f"⚠️ Settings error: {e}")
        messagebox.showerror("Error", f"Failed to open settings: {str(e)}")


# Resistance Buttons with Pi-responsive sizing
levels = ["Low", "Medium", "High", "Custom"]
button_frame = tk.Frame(root, bg="black")
button_frame.pack(pady=15 if on_pi else 20)

# Calculate button sizes based on screen
if on_pi and screen_width <= 800:
    btn_width = 10
    btn_height = 2
    btn_padx = 8
    btn_pady = 8
else:
    btn_width = 15
    btn_height = 2
    btn_padx = 10
    btn_pady = 5

for i, lvl in enumerate(levels):
    btn = tk.Button(button_frame, text=lvl, command=lambda l=lvl: select_level(l), 
                   width=btn_width, height=btn_height, bg="#45FFFF", fg="black", 
                   font=button_font)
    btn.grid(row=i//2, column=i%2, padx=btn_padx, pady=btn_pady)


# Extra Buttons with Pi sizing
extra_frame = tk.Frame(root, bg="black")
extra_frame.pack(pady=10)

if on_pi and screen_width <= 800:
    extra_btn_width = 18
    extra_btn_padx = 5
else:
    extra_btn_width = 20
    extra_btn_padx = 5

tk.Button(extra_frame, text="View Session History", command=view_session_history, 
         width=extra_btn_width, height=2, bg="#AAAAFF", fg="black", 
         font=button_font).grid(row=0, column=0, padx=extra_btn_padx, pady=5)

tk.Button(extra_frame, text="Settings", command=open_settings, 
         width=extra_btn_width, height=2, bg="#FFD700", fg="black", 
         font=button_font).grid(row=0, column=1, padx=extra_btn_padx, pady=5)


# Status bar with Pi info
status_var = tk.StringVar()
platform_info = f"{'Raspberry Pi' if on_pi else 'PC/Mac'}"
if on_pi:
    platform_info += f" ({screen_width}x{screen_height})"
status_var.set(f"Platform: {platform_info} | GPIO: {'Enabled' if use_gpio else 'Disabled'}")
status_bar = tk.Label(root, textvariable=status_var, fg="gray", bg="black", 
                     font=small_font, anchor="w")
status_bar.pack(side="bottom", fill="x", padx=5, pady=2)


# Run loop
print("🚀 HydroHalo GUI starting...")
try:
    root.mainloop()
except KeyboardInterrupt:
    print("\n⚠️ Keyboard interrupt received")
except Exception as e:
    print(f"💥 Fatal error: {e}")
    traceback.print_exc()
finally:
    cleanup_on_exit()
    print("👋 HydroHalo GUI shutdown complete")


# End