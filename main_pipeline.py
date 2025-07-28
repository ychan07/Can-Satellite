

import os
import time
import numpy as np
from scipy.fft import fft, fftshift
from rtlsdr import RtlSdr
import board
import busio
import adafruit_bmp280

# LoRa 모듈 임포트 (LoRa 폴더에 접근 가능해야 함)
# 이 스크립트를 프로젝트 루트에서 실행한다고 가정합니다.
from LoRa.LoRa_module import LoRaComms

# --- 설정 (Configuration) ---

# 고도 트리거 설정
ASCENT_THRESHOLD_M = 10.0  # 관측 준비를 시작할 최소 고도 (미터)
DESCENT_TRIGGER_M = 1.0    # 하강으로 판단하고 관측을 시작할 고도 변화 (미터)

# SDR 설정
SDR_CENTER_FREQ = 1420.405751e6  # 21cm 중성수소선 주파수 (Hz)
SDR_SAMPLE_RATE = 2.048e6        # 샘플링 속도 (SPS)
SDR_NUM_SAMPLES = 2**16          # FFT를 위한 샘플 개수
SDR_GAIN = 15                    # SDR 수신 게인 (dB)

# 데이터 저장 설정
DATA_BASE_DIR = "Cansat_data"
OBSERVATION_DIR = os.path.join(DATA_BASE_DIR, "observation")

# --- 초기화 (Initialization) ---

def initialize_lora():
    """LoRa 통신 모듈을 초기화하고 핸들러를 반환합니다."""
    try:
        lora_handler = LoRaComms()
        if lora_handler.node:
            print("LoRa module initialized successfully.")
            lora_handler.send_message("INFO: LoRa module ready.")
            return lora_handler
        else:
            print("Warning: LoRa module initialization failed.")
            return None
    except Exception as e:
        print(f"Error initializing LoRa: {e}")
        return None

def initialize_sdr():
    """RTL-SDR을 초기화하고 객체를 반환합니다."""
    try:
        sdr = RtlSdr()
        sdr.sample_rate = SDR_SAMPLE_RATE
        sdr.center_freq = SDR_CENTER_FREQ
        sdr.gain = SDR_GAIN
        print(f"SDR initialized: Freq={sdr.center_freq/1e6:.2f}MHz, Rate={sdr.sample_rate/1e6:.2f}MSps, Gain={sdr.gain}dB")
        return sdr
    except Exception as e:
        print(f"Error initializing SDR: {e}")
        return None

def initialize_sensor():
    """BMP280 고도 센서를 초기화하고 객체를 반환합니다."""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
        # 중요: 정확한 고도 측정을 위해 현장의 해수면 기압으로 보정해야 합니다.
        bmp280.sea_level_pressure = 1013.25
        print("BMP280 altitude sensor initialized.")
        return bmp280
    except Exception as e:
        print(f"Error initializing BMP280 sensor: {e}")
        return None

# --- 핵심 기능 (Core Functions) ---

def get_altitude(sensor):
    """센서로부터 현재 고도를 읽어 반환합니다."""
    try:
        return sensor.altitude
    except Exception as e:
        print(f"Warning: Failed to read altitude - {e}")
        return None # 오류 발생 시 None 반환

def capture_and_save_spectrum(sdr, save_dir):
    """
    SDR에서 데이터를 캡처하고, 스펙트럼을 계산한 후,
    toolbox.py와 호환되는 형식으로 파일에 저장합니다.
    """
    try:
        # 1. I/Q 데이터 수집
        samples = sdr.read_samples(SDR_NUM_SAMPLES)

        # 2. FFT 및 파워 스펙트럼 계산
        spectrum = fftshift(fft(samples))
        power_spectrum_db = 10 * np.log10(np.abs(spectrum)**2 + 1e-12)

        # 3. 주파수 축 생성 및 MHz로 변환
        freqs = np.fft.fftfreq(SDR_NUM_SAMPLES, d=1/SDR_SAMPLE_RATE)
        freqs_mhz = (fftshift(freqs) + SDR_CENTER_FREQ) / 1e6

        # 4. toolbox 호환을 위한 더미 열 추가
        dummy_col = np.zeros_like(power_spectrum_db)

        # 5. 타임스탬프 파일명으로 저장 (공백 분리, 헤더 없음)
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        filename = os.path.join(save_dir, f"{timestamp}.csv")
        
        np.savetxt(filename, np.column_stack([freqs_mhz, power_spectrum_db, dummy_col]),
                   delimiter=' ', header='', comments='')
        
        return os.path.basename(filename)

    except Exception as e:
        print(f"Error during spectrum capture/save: {e}")
        return None

