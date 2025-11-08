import tkinter as tk
from PIL import Image, ImageTk
import os
import platform
import threading
import time
from datetime import datetime

# --- Detect Raspberry Pi ---
on_pi = "raspberrypi" in platform.uname().node.lower()

# --- GPIO setup ---
use_gpio = on_pi
use_sound = True
if on_pi:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    RESISTANCE_PIN = 18
    GPIO.setup(RESISTANCE_PIN, GPIO.OUT)

# --- GUI setup ---
root = tk.Tk()
root.title("HydroHalo Startup")
root.configure(bg="black")

# --- Responsive window setup ---
root.update_idletasks()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Scale to 90% of available screen
window_width = int(screen_width * 0.9)
window_height = int(screen_height * 0.9)
x_position = (screen_width - window_width) // 2
y_position = (screen_height - window_height) // 2

# Apply size and position
root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
root.minsize(600, 400)

# Auto fullscreen for small displays
if screen_width < 1000 or screen_height < 600:
    root.attributes("-fullscreen", True)

# Handle resize gracefully
def on_resize(event):
    root.update_idletasks()

root.bind("<Configure>", on_resize)

# --- Logo Section ---
logo_path = os.path.join(os.path.dirname(__file__), "hydrohalo_logo.png")
if os.path.exists(logo_path):
    logo_img = Image.open(logo_path).resize((250, 250))
    logo_photo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(root, image=logo_photo, bg="black")
    logo_label.image = logo_photo
    logo_label.pack(pady=20)
else:
    tk.Label(root, text="[Logo Missing]", fg="white", bg="black", font=("Arial", 24)).pack(pady=40)

# --- Title & Labels ---
tk.Label(root, text="HydroHalo", fg="#45FFFF", bg="black", font=("Helvetica", 36, "bold")).pack()
tk.Label(root, text="Select Resistance Level:", fg="white", bg="black", font=("Helvetica", 18)).pack(pady=20)

# --- Countdown & Logic Functions ---
def start_countdown(duration_seconds, display_label, level):
    log_session(level, duration_seconds)
    if use_gpio and on_pi:
        GPIO.output(RESISTANCE_PIN, GPIO.HIGH)

    for remaining in range(duration_seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        display_label.config(text=f"Time remaining: {time_str}")
        time.sleep(1)

    display_label.config(text="✅ Resistance cycle complete!")
    flash_label(display_label)
    play_sound()

    if use_gpio and on_pi:
        GPIO.output(RESISTANCE_PIN, GPIO.LOW)

def flash_label(label, count=6):
    def toggle():
        current_color = label.cget("fg")
        label.config(fg="red" if current_color == "#00BFFF" else "#00BFFF")
    for i in range(count):
        label.after(i * 500, toggle)

def play_sound():
    if not use_sound:
        return
    try:
        if on_pi:
            os.system('aplay /usr/share/sounds/alsa/Front_Center.wav')
        else:
            import winsound
            winsound.Beep(1000, 500)
    except Exception as e:
        print("🔇 Sound playback failed:", e)

def log_session(level, duration_seconds):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} | Level: {level} | Duration: {duration_seconds} seconds\n"
    with open("session_log.txt", "a") as log_file:
        log_file.write(log_entry)
    print("📝 Session logged:", log_entry.strip())

# --- Resistance Level Selection ---
def select_level(level):
    time_window = tk.Toplevel(root)
    time_window.title(f"{level} Resistance Duration")
    time_window.geometry("400x250")
    time_window.configure(bg="black")

    tk.Label(time_window, text=f"Set duration for {level} resistance:", fg="white", bg="black", font=("Helvetica", 16)).pack(pady=20)

    time_options = {"5 seconds": 5, "10 seconds": 10, "12 seconds": 12, "15 seconds": 15}
    selected_label = tk.StringVar(time_window)
    selected_label.set("Time")
    tk.OptionMenu(time_window, selected_label, *time_options.keys()).pack(pady=10)

    countdown_label = tk.Label(time_window, text="", fg="#00BFFF", bg="black", font=("Helvetica", 14))
    countdown_label.pack(pady=10)

    def confirm_time():
        label = selected_label.get()
        duration = time_options[label]
        countdown_label.config(text=f"{level} resistance engaged for {label}")
        threading.Thread(target=start_countdown, args=(duration, countdown_label, level), daemon=True).start()

    tk.Button(time_window, text="Confirm", command=confirm_time, bg="#45FFFF", fg="black", font=("Helvetica", 12, "bold")).pack(pady=10)

# --- Session History Viewer ---
def view_session_history():
    history_window = tk.Toplevel(root)
    history_window.title("Session History")
    history_window.geometry("500x400")
    history_window.configure(bg="black")

    tk.Label(history_window, text="HydroHalo Session Log", fg="#45FFFF", bg="black", font=("Helvetica", 18)).pack(pady=10)
    text_area = tk.Text(history_window, wrap="word", bg="black", fg="white", font=("Helvetica", 12))
    text_area.pack(expand=True, fill="both", padx=10, pady=10)

    try:
        with open("session_log.txt", "r") as log_file:
            text_area.insert("1.0", log_file.read())
    except FileNotFoundError:
        text_area.insert("1.0", "No session history found.")

# --- Settings Menu ---
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("400x250")
    settings_window.configure(bg="black")

    tk.Label(settings_window, text="HydroHalo Settings", fg="#45FFFF", bg="black", font=("Helvetica", 18)).pack(pady=10)

    gpio_var = tk.BooleanVar(value=use_gpio)
    sound_var = tk.BooleanVar(value=use_sound)

    tk.Checkbutton(settings_window, text="Enable GPIO", variable=gpio_var, bg="black", fg="white", font=("Helvetica", 14)).pack(pady=5)
    tk.Checkbutton(settings_window, text="Enable Sound Alerts", variable=sound_var, bg="black", fg="white", font=("Helvetica", 14)).pack(pady=5)

    def save_settings():
        global use_gpio, use_sound
        use_gpio = gpio_var.get()
        use_sound = sound_var.get()
        print(f"Settings updated: GPIO={use_gpio}, Sound={use_sound}")
        tk.Label(settings_window, text="✅ Settings saved", fg="#00FF00", bg="black", font=("Helvetica", 12)).pack(pady=10)

    tk.Button(settings_window, text="Save", command=save_settings, bg="#45FFFF", fg="black", font=("Helvetica", 12, "bold")).pack(pady=10)

# --- Resistance Buttons ---
levels = ["Low", "Medium", "High", "Custom"]
for lvl in levels:
    tk.Button(root, text=lvl, command=lambda l=lvl: select_level(l), width=15, height=2, bg="#45FFFF", fg="black", font=("Helvetica", 14, "bold")).pack(pady=5)

# --- Extra Buttons ---
tk.Button(root, text="View Session History", command=view_session_history, width=20, height=2, bg="#AAAAFF", fg="black", font=("Helvetica", 12, "bold")).pack(pady=10)
tk.Button(root, text="Settings", command=open_settings, width=20, height=2, bg="#FFD700", fg="black", font=("Helvetica", 12, "bold")).pack(pady=5)

# --- Run loop ---
root.mainloop()

# --- Cleanup GPIO on exit ---
if on_pi:
    GPIO.cleanup()

#End
