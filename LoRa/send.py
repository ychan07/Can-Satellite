# lora_sender.py (캔위성용)

import RPi.GPIO as GPIO
import spidev
import time
import sys

# LoRa 모듈 핀 설정 (Raspberry Pi 4B/3B/Zero W pinout.xyz 기준)
# CS_PIN: SPI Chip Select (CE0) - 물리적 핀 24번
# RST_PIN: Reset 핀 - 물리적 핀 22번 (BCM 25)
# DIO0_PIN: DIO0 핀 (인터럽트) - 물리적 핀 18번 (BCM 24)
CS_PIN = 8   # BCM 8 (CE0)
RST_PIN = 25 # BCM 25
DIO0_PIN = 24 # BCM 24

# SPI 설정 (Raspberry Pi의 기본 SPI 버스 및 장치)
SPI_BUS = 0
SPI_DEVICE = 0

# LoRa 레지스터 주소 (SX127x 데이터시트 참조)
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_PA_CONFIG = 0x09
REG_LNA = 0x0C
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_TX_BASE_ADDR = 0x0E
REG_FIFO_RX_BASE_ADDR = 0x0F
REG_FIFO_RX_CURRENT_ADDR = 0x10
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_PKT_SNR_VALUE = 0x19
REG_PKT_RSSI_VALUE = 0x1A
REG_MODEM_CONFIG1 = 0x1D
REG_MODEM_CONFIG2 = 0x1E
REG_SYMB_TIMEOUT_LSB = 0x1F
REG_PREAMBLE_MSB = 0x20
REG_PREAMBLE_LSB = 0x21
REG_PAYLOAD_LENGTH = 0x22
REG_MAX_PAYLOAD_LENGTH = 0x23
REG_HOP_PERIOD = 0x24
REG_DIO_MAPPING1 = 0x40
REG_VERSION = 0x42

# LoRa 모드
MODE_LONG_RANGE_MODE = 0x80
MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_TX = 0x03
MODE_RX_CONTINUOUS = 0x05
MODE_RX_SINGLE = 0x06

# IRQ 플래그
IRQ_TX_DONE_MASK = 0x08
IRQ_PAYLOAD_CRC_ERROR_MASK = 0x20
IRQ_RX_DONE_MASK = 0x40

