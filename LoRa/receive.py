import time
import spidev
import RPi.GPIO as GPIO
from lora_driver import SX127x

# --- LoRa 모듈 설정 ---
# 사용하는 모듈의 핀 연결에 맞게 BCM 핀 번호 수정
CS_PIN = 8      # Chip Select (CE0)
DIO0_PIN = 24   # DIO0 (Interrupt Request)
RST_PIN = 25    # Reset Pin (옵션, 모듈에 RST 핀이 없다면 RST_PIN = None 으로 설정하거나 해당 라인 주석 처리)

# SPI 버스 및 디바이스 설정 (일반적으로 SPI 버스 0, 디바이스 0)
SPI_BUS = 0
SPI_DEVICE = 0

# LoRa 주파수 설정 (MHz) - 송신기와 동일하게 설정!
LORA_FREQUENCY = 920.0

# --- LoRa 파라미터 설정 ---
# 송신기와 동일하게 설정해야 합니다!
SPREADING_FACTOR = 7
BANDWIDTH = 125000  # 125 KHz
CODING_RATE = 5     # 4/5

# --- SPI 통신 초기화 ---
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = 1000000 # 1MHz

# --- GPIO 초기화 ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_PIN, GPIO.OUT)
GPIO.setup(DIO0_PIN, GPIO.IN, GPIO.PUD_UP) # 풀업 저항 설정
if RST_PIN is not None: # RST 핀이 설정된 경우에만 GPIO 설정
    GPIO.setup(RST_PIN, GPIO.OUT)

# --- SX127x LoRa 드라이버 초기화 ---
lora = SX127x(spi, cs_pin=CS_PIN, dio0_pin=DIO0_PIN, rst_pin=RST_PIN)

# --- LoRa 모듈 설정 함수 ---
def setup_lora_receiver():
    print("LoRa 수신 모듈 설정 중...")
    try:
        lora.setup(
            frequency=LORA_FREQUENCY,
            spreading_factor=SPREADING_FACTOR,
            bandwidth=BANDWIDTH,
            coding_rate=CODING_RATE,
            crc_enable=True # CRC 활성화로 데이터 무결성 검증
        )
        print(f"LoRa 수신 모듈 설정 완료: 주파수={LORA_FREQUENCY}MHz, SF={SPREADING_FACTOR}, BW={BANDWIDTH/1000}KHz")
        lora.receive() # 수신 모드 진입
        print("LoRa 패킷 수신 대기 중...")
    except Exception as e:
        print(f"LoRa 모듈 설정 오류: {e}")
        GPIO.cleanup()
        spi.close()
        exit()

# --- 데이터 수신 콜백 함수 ---
# DIO0 핀의 변화를 감지하여 호출되는 함수
def on_lora_receive(channel):
    global lora # lora 객체에 접근하기 위해 global 선언
    if lora.has_received_packet(): # 수신된 패킷이 있는지 확인
        try:
            packet_data = lora.read_packet() # 패킷 데이터 읽기
            
            # 수신 강도 (RSSI) 및 신호 대 잡음비 (SNR) 가져오기
            rssi = lora.get_last_rssi()
            snr = lora.get_last_snr()

            # 바이트 데이터를 문자열로 디코딩
            received_message = packet_data.decode('utf-8')
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) # UTC 시간

            print(f"\n[{current_time}] Packet Received!")
            print(f"  Data: '{received_message}'")
            print(f"  RSSI: {rssi} dBm, SNR: {snr} dB")

            # 다음 패킷 수신 대기 모드로 재전환 (중요!)
            lora.receive() 
        except Exception as e:
            print(f"  Error processing received packet: {e}")
            lora.receive() # 오류 발생 시에도 수신 대기 모드로 재전환 시도


# --- 메인 루프 ---
try:
    setup_lora_receiver()
    # DIO0 핀에 인터럽트 이벤트 감지 설정 (LoRa 모듈이 데이터 수신 시 알림)
    # RISING 엣지에서 on_lora_receive 함수 호출
    # bouncetime은 노이즈로 인한 중복 호출 방지
    GPIO.add_event_detect(DIO0_PIN, GPIO.RISING, callback=on_lora_receive, bouncetime=200)

    # 프로그램이 종료되지 않도록 무한 대기 (인터럽트 기반이므로 CPU 사용량 낮음)
    while True:
        time.sleep(1) # 주기적으로 다른 작업 수행 가능 (여기서는 단순히 대기)

except KeyboardInterrupt:
    print("\n수신 중단. LoRa 모듈 비활성화.")
except Exception as e:
    print(f"예상치 못한 에러 발생: {e}")
finally:
    lora.sleep() # LoRa 모듈을 슬립 모드로 전환하여 전력 소모 줄임
    spi.close()
    GPIO.cleanup()
    print("프로그램 종료.")