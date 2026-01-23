import customtkinter as ctk
import math
import threading

class CurrentTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pid_entries = {}
        self.limit_entries = {}
        self.offset_entries = {} 
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Controle de Corrente (Torque)", font=("Segoe UI", 22, "bold")).pack(pady=10, padx=20, anchor="w")
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # --- 1. PIDs (ID e IQ) ---
        pid_row = ctk.CTkFrame(scroll, fg_color="transparent")
        pid_row.pack(fill="x", padx=10, pady=10)
        pid_row.grid_columnconfigure((0, 1), weight=1)
        
        self.app.create_pid_group(pid_row, "PID Corrente Direta (Id)", 0, 0, self.pid_entries)
        self.app.create_pid_group(pid_row, "PID Corrente Quadratura (Iq)", 1, 1, self.pid_entries)
        
        # --- 2. LIMITES ---
        f_sec = ctk.CTkFrame(scroll)
        f_sec.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f_sec, text="Limites de Segurança", font=("Segoe UI", 14, "bold")).pack(pady=(10,5))
        
        self.app.create_action_row(f_sec, "Tensão Máx (V):", "---", "Definir", self.app.set_volt, "voltage", self.limit_entries)
        
        # --- 3. ENCODER OFFSET (CORRIGIDO: VALOR ÚNICO) ---
        f_off = ctk.CTkFrame(scroll)
        f_off.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f_off, text="Encoder Offset Calibrado", font=("Segoe UI", 14, "bold")).pack(pady=(10,5))
        
        row_off = ctk.CTkFrame(f_off, fg_color="transparent")
        row_off.pack(fill="x", padx=10)
        
        ctk.CTkLabel(row_off, text="Offset (° ou rad):", width=100, anchor="w").pack(side="left")
        self.ent_offset = ctk.CTkEntry(row_off, placeholder_text="0.0")
        self.ent_offset.pack(side="left", fill="x", expand=True, padx=10)
        
        # Guardamos referência no dicionário para o sync encontrar
        self.offset_entries["offset"] = self.ent_offset
        
        ctk.CTkButton(f_off, text="Definir Offset", fg_color="#555555", 
                      command=self.set_offset_action).pack(pady=10, padx=20, fill="x")

        # --- 4. CONTROLE ALVO ---
        f_ctrl = ctk.CTkFrame(scroll)
        f_ctrl.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f_ctrl, text="Setar Corrente Alvo (Iq)", font=("Segoe UI", 14, "bold")).pack(pady=(10,5))
        
        self.app.create_action_row(f_ctrl, "Corrente Iq (A):", "0.0", "Enviar Torque", self.send_current_target, btn_color="#E04F5F")
        
    def send_current_target(self, val):
        if not self.app.driver_manager.is_connected: return
        try:
            self.app.send_target_safe(float(val), 0) 
        except: pass

    def set_offset_action(self):
        """Lê o campo único e envia o comando set_encoder_offset"""
        if not self.app.driver_manager.is_connected: return
        try:
            val = float(self.offset_entries["offset"].get())
            
            def task():
                with self.app.serial_lock:
                    if hasattr(self.app.driver_manager.driver, "set_encoder_offset"):
                        # Envia valor único (float)
                        self.app.driver_manager.driver.set_encoder_offset(val)
                
                self.app.log_to_terminal(f"Offset definido: {val:.4f}\n")
                self.app.manual_sync() 
                
            threading.Thread(target=task, daemon=True).start()
        except ValueError:
            self.app.log_to_terminal("Erro: Valor de offset inválido.\n")