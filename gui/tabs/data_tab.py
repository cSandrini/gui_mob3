import customtkinter as ctk
import threading
import time
import datetime
import os
import csv
import matplotlib.pyplot as plt
import math

class DataTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Variáveis da Resposta ao Degrau
        self.step_entries = []
        self.is_acquiring = False
        
        # Variáveis da Caracterização
        self.char_entries = {} 
        self.is_characterizing = False

        self.setup_ui()

    def setup_ui(self):
        # Título Geral
        ctk.CTkLabel(self, text="Aquisição e Análise de Dados", font=("Segoe UI", 22, "bold")).pack(pady=10, padx=20, anchor="w")
        
        # Criação das Abas Internas para separar os Modos
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_step = self.tab_view.add("Resposta ao Degrau")
        self.tab_char = self.tab_view.add("Caracterização (Torque x Corrente)")
        
        # Monta as interfaces em cada aba
        self.setup_step_response_ui(self.tab_step)
        self.setup_characterization_ui(self.tab_char)

    # =========================================================================
    # --- GUI: RESPOSTA AO DEGRAU (Código Original Refatorado) ---
    # =========================================================================
    def setup_step_response_ui(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Configurações
        config_frame = ctk.CTkFrame(scroll)
        config_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(config_frame, text="Configurações Temporais", font=("Segoe UI", 14, "bold")).pack(pady=5)
        
        grid_cfg = ctk.CTkFrame(config_frame, fg_color="transparent")
        grid_cfg.pack(pady=5)
        
        ctk.CTkLabel(grid_cfg, text="Estabilização (s):").grid(row=0, column=0, padx=5)
        self.ent_duration = ctk.CTkEntry(grid_cfg, width=80)
        self.ent_duration.insert(0, "2.0") 
        self.ent_duration.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(grid_cfg, text="Amostragem (ms):").grid(row=0, column=2, padx=5)
        self.ent_sample_rate = ctk.CTkEntry(grid_cfg, width=80)
        self.ent_sample_rate.insert(0, "20") 
        self.ent_sample_rate.grid(row=0, column=3, padx=5)

        # Inputs dos Degraus
        steps_frame = ctk.CTkFrame(scroll)
        steps_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        header = ctk.CTkFrame(steps_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Sequência de Posições (Graus)", font=("Segoe UI", 14, "bold")).pack(side="left")
        
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")
        ctk.CTkButton(btn_box, text="+", width=40, command=self.add_step).pack(side="left", padx=2)
        ctk.CTkButton(btn_box, text="-", width=40, fg_color="#dc3545", command=self.rem_step).pack(side="left", padx=2)

        self.steps_container = ctk.CTkScrollableFrame(steps_frame, height=200, fg_color="#2b2b2b")
        self.steps_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Botão Ação
        self.btn_start = ctk.CTkButton(scroll, text="INICIAR RESPOSTA AO DEGRAU", height=50, fg_color="#28a745", font=("Segoe UI", 16, "bold"), command=self.start_acquisition_thread)
        self.btn_start.pack(fill="x", padx=20, pady=20)

        self.lbl_status = ctk.CTkLabel(scroll, text="Status: Pronto", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 20))

        # Inicia com 3 passos
        self.add_step(0.0)
        self.add_step(30.0)
        self.add_step(60.0)

    # =========================================================================
    # --- GUI: CARACTERIZAÇÃO TORQUE X CORRENTE (NOVO) ---
    # =========================================================================
    def setup_characterization_ui(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="Teste de Rampa de Corrente", font=("Segoe UI", 18, "bold")).pack(pady=10)
        ctk.CTkLabel(scroll, text="O motor será travado em uma posição e a corrente IQ será incrementada.", font=("Segoe UI", 12)).pack(pady=(0, 10))

        # Frame de Parâmetros
        params_frame = ctk.CTkFrame(scroll)
        params_frame.pack(fill="x", padx=10, pady=10)
        
        # Grid layout para os parâmetros
        params_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Helper para criar inputs
        def create_param(row, col, label, default):
            f = ctk.CTkFrame(params_frame, fg_color="transparent")
            f.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            ctk.CTkLabel(f, text=label, anchor="w").pack(fill="x")
            e = ctk.CTkEntry(f)
            e.insert(0, default)
            e.pack(fill="x")
            return e

        self.char_entries['start_current'] = create_param(0, 0, "Corrente Inicial (A):", "0.0")
        self.char_entries['end_current']   = create_param(0, 1, "Corrente Final (A):", "5.0")
        self.char_entries['step_current']  = create_param(1, 0, "Passo de Corrente (A):", "0.5")
        self.char_entries['step_duration'] = create_param(1, 1, "Duração por Passo (s):", "1.0")
        self.char_entries['lock_pos']      = create_param(2, 0, "Posição de Travamento (°):", "0.0")
        self.char_entries['sample_rate']   = create_param(2, 1, "Amostragem (ms):", "20")

        # Botão de Ação
        self.btn_char_start = ctk.CTkButton(scroll, text="INICIAR CARACTERIZAÇÃO", height=50, fg_color="#7B1FA2", font=("Segoe UI", 16, "bold"), command=self.start_characterization_thread)
        self.btn_char_start.pack(fill="x", padx=20, pady=30)

        self.lbl_char_status = ctk.CTkLabel(scroll, text="Status: Aguardando configuração", font=("Segoe UI", 12))
        self.lbl_char_status.pack(pady=(0, 20))

    # =========================================================================
    # --- LOGICA: RESPOSTA AO DEGRAU (Mantida Original) ---
    # =========================================================================
    def add_step(self, val=None):
        row_frame = ctk.CTkFrame(self.steps_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        idx = len(self.step_entries) + 1
        ctk.CTkLabel(row_frame, text=f"Passo {idx}:", width=60).pack(side="left")
        ent = ctk.CTkEntry(row_frame, placeholder_text="Ângulo (°)")
        if val is not None: ent.insert(0, str(val))
        ent.pack(side="right", fill="x", expand=True)
        self.step_entries.append((row_frame, ent))

    def rem_step(self):
        if len(self.step_entries) > 1:
            frame, ent = self.step_entries.pop()
            frame.destroy()

    def collect_gui_metadata(self):
        fw_version = "Unknown"
        try:
            full_text = self.app.sidebar.version_label.cget("text")
            fw_version = full_text.replace("Firmware: ", "")
        except: pass

        pid_strings = []
        pos_tab = self.app.tabs.get("position")
        if pos_tab:
            labels = {0: "Id", 1: "Iq", 2: "Vel", 3: "Pos"}
            for mode_idx in range(4):
                if mode_idx in pos_tab.pid_entries:
                    try:
                        fields = pos_tab.pid_entries[mode_idx]
                        pid_strings.append(f"{labels[mode_idx]}:({fields['kp'].get()},{fields['ki'].get()},{fields['kd'].get()})")
                    except: pass
        full_pid_str = " | ".join(pid_strings) if pid_strings else "PIDs not loaded"
        return fw_version, full_pid_str

    def start_acquisition_thread(self):
        if self.is_acquiring: return
        if not self.app.driver_manager.is_connected:
            self.lbl_status.configure(text="Erro: Motor desconectado!", text_color="#FF3B30")
            return

        try:
            targets = []
            for _, ent in self.step_entries:
                if not ent.get(): raise ValueError
                targets.append(float(ent.get()))
            duration = float(self.ent_duration.get())
            sample_period = float(self.ent_sample_rate.get()) / 1000.0
        except ValueError:
            self.lbl_status.configure(text="Erro: Valores inválidos!", text_color="#FF3B30")
            return

        fw_ver, pid_str = self.collect_gui_metadata()
        self.is_acquiring = True
        self.btn_start.configure(state="disabled", text="ADQUIRINDO DADOS...", fg_color="#FFA500")
        
        threading.Thread(target=self.acquisition_task, args=(targets, duration, sample_period, fw_ver, pid_str), daemon=True).start()

    def acquisition_task(self, targets, step_duration, sample_period, fw_ver, pid_str):
        data_log = {"time": [], "setpoint": [], "position": [], "velocity": [], "current_q": []}
        start_time = time.time()
        
        with self.app.serial_lock:
            try: self.app.driver_manager.driver.control_mode(3)
            except: pass
            time.sleep(0.1)

        try:
            for i, target_deg in enumerate(targets):
                self.update_status_safe(f"Executando degrau {i+1}/{len(targets)}: {target_deg}°")
                target_rad = math.radians(target_deg)

                with self.app.serial_lock:
                    self.app.driver_manager.driver.target_value(target_rad)

                step_start = time.time()
                while (time.time() - step_start) < step_duration:
                    loop_start = time.time()
                    pos_rad = 0.0; vel_rpm = 0.0; iq = 0.0
                    
                    with self.app.serial_lock:
                        try:
                            p = self.app.driver_manager.driver.get_wrapped_angle()
                            if p is not None: pos_rad = math.radians(p)
                            v = self.app.driver_manager.driver.get_velocity()
                            if v is not None: vel_rpm = v
                            dq = self.app.driver_manager.driver.get_dq_currents()
                            if dq and len(dq) >= 2: _, iq = dq
                        except: pass

                    data_log["time"].append(time.time() - start_time)
                    data_log["setpoint"].append(target_rad)
                    data_log["position"].append(pos_rad)
                    data_log["velocity"].append(vel_rpm)
                    data_log["current_q"].append(iq)

                    elapsed = time.time() - loop_start
                    if sample_period > elapsed: time.sleep(sample_period - elapsed)
            
            self.update_status_safe("Gerando gráficos...", "#3b8ed0")
            self.save_and_plot(data_log, fw_ver, pid_str)
            self.update_status_safe("Concluído! Pasta criada.", "#4CD964")

        except Exception as e:
            self.update_status_safe(f"Erro: {str(e)}", "#FF3B30")
        finally:
            self.is_acquiring = False
            self.after(0, lambda: self.btn_start.configure(state="normal", text="INICIAR RESPOSTA AO DEGRAU", fg_color="#28a745"))

    def save_and_plot(self, data, version, pid_string):
        date_str = datetime.datetime.now().strftime("%d-%m-%Y")
        i = 1
        while True:
            folder_name = f"dados{i}-{date_str}"
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
                break
            i += 1
        
        filepath_csv = os.path.join(folder_name, "dados.csv")
        filepath_img = os.path.join(folder_name, "grafico.png")

        try:
            with open(filepath_csv, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Tempo (s)", "Setpoint (rad)", "Posicao (rad)", "Velocidade (RPM)", "Corrente Q (A)"])
                for k in range(len(data["time"])):
                    writer.writerow([f"{data['time'][k]:.4f}", f"{data['setpoint'][k]:.4f}", f"{data['position'][k]:.4f}", f"{data['velocity'][k]:.2f}", f"{data['current_q'][k]:.4f}"])
        except: pass

        try:
            plt.style.use('default') 
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
            
            ax1.plot(data["time"], data["setpoint"], 'r--', label='Setpoint')
            ax1.plot(data["time"], data["position"], 'b-', label='Posicao (rad)')
            ax1.set_ylabel('Posicao (rad)'); ax1.grid(True); ax1.legend(loc='upper right')
            
            ax2.plot(data["time"], data["velocity"], 'g-', label='Velocidade (RPM)')
            ax2.set_ylabel('Velocidade (RPM)'); ax2.grid(True); ax2.legend(loc='upper left')

            ax3.plot(data["time"], data["current_q"], 'm-', label='Corrente Q (A)')
            ax3.set_ylabel('Corrente (A)'); ax3.set_xlabel('Tempo (s)'); ax3.grid(True); ax3.legend(loc='upper right')

            info_text = f"MOB3 Driver | FW: {version}\nParams: {pid_string}"
            fig.text(0.02, 0.01, info_text, fontsize=7, color='gray', ha='left')

            plt.tight_layout(rect=[0, 0.04, 1, 1])
            plt.savefig(filepath_img, dpi=100)
            plt.close(fig)
            os.startfile(filepath_img)
        except: pass

    # =========================================================================
    # --- LOGICA: CARACTERIZAÇÃO (Placeholder) ---
    # =========================================================================
    def start_characterization_thread(self):
        # Aqui você implementará a lógica no futuro
        self.lbl_char_status.configure(text="Iniciado! (Lógica ainda não implementada)", text_color="#FFCC00")
        print("Parametros capturados:")
        for k, v in self.char_entries.items():
            print(f"{k}: {v.get()}")

    def update_status_safe(self, text, color="#FFFFFF"):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))