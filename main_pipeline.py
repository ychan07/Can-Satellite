

import os
import time
from collections import deque
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

# 상태 감지 설정 (State Detection Configuration)
LOOP_INTERVAL_S = 0.5        # 메인 루프 주기 (초)
MOVING_AVG_SIZE = 5          # 이동 평균을 계산할 샘플 개수
ASCENT_SPEED_THRESHOLD = 0.5   # 상승으로 판단할 최소 수직 속도 (m/s)
DESCENT_SPEED_THRESHOLD = -0.5 # 하강으로 판단할 최소 수직 속도 (m/s)
ASCENT_CONFIRMATION_COUNT = 5  # 상승 상태를 확정하기 위한 연속 만족 횟수
DESCENT_CONFIRMATION_COUNT = 3 # 하강 상태를 확정하기 위한 연속 만족 횟수

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
        if lora: lora.send_message(error_msg)
        return

    # --- 고급 상태 감지 로직 초기화 ---
    altitude_window = deque(maxlen=MOVING_AVG_SIZE)
    velocity_window = deque(maxlen=MOVING_AVG_SIZE)
    
    # 초기 고도 안정화 (필터 예열)
    print("Calibrating initial altitude...")
    try:
        initial_readings = [sensor.altitude for _ in range(MOVING_AVG_SIZE)]
        altitude_window.extend(initial_readings)
    except Exception as e:
        error_msg = f"FATAL: Could not get initial altitude. Error: {e}"
        print(error_msg)
        if lora: lora.send_message(error_msg)
        return

    last_altitude_smoothed = np.mean(altitude_window)
    last_time = time.monotonic()
    print(f"Initial altitude calibrated to: {last_altitude_smoothed:.2f}m")

    # 상태 변수 초기화
    state = "GROUND"
    ascent_counter = 0
    descent_counter = 0
    last_lora_time = 0

    if lora:
        lora.send_message(f"INFO: Pipeline ready. State: GROUND. Alt: {last_altitude_smoothed:.1f}m")

    # 첫 루프의 시간 간격(time_delta)을 정확히 하기 위해 한번 기다림
    time.sleep(LOOP_INTERVAL_S)

    try:
        while True:
            current_time = time.monotonic()
            
            # 1. 고도 및 속도 계산
            try:
                raw_altitude = sensor.altitude
            except Exception as e:
                print(f"Warning: Failed to read altitude - {e}")
                time.sleep(LOOP_INTERVAL_S)
                continue

            altitude_window.append(raw_altitude)
            smoothed_altitude = np.mean(altitude_window)
            
            time_delta = current_time - last_time
            vertical_velocity = (smoothed_altitude - last_altitude_smoothed) / time_delta if time_delta > 0 else 0
            velocity_window.append(vertical_velocity)
            smoothed_velocity = np.mean(velocity_window)

            # 2. 상태 머신 (State Machine)
            if state == "GROUND":
                if smoothed_velocity > ASCENT_SPEED_THRESHOLD:
                    ascent_counter += 1
                    if ascent_counter >= ASCENT_CONFIRMATION_COUNT:
                        state = "ASCENDING"
                        msg = f"STATE_CHANGE: Ascent detected. Now ASCENDING. Alt: {smoothed_altitude:.1f}m, Vel: {smoothed_velocity:+.1f}m/s"
                        print(msg)
                        if lora: lora.send_message(msg)
                        # 상태 전환 시 반대편 카운터는 확실히 리셋
                        descent_counter = 0 
                else:
                    # 상승 조건이 아닐 때는 항상 리셋
                    ascent_counter = 0

            elif state == "ASCENDING":
                if smoothed_velocity < DESCENT_SPEED_THRESHOLD:
                    descent_counter += 1
                    if descent_counter >= DESCENT_CONFIRMATION_COUNT:
                        state = "OBSERVING"
                        msg = f"STATE_CHANGE: Descent detected. Now OBSERVING. Alt: {smoothed_altitude:.1f}m, Vel: {smoothed_velocity:+.1f}m/s"
                        print(msg)
                        if lora: lora.send_message(msg)
                        ascent_counter = 0
                else:
                    descent_counter = 0

            elif state == "OBSERVING":
                # 관측 상태에서는 스펙트럼 캡처 및 저장
                filename = capture_and_save_spectrum(sdr, OBSERVATION_DIR)
                if filename:
                    # 관측 성공 메시지는 2초마다 전송 (너무 자주 보내지 않도록)
                    if time.time() - last_lora_time > 2:
                        msg = f"OBS: Alt: {smoothed_altitude:.1f}m, Vel: {smoothed_velocity:+.1f}m/s. Saved {filename}"
                        print(msg)
                        if lora: lora.send_message(msg)
                        last_lora_time = time.time()
                else:
                    msg = f"ERROR: Failed to save spectrum data. Alt: {smoothed_altitude:.1f}m"
                    print(msg)
                    if lora: lora.send_message(msg)
            
            # 주기적인 상태 보고 (2초마다)
            if time.time() - last_lora_time > 2 and state != "OBSERVING":
                msg = f"STATUS: {state}. Alt: {smoothed_altitude:.1f}m, Vel: {smoothed_velocity:+.1f}m/s, Cnt(A/D):{ascent_counter}/{descent_counter}"
                print(msg)
                if lora: lora.send_message(msg)
                last_lora_time = time.time()

            # 현재 상태를 다음 루프를 위해 저장
            last_altitude_smoothed = smoothed_altitude
            last_time = current_time

            time.sleep(LOOP_INTERVAL_S)

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
