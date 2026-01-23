import customtkinter as ctk
import threading
import time
import concurrent.futures
import multiprocessing
from core.driver_manager import DriverManager
from gui.sidebar import Sidebar
from gui.console import Console

# Abas
from gui.tabs.position_tab import PositionTab
from gui.tabs.velocity_tab import VelocityTab
from gui.tabs.data_tab import DataTab
from gui.tabs.current_tab import CurrentTab

from gui.oscilloscope import run_dpg_process
from utils.constants import *

class MotorControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MOB3 Driver Controller - Full v2.4")
        self.geometry(WINDOW_SIZE)
        
        self.serial_lock = threading.Lock()
        self.scope_queue = multiprocessing.Queue()
        self.scope_process = None
        
        self.driver_manager = DriverManager(self.log_to_terminal)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.is_monitoring = False
        self.active_mode_set = None
        self.motor_enabled = False
        self.stop_threads = False

        self.grid_rowconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = Sidebar(self, {
            "show_pos": lambda: self.select_tab("position"),
            "show_vel": lambda: self.select_tab("velocity"),
            "show_curr": lambda: self.select_tab("current"),
            "show_data": lambda: self.select_tab("data"),
            "toggle_power": self.toggle_motor_power,
            "sync": self.manual_sync,
            "open_scope": self.toggle_oscilloscope
        })
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        self.console = Console(self, tab_callback=self.on_console_tab_change)
        self.console.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10))

        self.tabs = {
            "position": PositionTab(self, self),
            "velocity": VelocityTab(self, self),
            "current": CurrentTab(self, self),
            "data": DataTab(self, self)
        }
        
        self.loading_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.loading_label = ctk.CTkLabel(self.loading_overlay, text="Carregando...", font=("Segoe UI", 16))
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.resize_timer = None
        self.last_width = self.winfo_width()
        self.last_height = self.winfo_height()
        self.bind("<Configure>", self.on_resize)

        self.current_tab_name = None
        self.select_tab("position")

        threading.Thread(target=self.auto_connect_loop, daemon=True).start()

    def auto_connect_loop(self):
        while not self.stop_threads:
            status, port, version = self.driver_manager.auto_connect()
            
            if status == "connected":
                self.after(0, lambda: (
                    self.sidebar.update_status(f"Conectado - {port}", COLOR_CONNECTED),
                    self.sidebar.update_version(version)
                ))
                self.log_to_terminal("Conectado! Sincronizando...\n")
                self.manual_sync()
                
            elif status == "lost":
                self.after(0, lambda: self.sidebar.update_status("DESCONECTADO", COLOR_DISCONNECTED))
                self.is_monitoring = False
            
            time.sleep(2.0)

    def manual_sync(self):
        if not self.driver_manager.is_connected: return
        threading.Thread(target=self._sync_task, daemon=True).start()

    def _sync_task(self):
        time.sleep(0.5)
        try:
            d = self.driver_manager.driver
            with self.serial_lock:
                curr = d.get_max_current()
                time.sleep(0.01)
                volt = d.get_max_voltage()
                time.sleep(0.01)
                vel  = d.get_max_velocity()
                time.sleep(0.01)
                status = d.get_status()
                
                # --- LEITURA DO OFFSET ENCODER (VALOR ÚNICO) ---
                enc_offset = None
                if hasattr(d, "get_encoder_offset"):
                    # Agora retorna um único float ou None
                    enc_offset = d.get_encoder_offset() 

            pids = {}
            for m in range(4):
                with self.serial_lock:
                    pids[m] = d.get_pid_parameters(m)
                time.sleep(0.02)

            self.after(0, lambda: self._apply_sync_to_ui(curr, volt, vel, pids, status, enc_offset))
        except Exception as e:
            self.log_to_terminal(f"Sync: {e}\n")

    def _apply_sync_to_ui(self, curr, volt, vel, pids, status, enc_offset=None):
        def update_entry(entry, val):
            if entry and val is not None:
                entry.delete(0, "end")
                try: entry.insert(0, f"{float(val):.4f}")
                except: entry.insert(0, str(val))

        self.motor_enabled = (status == 1)
        self.update_power_btn_ui()

        for tab_name in ["position", "velocity", "current"]:
            tab = self.tabs[tab_name]
            
            # Limites
            if hasattr(tab, "limit_entries"):
                update_entry(tab.limit_entries.get("current"), curr)
                update_entry(tab.limit_entries.get("voltage"), volt)
                update_entry(tab.limit_entries.get("velocity"), vel)
            
            # PIDs
            if hasattr(tab, "pid_entries"):
                for m, val_tuple in pids.items():
                    if m in tab.pid_entries and val_tuple:
                        fields = tab.pid_entries[m]
                        update_entry(fields["kp"], val_tuple[0])
                        update_entry(fields["ki"], val_tuple[1])
                        update_entry(fields["kd"], val_tuple[2])
            
            # --- ATUALIZA OFFSET ÚNICO (CORRIGIDO) ---
            if tab_name == "current" and hasattr(tab, "offset_entries") and enc_offset is not None:
                # Agora trata enc_offset como um valor único, não uma lista/tupla
                update_entry(tab.offset_entries.get("offset"), enc_offset)
        
        self.log_to_terminal("Sincronização concluída.\n")

    # --- (RESTANTE DO CÓDIGO PERMANECE IDÊNTICO) ---
    def on_console_tab_change(self, tab_name):
        if tab_name == "Valores": self.start_monitoring()
        else: self.stop_monitoring()

    def start_monitoring(self):
        if not self.is_monitoring:
            self.is_monitoring = True
            threading.Thread(target=self.run_monitor_loop, daemon=True).start()
            self.log_to_terminal("Monitoramento iniciado.\n")

    def stop_monitoring(self): self.is_monitoring = False

    def run_monitor_loop(self):
        target_interval = 1.0 / 60
        last_console_update = 0
        console_update_interval = 0.2 
        
        while self.is_monitoring and self.driver_manager.is_connected and not self.stop_threads:
            start_time = time.time()
            try:
                val = None
                with self.serial_lock:
                    if self.current_tab_name == "position": 
                        val = self.driver_manager.driver.get_wrapped_angle()
                    elif self.current_tab_name == "velocity": 
                        val = self.driver_manager.driver.get_velocity()
                    elif self.current_tab_name == "current":
                        val = self.driver_manager.driver.get_dq_currents()
                
                if val is not None and self.scope_process and self.scope_process.is_alive():
                    self.scope_queue.put(val)

                current_time = time.time()
                if val is not None and (current_time - last_console_update > console_update_interval):
                    if self.current_tab_name == "current" and isinstance(val, (tuple, list)):
                        msg = f"Id: {val[0]:.2f}A | Iq: {val[1]:.2f}A\n"
                        self.after(0, lambda m=msg: self.console.log_value(m))
                    else:
                        label = "Ângulo" if self.current_tab_name == "position" else "Velocidade"
                        unit = "°" if self.current_tab_name == "position" else " RPM"
                        self.after(0, lambda v=val, l=label, u=unit: self.console.log_value(f"{l}: {v:.2f}{u}\n"))
                    last_console_update = current_time
            except: break
            
            elapsed = time.time() - start_time
            if target_interval > elapsed: time.sleep(target_interval - elapsed)

    def send_target_safe(self, val, mode):
        def task():
            with self.serial_lock:
                if self.active_mode_set != mode:
                    self.driver_manager.driver.control_mode(mode)
                    self.active_mode_set = mode
                    time.sleep(0.02)
                self.driver_manager.driver.target_value(float(val))
        threading.Thread(target=task, daemon=True).start()

    def set_pid(self, m, f):
        def task():
            try:
                p, i, d = float(f["kp"].get()), float(f["ki"].get()), float(f["kd"].get())
                with self.serial_lock: self.driver_manager.driver.set_pid_parameters(m, p, i, d)
                self.log_to_terminal(f"PID {m} atualizado.\n")
                self.manual_sync()
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def set_curr(self, v): threading.Thread(target=lambda: self._safe_set(self.driver_manager.driver.set_max_current, float(v)), daemon=True).start()
    def set_volt(self, v): threading.Thread(target=lambda: self._safe_set(self.driver_manager.driver.set_max_voltage, float(v)), daemon=True).start()
    def set_speed(self, v): threading.Thread(target=lambda: self._safe_set(self.driver_manager.driver.set_max_velocity, float(v)), daemon=True).start()
    def _safe_set(self, func, val):
        with self.serial_lock: func(val)
        self.manual_sync()

    def create_pid_group(self, parent, title, mode, col, registry):
        frame = ctk.CTkFrame(parent, border_width=1, border_color="#333333")
        frame.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 14, "bold"), text_color=COLOR_PRIMARY).pack(pady=10)
        fields = {}
        for label in ["kp", "ki", "kd"]:
            f = ctk.CTkFrame(frame, fg_color="transparent"); f.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(f, text=f"{label.capitalize()}:", width=40).pack(side="left")
            ent = ctk.CTkEntry(f); ent.insert(0, "---"); ent.pack(side="right", fill="x", expand=True)
            fields[label] = ent
        registry[mode] = fields
        ctk.CTkButton(frame, text="Atualizar", command=lambda: self.set_pid(mode, fields)).pack(pady=15, padx=20, fill="x")

    def create_action_row(self, parent, label_text, default_val, btn_text, command, key=None, registry=None, btn_color=None):
        row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text=label_text, width=140, anchor="w").pack(side="left")
        ent = ctk.CTkEntry(row, width=120); ent.insert(0, default_val); ent.pack(side="left", padx=(0, 5))
        if registry is not None and key: registry[key] = ent
        btn = ctk.CTkButton(row, text=btn_text, width=100, command=lambda: command(ent.get()))
        if btn_color: btn.configure(fg_color=btn_color)
        btn.pack(side="left"); return ent

    def log_to_terminal(self, msg): self.after(0, lambda: self.console.log_message(msg))
    
    def toggle_oscilloscope(self):
        if self.scope_process and self.scope_process.is_alive(): return
        self.scope_process = multiprocessing.Process(target=run_dpg_process, args=(self.scope_queue,))
        self.scope_process.daemon = True
        self.scope_process.start()

    def toggle_motor_power(self):
        if not self.driver_manager.is_connected: return
        def action():
            if self.motor_enabled:
                if self.driver_manager.driver.disable_motor()[0] == 0x03: self.motor_enabled = False
            else:
                if self.driver_manager.driver.enable_motor()[0] == 0x02: self.motor_enabled = True
            self.after(0, self.update_power_btn_ui)
        threading.Thread(target=action, daemon=True).start()

    def update_power_btn_ui(self):
        color = COLOR_DANGER if self.motor_enabled else COLOR_SUCCESS
        text = "Desligar Motor" if self.motor_enabled else "Ligar Motor"
        self.sidebar.btn_power.configure(text=text, fg_color=color)

    def show_loading_mask(self):
        self.loading_overlay.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.loading_overlay.lift()
        
    def remove_loading_mask(self):
        self.loading_overlay.grid_forget()
        self.resize_timer = None

    def on_resize(self, event):
        if event.widget == self:
            if event.width == self.last_width and event.height == self.last_height: return
            self.last_width = event.width
            self.last_height = event.height
            self.show_loading_mask()
            if self.resize_timer: self.after_cancel(self.resize_timer)
            self.resize_timer = self.after(300, self.remove_loading_mask)

    def select_tab(self, name):
        if self.current_tab_name == name: return
        self.show_loading_mask()
        self.update_idletasks()
        self.current_tab_name = name
        for t in self.tabs.values(): t.grid_forget()
        self.tabs[name].grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        if self.resize_timer: self.after_cancel(self.resize_timer)
        self.resize_timer = self.after(150, self.remove_loading_mask)

    def on_closing(self):
        self.stop_threads = True
        self.is_monitoring = False
        if self.scope_process and self.scope_process.is_alive(): self.scope_process.terminate()
        self.driver_manager.close()
        self.destroy()