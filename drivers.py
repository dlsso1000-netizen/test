"""
로스터기 드라이버 모듈
각 장비에 맞는 드라이버를 제공합니다.
"""
import random
import time

class BaseDriver:
    """기본 드라이버 클래스"""
    def __init__(self, config):
        self.config = config
        self.connected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def read_temps(self):
        raise NotImplementedError


class SimulationDriver(BaseDriver):
    """시뮬레이션 드라이버 (테스트용)"""
    def __init__(self, config):
        super().__init__(config)
        self.bt = 25.0  # 초기 원두 온도
        self.et = 30.0  # 초기 배기 온도
        self.start_time = None

    def connect(self):
        super().connect()
        self.start_time = time.time()
        self.bt = 25.0
        self.et = 30.0

    def read_temps(self):
        """시뮬레이션된 온도 데이터 반환"""
        if self.start_time is None:
            self.start_time = time.time()

        elapsed = time.time() - self.start_time
        minutes = elapsed / 60.0

        # 로스팅 곡선 시뮬레이션
        if minutes < 1:
            # 초기 하락 (Turning Point 전)
            self.bt = 25 + minutes * 80 - random.uniform(0, 5)
        elif minutes < 3:
            # Turning Point 이후 상승
            self.bt = 100 + (minutes - 1) * 30 + random.uniform(-2, 2)
        elif minutes < 6:
            # Yellowing 구간
            self.bt = 160 + (minutes - 3) * 15 + random.uniform(-1, 1)
        elif minutes < 9:
            # 1st Crack 접근
            self.bt = 205 + (minutes - 6) * 8 + random.uniform(-1, 1)
        else:
            # 1st Crack 이후
            self.bt = min(230, 229 + (minutes - 9) * 2 + random.uniform(-0.5, 0.5))

        # ET는 BT보다 항상 약간 높음
        self.et = self.bt + 15 + random.uniform(-3, 3)

        return round(self.bt, 1), round(self.et, 1)


class ModbusDriver(BaseDriver):
    """Modbus 기반 드라이버 (Easyster, Proaster 등)"""
    def __init__(self, config):
        super().__init__(config)
        self.port = config.get('port', 'COM3')
        self.client = None

    def connect(self):
        try:
            from pymodbus.client import ModbusSerialClient
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=9600,
                timeout=1
            )
            if self.client.connect():
                super().connect()
            else:
                raise ConnectionError(f"포트 {self.port}에 연결할 수 없습니다.")
        except ImportError:
            raise ImportError("pymodbus 라이브러리가 필요합니다. pip install pymodbus")

    def disconnect(self):
        if self.client:
            self.client.close()
        super().disconnect()

    def read_temps(self):
        if not self.connected or not self.client:
            return 0.0, 0.0

        try:
            # 레지스터 주소는 장비마다 다름 (예시)
            result = self.client.read_holding_registers(0, 2, slave=1)
            if result.isError():
                return 0.0, 0.0
            bt = result.registers[0] / 10.0
            et = result.registers[1] / 10.0
            return bt, et
        except Exception:
            return 0.0, 0.0


class USBTempDriver(BaseDriver):
    """USB 온도계 드라이버 (Center 306 등)"""
    def __init__(self, config):
        super().__init__(config)
        self.port = config.get('port', 'COM3')
        self.serial = None

    def connect(self):
        try:
            import serial
            self.serial = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=1
            )
            super().connect()
        except ImportError:
            raise ImportError("pyserial 라이브러리가 필요합니다. pip install pyserial")
        except Exception as e:
            raise ConnectionError(f"시리얼 포트 연결 실패: {e}")

    def disconnect(self):
        if self.serial:
            self.serial.close()
        super().disconnect()

    def read_temps(self):
        if not self.connected or not self.serial:
            return 0.0, 0.0

        try:
            # Center 306 프로토콜 (예시)
            self.serial.write(b'\x02\x00\x00\x00\x03')
            response = self.serial.read(10)
            if len(response) >= 6:
                bt = (response[2] * 256 + response[3]) / 10.0
                et = (response[4] * 256 + response[5]) / 10.0
                return bt, et
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0


class WebSocketDriver(BaseDriver):
    """WebSocket 기반 드라이버 (Probat 등)"""
    def __init__(self, config):
        super().__init__(config)
        self.url = config.get('url', 'ws://localhost:8080')
        self.ws = None
        self.last_bt = 0.0
        self.last_et = 0.0

    def connect(self):
        # WebSocket은 비동기이므로 간단한 구현
        super().connect()

    def read_temps(self):
        # 실제 구현에서는 WebSocket에서 데이터 수신
        return self.last_bt, self.last_et


# 드라이버 팩토리 함수
def get_driver(device_name: str, config: dict) -> BaseDriver:
    """장비 이름에 맞는 드라이버 인스턴스 반환"""

    drivers = {
        "Simulation (가상)": SimulationDriver,
        "Easyster (Modbus)": ModbusDriver,
        "Proaster (Modbus)": ModbusDriver,
        "Center 306 (USB)": USBTempDriver,
        "Probat (WebSocket)": WebSocketDriver,
    }

    driver_class = drivers.get(device_name)
    if driver_class is None:
        raise ValueError(f"지원하지 않는 장비입니다: {device_name}")

    return driver_class(config)
