import customtkinter as ctk
import threading

class VelocityTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pid_entries = {}
        self.limit_entries = {}
        self.setup_ui()

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10)
        
        # PID Row
        pid_row = ctk.CTkFrame(scroll, fg_color="transparent")
        pid_row.pack(fill="x", padx=10, pady=10)
        pid_row.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.app.create_pid_group(pid_row, "PID Corrente ID", 0, 0, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Corrente IQ", 1, 1, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Velocidade", 2, 2, self.pid_entries)
        
        # Limits
        f_sec = ctk.CTkFrame(scroll); f_sec.pack(fill="x", padx=20, pady=10)
        self.app.create_action_row(f_sec, "Corrente Máx (A):", "---", "Definir", self.app.set_curr, "current", self.limit_entries)
        self.app.create_action_row(f_sec, "Tensão Máx (V):", "---", "Definir", self.app.set_volt, "voltage", self.limit_entries)
        self.app.create_action_row(f_sec, "Velocidade Máx (RPM):", "---", "Definir", self.app.set_speed, "velocity", self.limit_entries)
        
        # Control
        f_ctrl = ctk.CTkFrame(scroll); f_ctrl.pack(fill="x", padx=20, pady=10)
        # BOTÃO REMOVIDO DAQUI
        self.app.create_action_row(f_ctrl, "Velocidade (RPM):", "0.0", "Setar", self.send_velocity, btn_color="#3b8ed0")
        
    def send_velocity(self, val):
        if not self.app.driver_manager.is_connected: return
        try:
            self.app.send_target_safe(float(val), 2) # Usa envio seguro
        except: pass