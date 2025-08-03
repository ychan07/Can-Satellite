import time
import subprocess
import sys
import os
import threading
from collections import deque

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from LoRa.LoRa_module import LoRaComms
import board
import busio
import adafruit_bmp280

# --- Configuration ---
DESCENT_THRESHOLD = 3  # 낙하 감지 고도 변화량 (미터)
LANDING_TIME_WINDOW = 5  # 착지 감지를 위한 시간 (초)
LANDING_ALTITUDE_THRESHOLD = 0.5  # 착지 감지를 위한 고도 변화량 (미터)
ALTITUDE_READ_INTERVAL = 1  # 고도 측정 간격 (초)

lora_handler = None
sdr_process = None
stop_sdr_event = threading.Event()

def print_and_lora_send(message):
    """Prints a message to the console and sends it via LoRa."""
    print(message)
    if lora_handler and lora_handler.node:
        lora_handler.send_message(message)

def get_altitude():
    """BMP280 센서로부터 현재 고도를 읽어옵니다."""
    try:
        return bmp280.altitude
    except Exception as e:
        print_and_lora_send(f"Error: Failed to read altitude: {e}")
        return None

def run_sdr_measurement_thread():
    """SDR 측정을 별도의 스레드에서 실행합니다."""
    global sdr_process
    sdr_script_path = os.path.join(os.path.dirname(__file__), 'sdr(prac)', 'code.py')
    sdr_working_dir = os.path.join(os.path.dirname(__file__), 'sdr(prac)')

    if not os.path.exists(sdr_script_path):
        print_and_lora_send(f"Error: SDR script not found: {sdr_script_path}")
        return

    print_and_lora_send(f"Starting SDR measurement script: {sdr_script_path}")
    try:
        # Popen을 사용하여 비동기적으로 실행하고, stop_sdr_event를 감시
        sdr_process = subprocess.Popen(['python', sdr_script_path], cwd=sdr_working_dir)
        
        # stop_sdr_event가 설정될 때까지 대기
        stop_sdr_event.wait()

        # 이벤트가 설정되면 SDR 프로세스 종료
        print_and_lora_send("Stopping SDR measurement...")
        sdr_process.terminate()
        sdr_process.wait() # 프로세스가 완전히 종료될 때까지 대기
        print_and_lora_send("SDR measurement stopped.")

    except subprocess.CalledProcessError as e:
        print_and_lora_send(f"Error: SDR measurement script failed: {e}")
    except FileNotFoundError:
        print_and_lora_send("Error: 'python' command not found. Make sure Python is installed and in your PATH.")
    except Exception as e:
        print_and_lora_send(f"An unexpected error occurred in SDR thread: {e}")


def main():
    global lora_handler
    print_and_lora_send("--- Can-Satellite Autonomous Pipeline ---")

    # --- Initialize LoRa ---
    lora_handler = LoRaComms()
    if not lora_handler.node:
        print_and_lora_send("Warning: LoRa module initialization failed.")

    # --- Initialize BMP280 Sensor ---
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        global bmp280
        bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
        bmp280.sea_level_pressure = 1013.25
        print_and_lora_send("BMP280 altitude sensor initialized.")
    except Exception as e:
        print_and_lora_send(f"Error: Could not initialize BMP280 sensor: {e}")
        sys.exit(1)

    # --- Wait for Descent ---
    print_and_lora_send("Waiting for descent...")
    last_altitude = get_altitude()
    if last_altitude is None:
        print_and_lora_send("Could not get initial altitude. Exiting.")
        return

    while True:
        time.sleep(ALTITUDE_READ_INTERVAL)
        current_altitude = get_altitude()
        if current_altitude is None:
            continue

        altitude_change = last_altitude - current_altitude
        print(f"Current Alt: {current_altitude:.2f}m, Change: {altitude_change:.2f}m")

        if altitude_change > DESCENT_THRESHOLD:
            print_and_lora_send(f"Descent detected! (Drop: {altitude_change:.2f}m)")
            break
        
        # 낙하하지 않았으면 현재 고도를 이전 고도로 업데이트
        if current_altitude < last_altitude:
            last_altitude = current_altitude


    # --- Start SDR Measurement ---
    sdr_thread = threading.Thread(target=run_sdr_measurement_thread)
    sdr_thread.start()
    print_and_lora_send("SDR measurement started in background.")

    # --- Wait for Landing ---
    print_and_lora_send("Monitoring for landing...")
    altitude_history = deque(maxlen=LANDING_TIME_WINDOW)
    
    while sdr_thread.is_alive():
        current_altitude = get_altitude()
        if current_altitude is not None:
            altitude_history.append(current_altitude)

            if len(altitude_history) == LANDING_TIME_WINDOW:
                altitude_variation = max(altitude_history) - min(altitude_history)
                print(f"Altitude variation in last {LANDING_TIME_WINDOW}s: {altitude_variation:.2f}m")

                if altitude_variation < LANDING_ALTITUDE_THRESHOLD:
                    print_and_lora_send(f"Landing detected! (Variation: {altitude_variation:.2f}m)")
                    stop_sdr_event.set() # SDR 중지 신호 전송
                    break
        
        time.sleep(1)

    # --- Finalization ---
    sdr_thread.join() # SDR 스레드가 완전히 종료될 때까지 대기
    if lora_handler and lora_handler.node:
        lora_handler.cleanup()
    print_and_lora_send("Pipeline finished.")


if __name__ == "__main__":
    main()
