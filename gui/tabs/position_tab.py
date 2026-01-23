import customtkinter as ctk
import math
import threading
import time
import utils.constants as constants
from utils.constants import COLOR_PRIMARY   

class PositionTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pid_entries = {}
        self.limit_entries = {}
        self.routine_entries = [] 
        self.is_running_routine = False
        self.setup_ui()

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # --- 1. LINHA DOS PIDS ---
        pid_row = ctk.CTkFrame(scroll, fg_color="transparent")
        pid_row.pack(fill="x", padx=10)
        pid_row.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        self.app.create_pid_group(pid_row, "PID Corrente ID", 0, 0, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Corrente IQ", 1, 1, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Velocidade", 2, 2, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Posição", 3, 3, self.pid_entries)
        
        # --- 2. LINHA PRINCIPAL (3 COLUNAS) ---
        main_row = ctk.CTkFrame(scroll, fg_color="transparent")
        main_row.pack(fill="x", padx=10, pady=10)
        main_row.grid_columnconfigure((0, 1, 2), weight=1)

        # === COLUNA 1: LIMITES ===
        col_limits = ctk.CTkFrame(main_row)
        col_limits.grid(row=0, column=0, sticky="nsew", padx=5)
        ctk.CTkLabel(col_limits, text="Limites de Segurança", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        # Usando pady pequeno para compactar
        self.app.create_action_row(col_limits, "Corrente Máx (A):", "---", "Definir", self.app.set_curr, "current", self.limit_entries)
        self.app.create_action_row(col_limits, "Tensão Máx (V):", "---", "Definir", self.app.set_volt, "voltage", self.limit_entries)
        self.app.create_action_row(col_limits, "Velocidade Máx:", "---", "Definir", self.app.set_speed, "velocity", self.limit_entries)

        # === COLUNA 2: CONTROLE ÚNICO (Corrigido) ===
        col_single = ctk.CTkFrame(main_row)
        col_single.grid(row=0, column=1, sticky="nsew", padx=5)
        ctk.CTkLabel(col_single, text="Movimento Único", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        # Container interno para alinhar ao topo (sem expand=True vertical)
        f_content = ctk.CTkFrame(col_single, fg_color="transparent")
        f_content.pack(fill="x", padx=10, pady=0) # Padding 0 no topo para alinhar com os inputs da esquerda
        
        ctk.CTkLabel(f_content, text="Setpoint (°):", anchor="w").pack(fill="x", pady=(0, 5))
        
        self.ent_target = ctk.CTkEntry(f_content, placeholder_text="0.0")
        self.ent_target.pack(fill="x", pady=(0, 10))
        
        btn_move = ctk.CTkButton(f_content, text="Mover", fg_color=COLOR_PRIMARY, 
                                 command=lambda: self.send_target(self.ent_target.get()))
        btn_move.pack(fill="x")

        # === COLUNA 3: ROTINA (Corrigido) ===
        col_routine = ctk.CTkFrame(main_row)
        col_routine.grid(row=0, column=2, sticky="nsew", padx=5)
        ctk.CTkLabel(col_routine, text="Rotina Sequencial", font=("Segoe UI", 14, "bold")).pack(pady=10)

        self.routine_scroll = ctk.CTkScrollableFrame(col_routine, height=150, fg_color="#2b2b2b")
        self.routine_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Botões de Controle
        btn_box = ctk.CTkFrame(col_routine, fg_color="transparent")
        btn_box.pack(fill="x", padx=5, pady=5)
        
        # Botões + e -
        ctk.CTkButton(btn_box, text="+", width=30, command=self.add_routine_step).pack(side="left", padx=2)
        ctk.CTkButton(btn_box, text="-", width=30, fg_color=COLOR_PRIMARY, command=self.rem_routine_step).pack(side="left", padx=2)
        
        # Botão Executar Menor e Alinhado à Direita
        self.btn_run_routine = ctk.CTkButton(btn_box, text="Executar", width=80, fg_color=COLOR_PRIMARY, command=self.start_routine_thread)
        self.btn_run_routine.pack(side="right", padx=2) 
        
        self.lbl_routine_status = ctk.CTkLabel(col_routine, text="Status: Aguardando", font=("Segoe UI", 11))
        self.lbl_routine_status.pack(pady=(0, 5))

        # Inputs Iniciais
        self.add_routine_step()
        self.add_routine_step()

    # --- LÓGICA DA UI DA ROTINA ---
    def add_routine_step(self):
        row_frame = ctk.CTkFrame(self.routine_scroll, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        
        idx = len(self.routine_entries) + 1
        ctk.CTkLabel(row_frame, text=f"{idx}º:", width=25).pack(side="left")
        
        ent = ctk.CTkEntry(row_frame, placeholder_text="0.0", height=28)
        ent.pack(side="right", fill="x", expand=True)
        
        self.routine_entries.append((row_frame, ent))

    def rem_routine_step(self):
        if len(self.routine_entries) > 2:
            frame, ent = self.routine_entries.pop()
            frame.destroy()

    # --- LÓGICA DE EXECUÇÃO ---
    def start_routine_thread(self):
        if self.is_running_routine: return
        try:
            targets = []
            for _, ent in self.routine_entries:
                val = ent.get()
                if not val: raise ValueError
                targets.append(float(val))
        except:
            self.lbl_routine_status.configure(text="Valores inválidos!", text_color="#FF3B30")
            return

        self.is_running_routine = True
        self.btn_run_routine.configure(state="disabled", text="...")
        self.lbl_routine_status.configure(text="Iniciando...", text_color="#FFFFFF")
        threading.Thread(target=self.routine_task, args=(targets,), daemon=True).start()

    def routine_task(self, targets):
        tolerance = 0.05
        for i, target_deg in enumerate(targets):
            self.update_status_safe(f"Indo para {target_deg}° ({i+1}/{len(targets)})")
            self.send_target(target_deg)
            
            start_wait = time.time()
            arrived = False
            while time.time() - start_wait < 10.0:
                if not self.app.driver_manager.is_connected: break
                current_angle = self.get_safe_angle()
                if current_angle is not None:
                    if abs(current_angle - target_deg) <= tolerance:
                        arrived = True
                        break
                time.sleep(0.1)
            
            if not arrived:
                self.update_status_safe(f"Erro no passo {i+1}", "#FF3B30")
                self.reset_routine_ui()
                return
            time.sleep(0.5)

        self.update_status_safe("Concluído!", "#4CD964")
        self.reset_routine_ui()

    def get_safe_angle(self):
        val = None
        try:
            with self.app.serial_lock:
                val = self.app.driver_manager.driver.get_wrapped_angle()
        except: pass
        return val

    def update_status_safe(self, text, color="#FFFFFF"):
        self.after(0, lambda: self.lbl_routine_status.configure(text=text, text_color=color))

    def reset_routine_ui(self):
        self.is_running_routine = False
        self.after(0, lambda: self.btn_run_routine.configure(state="normal", text="Executar"))

    def send_target(self, val):
        if not self.app.driver_manager.is_connected: return
        import math
        try:
            rads = math.radians(float(val))
            self.app.send_target_safe(rads, 3)
        except: pass