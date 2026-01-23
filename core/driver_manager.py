import serial
import serial.tools.list_ports
import time
from sdk.mob3_sdk import MOB3Driver

# Constantes de Conexão
CMD_HANDSHAKE = bytes.fromhex("AE13070000E027") 
EXPECTED_HEX = "be13070000e47d"

class DriverManager:
    def __init__(self, log_callback):
        self.driver = None
        self.is_connected = False
        self.log_callback = log_callback

    def auto_connect(self):
        """
        Executa uma verificação de conexão (Lógica Simples/Clássica).
        Retorna: (status_string, port_name, firmware_version)
        """
        # 1. Obtém lista atual de portas COM
        try:
            current_ports = [p.device for p in serial.tools.list_ports.comports()]
        except:
            current_ports = []

        # --- CASO JÁ ESTEJA CONECTADO ---
        if self.is_connected and self.driver:
            # Verifica se o cabo foi desconectado (porta sumiu da lista)
            if self.driver.serial_port.port not in current_ports:
                self.close()
                return "lost", None, None
            
            # (Opcional) Verifica se a porta está respondendo
            try:
                # Apenas checa se o objeto serial ainda acha que está aberto
                if not self.driver.serial_port.is_open:
                    self.close()
                    return "lost", None, None
            except:
                self.close()
                return "lost", None, None

            return "maintained", None, None

        # --- CASO ESTEJA DESCONECTADO (Varredura) ---
        for port in current_ports:
            try:
                # Tenta abrir porta para teste rápido
                # Timeout curto para não travar se não for o motor
                temp_ser = serial.Serial(port, baudrate=115200, timeout=0.2, write_timeout=0.2)
                
                # Limpa buffers para evitar leitura de lixo antigo
                temp_ser.reset_input_buffer()
                temp_ser.reset_output_buffer()

                # Handshake
                temp_ser.write(CMD_HANDSHAKE)
                response = temp_ser.read(15).hex().lower()
                temp_ser.close()

                # Verifica assinatura
                if EXPECTED_HEX in response:
                    # Pausa para o Windows liberar a porta após o close()
                    time.sleep(0.1)
                    
                    # Conecta o driver oficial
                    self.driver = MOB3Driver(port, logger_func=self.log_callback)
                    self.is_connected = True
                    
                    # Tenta pegar versão
                    try: 
                        version = self.driver.get_version()
                    except: 
                        version = "Unknown"
                        
                    return "connected", port, version
            except:
                # Se der erro (porta em uso, acesso negado, não é o motor), ignora
                pass
        
        return "searching", None, None

    def close(self):
        if self.driver:
            try: self.driver.close()
            except: pass
        self.driver = None
        self.is_connected = False