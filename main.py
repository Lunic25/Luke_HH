# main entry point (Kivy GUI + controller logic)import tkinter as tk
import tkinter as tk
import os
import sys

# ---------- GLOBAL CONFIG ----------
BG_COLOR = "#0a0a0a"
BTN_COLOR = "#1f6feb"
BTN_TEXT = "white"
BTN_WIDTH = 18
BTN_HEIGHT = 3
FONT_MAIN = ("Arial", 24, "bold")
FONT_TITLE = ("Arial", 32, "bold")


class HydroHaloApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("HydroHalo Touch UI")
        self.geometry("800x480")
        self.configure(bg=BG_COLOR)
        self.attributes("-fullscreen", True)

        # Pages container
        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(fill="both", expand=True)

        self.pages = {}

        for Page in (HomePage, MotorControlPage, DiagnosticsPage, SettingsPage):
            page_name = Page.__name__
            page = Page(parent=self.container, controller=self)
            self.pages[page_name] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_page("HomePage")

    def show_page(self, page_name):
        page = self.pages[page_name]
        page.tkraise()


# ---------- PAGE: HOME ----------
class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        title = tk.Label(self, text="HydroHalo", fg="white", bg=BG_COLOR, font=FONT_TITLE)
        title.pack(pady=30)

        tk.Button(self, text="Motor Control", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("MotorControlPage")).pack(pady=20)

        tk.Button(self, text="Diagnostics", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("DiagnosticsPage")).pack(pady=20)

        tk.Button(self, text="Settings", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("SettingsPage")).pack(pady=20)


# ---------- PAGE: MOTOR CONTROL ----------
class MotorControlPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        tk.Label(self, text="Motor Control", fg="white", bg=BG_COLOR, font=FONT_TITLE).pack(pady=20)

        tk.Button(self, text="Start Motor", bg="#2ea043", fg="white",
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=self.start_motor).pack(pady=15)

        tk.Button(self, text="Stop Motor", bg="#d73a49", fg="white",
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=self.stop_motor).pack(pady=15)

        tk.Button(self, text="Back", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("HomePage")).pack(pady=30)

    def start_motor(self):
        print("Motor start triggered")  # ← replace with actual motor command

    def stop_motor(self):
        print("Motor stop triggered")  # ← replace with actual motor command


# ---------- PAGE: DIAGNOSTICS ----------
class DiagnosticsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        tk.Label(self, text="Diagnostics", fg="white", bg=BG_COLOR, font=FONT_TITLE).pack(pady=20)

        tk.Button(self, text="Run System Check", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=self.run_check).pack(pady=15)

        tk.Button(self, text="Back", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("HomePage")).pack(pady=30)

    def run_check(self):
        print("Diagnostics running...")  # add Pi hardware checks here


# ---------- PAGE: SETTINGS ----------
class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        tk.Label(self, text="Settings", fg="white", bg=BG_COLOR, font=FONT_TITLE).pack(pady=20)

        tk.Button(self, text="Shutdown Pi", bg="#d73a49", fg="white",
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=self.shutdown).pack(pady=15)

        tk.Button(self, text="Back", bg=BTN_COLOR, fg=BTN_TEXT,
                  width=BTN_WIDTH, height=BTN_HEIGHT, font=FONT_MAIN,
                  command=lambda: controller.show_page("HomePage")).pack(pady=30)

    def shutdown(self):
        os.system("sudo shutdown -h now")


# ---------- RUN APP ----------
if __name__ == "__main__":
    app = HydroHaloApp()
    app.mainloop()
