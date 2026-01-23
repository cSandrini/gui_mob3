import customtkinter as ctk
from utils.constants import COLOR_NEUTRAL, COLOR_WARNING, COLOR_CONNECTED, COLOR_DISCONNECTED, COLOR_PRIMARY

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, callbacks):
        super().__init__(master, width=200, corner_radius=0)
        self.callbacks = callbacks
        self.setup_ui()

    def setup_ui(self):
        # Título
        ctk.CTkLabel(self, text="MOB3 Control", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, padx=20, pady=20)

        # --- BOTÕES DE NAVEGAÇÃO (ABAS) ---
        # 1. Posição
        self.btn_pos = self.create_btn("Controle de Posição", 
            lambda: (self.callbacks["show_pos"](), self.set_active_button(self.btn_pos)), 1)
        
        # 2. Velocidade
        self.btn_vel = self.create_btn("Controle de Velocidade", 
            lambda: (self.callbacks["show_vel"](), self.set_active_button(self.btn_vel)), 2)
        
        # 3. Corrente (NOVO)
        self.btn_curr = self.create_btn("Controle de Corrente", 
            lambda: (self.callbacks["show_curr"](), self.set_active_button(self.btn_curr)), 3)
            
        # 4. Dados
        self.btn_data = self.create_btn("Adquirir Dados", 
            lambda: (self.callbacks["show_data"](), self.set_active_button(self.btn_data)), 4)
        
        # Define Posição como ativo inicial
        self.set_active_button(self.btn_pos)

        # --- AÇÕES GERAIS ---
        # 5. Osciloscópio
        self.btn_scope = self.create_btn("Abrir Osciloscópio", self.callbacks["open_scope"], 5)
        self.btn_scope.configure(fg_color="#7B1FA2", hover_color="#4A148C")

        # 6. Power
        self.btn_power = self.create_btn("Ligar Motor", self.callbacks["toggle_power"], 6)
        self.btn_power.configure(fg_color=COLOR_NEUTRAL)
        
        # 7. Sync
        self.btn_sync = self.create_btn("Sincronizar Valores", self.callbacks["sync"], 7)
        self.btn_sync.configure(fg_color=COLOR_NEUTRAL)

        # --- STATUS ---
        self.grid_rowconfigure(8, weight=1) # Empurra o status para o fundo
        
        self.status_label = ctk.CTkLabel(self, text="Buscando USB...", text_color=COLOR_WARNING)
        self.status_label.grid(row=9, column=0, padx=20, pady=(20, 5))
        
        self.version_label = ctk.CTkLabel(self, text="Firmware: ---", font=("Segoe UI", 11))
        self.version_label.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="sw")

    def create_btn(self, text, command, row):
        """Helper para criar botões padronizados na grid"""
        btn = ctk.CTkButton(self, text=text, command=command, fg_color="transparent", anchor="w")
        btn.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        return btn

    def set_active_button(self, active_btn):
        """Define a cor do botão ativo e reseta os outros"""
        # Adicionei self.btn_curr na lista de navegação
        nav_buttons = [self.btn_pos, self.btn_vel, self.btn_curr, self.btn_data]
        
        for btn in nav_buttons:
            if btn == active_btn:
                # ATIVO
                btn.configure(fg_color=COLOR_PRIMARY)
                btn.configure(state="disabled")
                btn.configure(text_color_disabled="#FFFFFF") 
            else:
                # INATIVO
                btn.configure(fg_color="transparent")
                btn.configure(state="normal")
                btn.configure(text_color="#DCE4EE")

    def update_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)

    def update_version(self, version):
        self.version_label.configure(text=f"Firmware: {version}")