# LoRa 클래스 정의
class LoRa:
    def __init__(self, spi_bus, spi_device, cs_pin, rst_pin, dio0_pin):
        self.cs_pin = cs_pin
        self.rst_pin = rst_pin
        self.dio0_pin = dio0_pin

        # GPIO 설정
        GPIO.setmode(GPIO.BCM) # BCM 핀 번호 모드 사용
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        GPIO.setup(self.dio0_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # DIO0을 입력으로 설정

        # SPI 초기화
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 1000000 # 1MHz

        # LoRa 모듈 리셋
        GPIO.output(self.rst_pin, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self.rst_pin, GPIO.HIGH)
        time.sleep(0.01)

        print("LoRa 모듈 초기화 중...")
        self.init_lora()

    def write_reg(self, address, value):
        GPIO.output(self.cs_pin, GPIO.LOW)
        self.spi.xfer2([address | 0x80, value]) # Write bit set (MSB)
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def read_reg(self, address):
        GPIO.output(self.cs_pin, GPIO.LOW)
        response = self.spi.xfer2([address & 0x7F, 0x00]) # Read bit cleared (MSB)
        GPIO.output(self.cs_pin, GPIO.HIGH)
        return response[1]

    def set_mode(self, mode):
        self.write_reg(REG_OP_MODE, mode)
        # print(f"모드 설정: {mode:02x}, 현재 모드: {self.read_reg(REG_OP_MODE):02x}")
        time.sleep(0.01) # 모드 변경 후 안정화 시간

    def init_lora(self):
        # LoRa 모드 (Long Range Mode) 활성화 및 Sleep 모드 진입
        self.set_mode(MODE_SLEEP | MODE_LONG_RANGE_MODE)

        # 주파수 설정 (예: 433MHz)
        # F_RF = F_OSC * FRF / 2^19
        # 433MHz = 32MHz * FRF / 524288
        # FRF = 433e6 * 524288 / 32e6 = 7076736 (0x6C8000)
        frf = int(433.0e6 / (32.0e6 / 524288.0))
        self.write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self.write_reg(REG_FRF_MID, (frf >> 8) & 0xFF)
        self.write_reg(REG_FRF_LSB, frf & 0xFF)

        # PA_BOOST 활성화 (고출력)
        self.write_reg(REG_PA_CONFIG, 0xFF) # Max power

        # LNA (Low Noise Amplifier) 설정
        self.write_reg(REG_LNA, 0x23) # LNA gain set to G1, LNA boost enabled

        # 모뎀 설정 1 (BW, Coding Rate, Implicit Header Mode)
        # BW: 125kHz (0x70), CR: 4/5 (0x02), Explicit Header Off (0x00) -> 0x72
        self.write_reg(REG_MODEM_CONFIG1, 0x72) # BW 125kHz, CR 4/5, Explicit Header

        # 모뎀 설정 2 (Spreading Factor, TX Continuous Mode, CRC Enable)
        # SF: 7 (0x70), TX Continuous Off (0x00), CRC On (0x04) -> 0x74
        self.write_reg(REG_MODEM_CONFIG2, 0x74) # SF7, CRC On

        # 심볼 타임아웃 설정
        self.write_reg(REG_SYMB_TIMEOUT_LSB, 0x64) # 100 symbols

        # 프리앰블 길이 설정 (Preamble Length)
        self.write_reg(REG_PREAMBLE_MSB, 0x00)
        self.write_reg(REG_PREAMBLE_LSB, 0x08) # 8 symbols

        # FIFO TX Base Address 설정
        self.write_reg(REG_FIFO_TX_BASE_ADDR, 0x00)
        self.write_reg(REG_FIFO_RX_BASE_ADDR, 0x00)

        # DIO0 맵핑 (TxDone 인터럽트)
        self.write_reg(REG_DIO_MAPPING1, 0x00) # DIO0 -> TxDone

        # Standby 모드로 전환
        self.set_mode(MODE_STDBY)
        print("LoRa 모듈 초기화 완료.")

    def send_packet(self, data):
        self.set_mode(MODE_STDBY) # Standby 모드로 전환
        self.write_reg(REG_FIFO_ADDR_PTR, 0x00) # FIFO 포인터 초기화

        # FIFO에 데이터 쓰기
        for byte in data:
            self.write_reg(REG_FIFO, byte)

        self.write_reg(REG_PAYLOAD_LENGTH, len(data)) # 페이로드 길이 설정

        # TX 모드로 전환하여 전송 시작
        self.set_mode(MODE_TX)

        # TxDone 인터럽트 대기
        # DIO0 핀이 HIGH가 될 때까지 기다립니다.
        start_time = time.time()
        while not GPIO.input(self.dio0_pin):
            if time.time() - start_time > 5: # 5초 타임아웃
                print("TX Done 대기 중 타임아웃 발생.")
                break
            time.sleep(0.001)

        # IRQ 플래그 읽기 및 초기화
        irq_flags = self.read_reg(REG_IRQ_FLAGS)
        self.write_reg(REG_IRQ_FLAGS, irq_flags) # 플래그 초기화

        if (irq_flags & IRQ_TX_DONE_MASK):
            print(f"패킷 전송 완료: {data.decode('utf-8')}")
        else:
            print("패킷 전송 실패 또는 TxDone IRQ 발생 안함.")

        self.set_mode(MODE_STDBY) # 전송 후 Standby 모드로 복귀

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()
        print("GPIO 및 SPI 정리 완료.")

# 메인 실행 부분
if __name__ == "__main__":
    lora = None
    try:
        lora = LoRa(SPI_BUS, SPI_DEVICE, CS_PIN, RST_PIN, DIO0_PIN)
        
        packet_count = 0
        while True:
            message = f"Hello from CanSat! Packet: {packet_count}"
            lora.send_packet(message.encode('utf-8'))
            packet_count += 1
            time.sleep(5) # 5초마다 전송

    except KeyboardInterrupt:
        print("\n프로그램 종료 요청.")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if lora:
            lora.cleanup()

