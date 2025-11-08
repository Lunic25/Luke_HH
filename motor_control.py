import tkinter as tk
from pyvesc import VESC

class MotorController:
    def __init__(self, port="/dev/ttyUSB0"):
        try:
            self.vesc = VESC(serial_port=port)
            print("✅ Connected to VESC on", port)
        except Exception as e:
            print("❌ Could not connect to VESC:", e)
            self.vesc = None

    def set_resistance(self, current):
        """Apply active torque (motor drives opposite user pull)."""
        if not self.vesc:
            print("⚠️ VESC not connected.")
            return
        try:
            # Positive current → active torque output
            self.vesc.set_current(current)
            print(f"Applied {current}A torque resistance")
        except Exception as e:
            print("Error:", e)

    def stop(self):
        """Stop torque output (free spin)."""
        if self.vesc:
            self.vesc.set_current(0)
        print("Motor stopped")


class ResistanceGUI:
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        master.title("Active Resistance Control")
        master.attributes('-fullscreen', True)
        master.configure(bg="black")

        tk.Label(master, text="Select Resistance Level",
                 fg="white", bg="black", font=("Arial", 24)).pack(pady=20)

        # Define resistance levels (current in amps)
        self.levels = {
            "Low": 2,
            "Medium": 5,
            "High": 10,
            "Extreme": 15
        }

        for name, current in self.levels.items():
            tk.Button(
                master, text=name,
                font=("Arial", 22, "bold"),
                width=12, height=2,
                bg="#3333aa", fg="white",
                command=lambda c=current: self.controller.set_resistance(c)
            ).pack(pady=15)

        tk.Button(
            master, text="STOP",
            font=("Arial", 24, "bold"),
            width=12, height=2,
            bg="#aa3333", fg="white",
            command=self.controller.stop
        ).pack(pady=30)

        tk.Button(
            master, text="Exit",
            font=("Arial", 18),
            bg="gray", fg="white",
            command=master.destroy
        ).pack(side="bottom", pady=20)


if __name__ == "__main__":
    controller = MotorController("/dev/ttyUSB0")
    root = tk.Tk()
    app = ResistanceGUI(root, controller)
    root.mainloop()

while True:
    pull_force = read_force_sensor()
    line_position = read_line_position()
    
    # Emergency stop if no pull or line near base
    if pull_force <= 0 or line_position <= 1.52:
        stop_motor()
        shutdown_cycle()
        break
    
    # Normal operation
    desired_current = map_resistance_level_to_current(user_selected_level)
    set_motor_current(desired_current)

# vesc_control_safety
import time
import math
from pyvesc import VESC
from pyvesc.protocol import GetValues, SetCurrent  # low-level messages if needed
from pyvesc.VESC import VESC as PyVesc

# --- Hardware / calibration constants (edit these) ---
PORT = "/dev/ttyUSB0"   # change if using UART pins (/dev/ttyS0)
ENC_COUNTS_PER_REV = 8192  # example: encoder CPR * quadrature (set to your encoder value)
MOTOR_POLE_PAIRS = 7       # not needed for length calc but used elsewhere
SPOOL_DIAMETER_M = 0.027   # 27 mm -> meters
SPOOL_CIRCUMFERENCE_M = math.pi * SPOOL_DIAMETER_M

# Safety thresholds
PULL_FORCE_CURRENT_THRESHOLD_A = 0.2  # below this current we consider "no pull" (tune)
RPM_MOVING_THRESHOLD = 5.0            # rpm threshold to consider reel is moving
MAX_ALLOWED_CURRENT_A = 20.0          # ensure this <= VESC limits

# Shutdown reel-in settings
REEL_IN_CURRENT_A = -2.0  # negative to spin motor inward (toward x=0). Tune carefully.
REEL_IN_STEP_DELAY = 0.1  # seconds between checks

# Position target (5 ft -> meters)
STOP_AT_DISTANCE_FT = 5.0
STOP_AT_DISTANCE_M = STOP_AT_DISTANCE_FT * 0.3048

# Init VESC connection
vesc = PyVesc(serial_port=PORT)

def read_telemetry():
    """Get basic telemetry: motor current (A), rpm, and encoder position (counts)."""
    try:
        values = vesc.get_values()  # pyvesc helper
        motor_current = values.current_motor  # motor current (A)
        rpm = values.rpm
        # encoder position: pyvesc's get_values may give 'encoder_pos' or 'abs_pos'; check your version
        enc_pos = getattr(values, "encoder_pos", None) or getattr(values, "abs_pos", None)
        return motor_current, rpm, enc_pos
    except Exception as e:
        print("Telemetry read error:", e)
        return None, None, None

