import multiprocessing
import customtkinter as ctk
from gui.main_window import MotorControlApp
from utils.constants import APPEARANCE_MODE, DEFAULT_COLOR_THEME

def main():
    # Essencial para Windows ao usar multiprocessing
    multiprocessing.freeze_support()
    
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(DEFAULT_COLOR_THEME)
    
    app = MotorControlApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()