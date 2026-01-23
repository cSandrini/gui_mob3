import serial
import struct
import time

empty_payload = b'\x00' 

class MOB3Driver:
    # PROTOCOL CONSTANTS
    HEADER_SEND = 0xAE13
    HEADER_RECV = 0xBE13
    
    CMD_CONNECTION_CHECK = 0x00
    CMD_GET_VERSION = 0x01
    CMD_GET_STATUS = 0x0E
    CMD_ENABLE_MOTOR = 0x02
    CMD_DISABLE_MOTOR = 0x03
    CMD_ENCODER_CALIBRATION = 0x04
    CMD_SET_ZERO_POSITION = 0x05
    CMD_CONTROL_MODE = 0x06
    CMD_SET_PID_PARAMTERS = 0x07
    CMD_GET_PID_PARAMETERS = 0x08
    CMD_TARGET_VALUE = 0x09
    CMD_GET_ROTOR_POSITION = 0x0A
    CMD_GET_RAW_ANGLE = 0x11
    CMD_GET_WRAPPED_ANGLE = 0x12
    CMD_GET_PHASE_CURRENTS = 0x13
    CMD_GET_DQ_CURRENTS = 0x14
    CMD_GET_VELOCITY = 0x15
    CMD_SET_MAX_CURRENT = 0x0D
    CMD_SET_MAX_VOLTAGE = 0x0F
    CMD_SET_MAX_VELOCITY = 0x10
    CMD_GET_MAX_CURRENT = 0x16
    CMD_GET_MAX_VOLTAGE = 0x17
    CMD_GET_MAX_VELOCITY = 0x18

    CMD_SET_ENCODER_OFFSET = 0x19
    CMD_GET_ENCODER_OFFSET = 0x1A
 

    CMD_ERROR = 0xFF
    ERROR_INVALID_COMMAND = 0x01
    ERROR_INVALID_PAYLOAD_SIZE = 0x02
    ERROR_MOTOR_DISABLED = 0x03
    ERROR_VALUE_OUT_OF_RANGE = 0x04

    def __init__(self, port, baudrate=115200, logger_func=None):
        self.serial_port = serial.Serial(port, baudrate, timeout=0.2)
        self.connected = self.serial_port.is_open
        self.logger = logger_func 
        
        if self.connected:
            self.serial_port.reset_input_buffer()

    def _log(self, message):
        """Envia mensagens exclusivamente para a interface."""
        if self.logger:
            self.logger(message)

    def calculate_crc(self, data: bytes) -> int:
        crc = 0
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
                crc &= 0xFFFF
        return crc

    def _send_packet(self, opcode, payload=b'', description=""):
        if payload is None: payload = b''
        msg_size = 6 + len(payload)
        frame_header = struct.pack('>HBB', self.HEADER_SEND, msg_size, opcode)
        packet_for_crc = frame_header + payload
        crc_val = self.calculate_crc(packet_for_crc)
        final_packet = frame_header + payload + struct.pack('>H', crc_val)
        
        # LOG DA DESCRIÇÃO E PACOTE
        if description:
            self._log(f"{description}\n")
        self._log(f"TX: {final_packet.hex(' ').upper()}\n")
        
        self.serial_port.write(final_packet)
        self.serial_port.flush()

    def _read_packet(self):
        try:
            start_time = time.time()
            while (time.time() - start_time) < 0.5:
                header = self.serial_port.read(1)
                if not header: continue
                if header == b'\xBE':
                    next_b = self.serial_port.read(1)
                    if next_b == b'\x13': break
            else:
                return None, None

            size_byte = self.serial_port.read(1)
            if not size_byte: return None, None
            packet_size = size_byte[0]

            data = self.serial_port.read(packet_size - 3)
            full_packet = b'\xBE\x13' + size_byte + data
            
            self._log(f"RX: {full_packet.hex(' ').upper()}\n")

            opcode = data[0]
            payload = data[1:-2]
            return opcode, payload
        except Exception as e:
            self._log(f"ERRO RX: {e}\n")
            return None, None

    def close(self):
        if self.serial_port.is_open:
            self.serial_port.close()

    # --- COMANDOS ATUALIZADOS COM DESCRIPTIONS ---

    def connection_check(self, description="(Verificar Conexão)"):
        self._send_packet(self.CMD_CONNECTION_CHECK, b'\x00', description)
        return self._read_packet()

    def get_version(self, description="(Lendo Versão do Firmware)"):
        self._send_packet(self.CMD_GET_VERSION, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_VERSION and payload and len(payload) >= 2:
            return f"v{payload[0]}.{payload[1]}"
        return "v?.?"
    
    def get_status(self, description=""): # Status geralmente roda em loop, descrição opcional
        self._send_packet(self.CMD_GET_STATUS, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_STATUS and payload:
            return payload[0]
        return "Unknown"

    def enable_motor(self, description="(Habilitar Motor)"):
        self._send_packet(self.CMD_ENABLE_MOTOR, empty_payload, description)
        return self._read_packet()

    def disable_motor(self, description="(Desabilitar Motor)"):
        self._send_packet(self.CMD_DISABLE_MOTOR, empty_payload, description)
        return self._read_packet()

    def set_max_current(self, current: float, description=None):
        if not description: description = f"(Definir Corrente Máxima - {current}A)"
        payload = struct.pack('<f', current)
        self._send_packet(self.CMD_SET_MAX_CURRENT, payload, description)
        return self._read_packet()

    def set_max_voltage(self, voltage: float, description=None):
        if not description: description = f"(Definir Tensão Máxima - {voltage}V)"
        payload = struct.pack('<f', voltage)
        self._send_packet(self.CMD_SET_MAX_VOLTAGE, payload, description)
        return self._read_packet()

    def set_max_velocity(self, speed_in_rpm: float, description=None):
        if not description: description = f"(Definir Velocidade Máxima - {speed_in_rpm} RPM)"
        payload = struct.pack('<f', speed_in_rpm)
        self._send_packet(self.CMD_SET_MAX_VELOCITY, payload, description)
        return self._read_packet()

    def control_mode(self, mode: int, description=None):
        if not description: description = f"(Alterar Modo de Controle - {mode})"
        self._send_packet(self.CMD_CONTROL_MODE, struct.pack('<B', mode), description)
        return self._read_packet()

    def set_pid_parameters(self, mode: int, kp: float, ki: float, kd: float, description=None):
        if not description:
            names = {0:"ID", 1:"IQ", 2:"Velocidade", 3:"Posição"}
            description = f"(Configurar PID {names.get(mode)} - Kp:{kp:.4f} Ki:{ki:.4f} Kd:{kd:.4f})"
        payload = struct.pack('<Bfff', mode, kp, ki, kd)
        self._send_packet(self.CMD_SET_PID_PARAMTERS, payload, description)
        return self._read_packet()

    def get_pid_parameters(self, mode: int, description=None):
        if not description:
            names = {0:"ID", 1:"IQ", 2:"Velocidade", 3:"Posição"}
            description = f"(Lendo Parâmetros PID {names.get(mode)})"
        payload = struct.pack('<B', mode)
        self._send_packet(self.CMD_GET_PID_PARAMETERS, payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_PID_PARAMETERS and payload and len(payload) == 13:
            return struct.unpack('<fff', payload[1:])
        return None

    def target_value(self, value: float, description=None):
        if not description: description = f"(Enviar Valor Alvo - {value:.2f})"
        payload = struct.pack('<f', value)
        self._send_packet(self.CMD_TARGET_VALUE, payload, description)
        return self._read_packet()

    def get_max_velocity(self, description="(Lendo Limite de Velocidade)"):
        self._send_packet(self.CMD_GET_MAX_VELOCITY, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_MAX_VELOCITY and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None
    
    def get_max_current(self, description="(Lendo Limite de Corrente)"):
        self._send_packet(self.CMD_GET_MAX_CURRENT, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_MAX_CURRENT and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None
    
    def get_max_voltage(self, description="(Lendo Limite de Tensão)"):
        self._send_packet(self.CMD_GET_MAX_VOLTAGE, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_MAX_VOLTAGE and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None

    def encoder_calibration(self, description="(Iniciar Calibração de Encoder)"):
        self._send_packet(self.CMD_ENCODER_CALIBRATION, empty_payload, description)
        return self._read_packet()

    def set_zero_position(self, description="(Definir Posição Zero)"):
        self._send_packet(self.CMD_SET_ZERO_POSITION, empty_payload, description)
        return self._read_packet()

    def get_wrapped_angle(self, description="(Lendo Ângulo Envolvido)"):
        self._send_packet(self.CMD_GET_WRAPPED_ANGLE, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_WRAPPED_ANGLE and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None

    def get_velocity(self, description="(Lendo Velocidade Atual)"):
        self._send_packet(self.CMD_GET_VELOCITY, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_VELOCITY and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None
    
    def get_phase_currents(self, description="(Lendo Correntes de Fase)"):
        self._send_packet(self.CMD_GET_PHASE_CURRENTS, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_PHASE_CURRENTS and payload and len(payload) == 8:
            return struct.unpack('<ff', payload)
        return None

    def get_dq_currents(self, description="(Lendo Correntes dq)"):
        self._send_packet(self.CMD_GET_DQ_CURRENTS, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_DQ_CURRENTS and payload and len(payload) == 8:
            return struct.unpack('<ff', payload)
        return None

    def get_encoder_offset(self, description="(Lendo Offset do Encoder)"):
        self._send_packet(self.CMD_GET_ENCODER_OFFSET, empty_payload, description)
        opcode, payload = self._read_packet()
        if opcode == self.CMD_GET_ENCODER_OFFSET and payload and len(payload) == 4:
            return struct.unpack('<f', payload)[0]
        return None
    
    def set_encoder_offset(self, offset: float, description=None):
        if not description:
            description = f"(Definir Offset do Encoder:{offset:.2f})"
        payload = struct.pack('<f', offset)
        self._send_packet(self.CMD_SET_ENCODER_OFFSET, payload, description)
        return self._read_packet()