def encoder_counts_to_meters(enc_counts):
    """Convert encoder counts to linear length wound/unwound (meters).
       We assume encoder counts increase as the spool winds out; sign conventions depend on wiring/setup.
    """
    if enc_counts is None:
        return None
    revs = enc_counts / ENC_COUNTS_PER_REV
    length_m = revs * SPOOL_CIRCUMFERENCE_M
    return length_m

def set_current(a):
    """Command motor current (A). Positive = torque in one direction; negative opposite."""
    if abs(a) > MAX_ALLOWED_CURRENT_A:
        print("Requested current exceeds MAX_ALLOWED_CURRENT_A, clamping.")
        a = max(min(a, MAX_ALLOWED_CURRENT_A), -MAX_ALLOWED_CURRENT_A)
    try:
        vesc.set_current(a)
    except Exception as e:
        print("Failed to set current:", e)

def stop_motor():
    print("STOP: setting current to 0.")
    set_current(0.0)

def shutdown_and_reel_in(current_level_a):
    """
    Called when an emergency stop condition is met.
    Gradually reduce user resistance, then slowly reel in to x=0.
    """
    print("Starting shutdown sequence...")
    # 1) Gradually ramp down resistance (if currently applying positive current)
    for a in [current_level_a * f for f in (0.6, 0.3, 0.1)]:
        set_current(a)
        time.sleep(0.3)

    # 2) Start slow reeling inward (negative current)
    print("Reeling in slowly...")
    set_current(REEL_IN_CURRENT_A)
    while True:
        _, rpm, enc_pos = read_telemetry()
        if enc_pos is None:
            print("No encoder feedback; aborting reel-in.")
            break
        length_m = encoder_counts_to_meters(enc_pos)
        if length_m is None:
            print("Invalid length; aborting.")
            break
        if length_m <= 0.01:  # near 0 meters, consider fully retracted
            print("Reached x=0 (or within 1cm).")
            break
        time.sleep(REEL_IN_STEP_DELAY)

    # 3) Final stop
    stop_motor()
    print("Shutdown & reel-in complete.")

# --- Main control loop (example) ---
def main_loop(user_selected_current):
    """
    Loop that:
     - Sends the selected resistance current while user operating
     - Monitors telemetry for emergency conditions:
         * Pull force = 0 -> immediate stop + shutdown
         * Line position <= 5 ft when pulling back -> immediate stop + shutdown
    """
    print("Starting main loop. Selected resistance current:", user_selected_current, "A")
    set_current(user_selected_current)

    try:
        while True:
            motor_current, rpm, enc_pos = read_telemetry()

            if motor_current is None:
                print("Telemetry not available; continuing. Check VESC connection.")
                time.sleep(0.2)
                continue

            # Convert encoder counts to meters
            length_m = encoder_counts_to_meters(enc_pos)

            # --- Emergency stop condition 1: pull force = 0 (current low)
            # If motor current drops below threshold and RPM is low (no movement), assume no pull.
            if abs(motor_current) < PULL_FORCE_CURRENT_THRESHOLD_A and abs(rpm) < RPM_MOVING_THRESHOLD:
                print("Emergency STOP: pull force = 0 detected (current low and rpm low).")
                stop_motor()
                shutdown_and_reel_in(user_selected_current)
                break

            # --- Emergency stop condition 2: line pulled back in and <= 5 ft from start
            # We need to detect when user is being pulled back (i.e., direction is reel-in)
            # If length <= 5ft and motion is toward inboard (rpm sign indicates direction), trigger stop
            if length_m is not None:
                if length_m <= STOP_AT_DISTANCE_M and rpm < 0:  # rpm sign depends on VESC setup
                    print(f"Emergency STOP: line <= {STOP_AT_DISTANCE_FT} ft and pulling back detected (length {length_m:.2f} m).")
                    stop_motor()
                    shutdown_and_reel_in(user_selected_current)
                    break

            # Normal operation: ensure motor is holding user-selected current
            # If you want to continuously command it (helps if VESC times out), keep setting.
            set_current(user_selected_current)

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("User requested KeyboardInterrupt, stopping motor.")
        stop_motor()

if __name__ == "__main__":
    # Example usage: user selects a resistance that corresponds to +5 A torque opposing the pull
    USER_SELECTED_CURRENT_A = 5.0
    main_loop(USER_SELECTED_CURRENT_A)

    #How can I test this?