# --- 메인 파이프라인 (Main Pipeline) ---

def main():
    """메인 자동 관측 파이프라인을 실행합니다."""
    
    # 디렉토리 생성
    if not os.path.exists(OBSERVATION_DIR):
        os.makedirs(OBSERVATION_DIR)
        print(f"Created data directory: {OBSERVATION_DIR}")

    # 1. 모듈 초기화
    lora = initialize_lora()
    sdr = initialize_sdr()
    sensor = initialize_sensor()

    if not all([lora, sdr, sensor]):
        error_msg = "FATAL: Initialization failed. Check connections and permissions."
        print(error_msg)
        if lora:
            lora.send_message(error_msg)
        return # 필수 모듈 중 하나라도 실패하면 종료

    # 초기 상태 설정
    state = "WAITING_FOR_ASCENT"
    peak_altitude = 0.0
    last_lora_time = 0
    
    if lora:
        lora.send_message("INFO: Pipeline starting. Waiting for ascent.")

    try:
        while True:
            current_altitude = get_altitude(sensor)
            if current_altitude is None: # 고도 읽기 실패 시
                time.sleep(1)
                continue

            # 최고 고도 갱신
            if current_altitude > peak_altitude:
                peak_altitude = current_altitude

            # --- 상태 머신 (State Machine) ---

            if state == "WAITING_FOR_ASCENT":
                if peak_altitude > ASCENT_THRESHOLD_M:
                    state = "ARMED_FOR_DESCENT"
                    msg = f"INFO: Ascent detected (>{ASCENT_THRESHOLD_M}m). Armed for descent."
                    print(msg)
                    if lora:
                        lora.send_message(msg)
                # 5초마다 LoRa 메시지 전송
                elif time.time() - last_lora_time > 5:
                    msg = f"STATE: Waiting for ascent. Alt: {current_altitude:.1f}m / Peak: {peak_altitude:.1f}m"
                    print(msg)
                    if lora:
                        lora.send_message(msg)
                    last_lora_time = time.time()

            elif state == "ARMED_FOR_DESCENT":
                if current_altitude < peak_altitude - DESCENT_TRIGGER_M:
                    state = "OBSERVING"
                    msg = f"ACTION: Descent detected! Alt: {current_altitude:.1f}m. Starting observation."
                    print(msg)
                    if lora:
                        lora.send_message(msg)
                # 2초마다 LoRa 메시지 전송
                elif time.time() - last_lora_time > 2:
                    msg = f"STATE: Armed. Alt: {current_altitude:.1f}m / Peak: {peak_altitude:.1f}m"
                    print(msg)
                    if lora:
                        lora.send_message(msg)
                    last_lora_time = time.time()

            elif state == "OBSERVING":
                # 1초에 한 번 관측 및 저장
                filename = capture_and_save_spectrum(sdr, OBSERVATION_DIR)
                if filename:
                    msg = f"OBS: Alt: {current_altitude:.1f}m. Saved {filename}"
                    print(msg)
                    if lora:
                        lora.send_message(msg)
                else:
                    msg = f"ERROR: Failed to save spectrum data. Alt: {current_altitude:.1f}m"
                    print(msg)
                    if lora:
                        lora.send_message(msg)
            
            time.sleep(1) # 메인 루프 주기

    except KeyboardInterrupt:
        print("\nPipeline stopped by user.")
        if lora:
            lora.send_message("INFO: Pipeline stopped by user.")
    except Exception as e:
        error_msg = f"FATAL_ERROR: {e}"
        print(error_msg)
        if lora:
            lora.send_message(error_msg)
    finally:
        # 자원 정리
        if sdr:
            sdr.close()
        if lora and lora.node:
            lora.cleanup()
        print("Resources cleaned up. Exiting.")

if __name__ == "__main__":
    main()
