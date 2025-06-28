import time
import spidev
import RPi.GPIO as GPIO
from lora_driver import SX127x

# --- LoRa 모듈 설정 ---
# 사용하는 모듈의 핀 연결에 맞게 BCM 핀 번호 수정
# Raspberry Pi Zero W 기준으로 예시
CS_PIN = 8      # Chip Select (CE0)
DIO0_PIN = 24   # DIO0 (Interrupt Request)
RST_PIN = 25    # Reset Pin (옵션, 모듈에 RST 핀이 없다면 RST_PIN = None 으로 설정하거나 해당 라인 주석 처리)

# SPI 버스 및 디바이스 설정 (일반적으로 SPI 버스 0, 디바이스 0)
SPI_BUS = 0
SPI_DEVICE = 0

# LoRa 주파수 설정 (MHz) - 한국 규제: 917 ~ 923.5 MHz
LORA_FREQUENCY = 920.0

# --- LoRa 파라미터 설정 ---
# 송신기와 수신기는 이 파라미터들이 정확히 일치해야 통신 가능
SPREADING_FACTOR = 7    # 7 ~ 12 (높을수록 통신 거리 증가, 데이터 전송 속도 감소)
BANDWIDTH = 125000      # 125 KHz (높을수록 데이터 전송 속도 증가, 감도 감소)
CODING_RATE = 5         # 4/5 (높을수록 오류 수정 능력 증가, 전송 시간 증가)

# --- SPI 통신 초기화 ---
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = 1000000 # 1MHz (SPI 속도)

# --- GPIO 초기화 ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.setup(DIO0_PIN, GPIO.IN, GPIO.PUD_UP) # 풀업 저항 설정
if RST_PIN is not None: # RST 핀이 설정된 경우에만 GPIO 설정
    GPIO.setup(RST_PIN, GPIO.OUT)

# --- SX127x LoRa 드라이버 초기화 ---
# RST_PIN이 없는 모듈은 rst_pin=None으로 설정
lora = SX127x(spi, cs_pin=CS_PIN, dio0_pin=DIO0_PIN, rst_pin=RST_PIN)

# --- LoRa 모듈 설정 함수 ---
def setup_lora_transmitter():
    print("LoRa 송신 모듈 설정 중...")
    try:
        lora.setup(
            frequency=LORA_FREQUENCY,
            spreading_factor=SPREADING_FACTOR,
            bandwidth=BANDWIDTH,
            coding_rate=CODING_RATE,
            crc_enable=True # CRC 활성화로 데이터 무결성 검증
            # tx_power=14, # 송신 파워 (dBm), 필요 시 설정
            # preamble_length=8, # 프리앰블 길이, 기본값 사용 권장
            # implicit_header=False, # 명시적 헤더, 기본값 사용 권장
        )
        print(f"LoRa 송신 모듈 설정 완료: 주파수={LORA_FREQUENCY}MHz, SF={SPREADING_FACTOR}, BW={BANDWIDTH/1000}KHz")
    except Exception as e:
        print(f"LoRa 모듈 설정 오류: {e}")
        GPIO.cleanup()
        spi.close()
        exit()

# --- 메인 루프 ---
try:
    setup_lora_transmitter()
    packet_count = 0
    while True:
        test_message = f"Hello LoRa from CanSat! Packet {packet_count}"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}] Sending: {test_message}")

        try:
            # 메시지를 바이트 형태로 인코딩하여 전송
            lora.send_packet(test_message.encode('utf-8'))
            print("  Packet sent successfully!")
        except Exception as e:
            print(f"  Error sending packet: {e}")

        packet_count += 1
        time.sleep(5) # 5초마다 데이터 전송

except KeyboardInterrupt:
    print("\n송신 중단. LoRa 모듈 비활성화.")
except Exception as e:
    print(f"예상치 못한 에러 발생: {e}")
finally:
    lora.sleep() # LoRa 모듈을 슬립 모드로 전환하여 전력 소모 줄임
    spi.close()
    GPIO.cleanup()
    print("프로그램 종료.")