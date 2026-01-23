import customtkinter as ctk
import time

class Console(ctk.CTkFrame):
    def __init__(self, master, tab_callback=None):
        super().__init__(master, height=250, corner_radius=5)
        self.tab_callback = tab_callback # Função para chamar quando trocar a aba
        self.setup_ui()

    def setup_ui(self):
        # Adicionei o comando=self.on_tab_change
        self.tabs = ctk.CTkTabview(self, command=self.on_tab_change)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_logs = self.tabs.add("Logs")
        self.tab_values = self.tabs.add("Valores")

        self.terminal_box = ctk.CTkTextbox(self.tab_logs, font=("Consolas", 12), text_color="#00FF41", fg_color="#000000")
        self.terminal_box.pack(fill="both", expand=True)
        self.terminal_box.configure(state="disabled")

        self.values_box = ctk.CTkTextbox(self.tab_values, font=("Consolas", 14), text_color="#00BFFF", fg_color="#000000")
        self.values_box.pack(fill="both", expand=True)
        self.values_box.configure(state="disabled")

    def on_tab_change(self):
        # Pega o nome da aba atual ("Logs" ou "Valores") e avisa a Main Window
        if self.tab_callback:
            self.tab_callback(self.tabs.get())

    def log_message(self, msg):
        self.terminal_box.configure(state="normal")
        self.terminal_box.insert("end", msg)
        self.terminal_box.see("end")
        self.terminal_box.configure(state="disabled")

    def log_value(self, msg):
        self.values_box.configure(state="normal")
        self.values_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.values_box.see("end")
        self.values_box.configure(state="disabled")

    def set_active_tab(self, name):
        self.tabs.set(name)