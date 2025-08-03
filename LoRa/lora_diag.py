# lora_diag.py
# LoRa 모듈의 초기화 과정을 단계별로 실행하며 상세한 진단 정보를 출력합니다.

import time
import sys

# RPi.GPIO와 serial 라이브러리를 직접 사용합니다.
try:
    import RPi.GPIO as GPIO
    import serial
except ImportError as e:
    print(f"오류: 필수 라이브러리를 찾을 수 없습니다. ({e})")
    print("pip install RPi.GPIO pyserial 명령어로 설치해주세요.")
    sys.exit(1)

# --- sx126x.py에서 가져온 기본 설정 ---
M0 = 22
M1 = 27
SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 9600

# 설정 레지스터 값 (C2: 전원 꺼지면 설정 초기화)
CFG_REG = [0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x12, 0x43, 0x00, 0x00]

def main():
    ser = None
    print("--- LoRa 모듈 상세 진단 시작 ---")

    # --- 1단계: GPIO 핀 초기화 ---
    try:
        print("\n[1/5] GPIO 핀 초기화를 시도합니다...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(M0, GPIO.OUT)
        GPIO.setup(M1, GPIO.OUT)
        print("  > 성공: GPIO 핀(M0, M1)을 출력 모드로 설정했습니다.")
    except Exception as e:
        print(f"  > 실패: GPIO 핀 초기화 중 오류가 발생했습니다.")
        print(f"    오류 메시지: {e}")
        print("    (sudo 권한으로 실행했는지 확인하세요)")
        return

    # --- 2단계: 시리얼 포트 열기 ---
    try:
        print(f"\n[2/5] 시리얼 포트({SERIAL_PORT}) 열기를 시도합니다...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.flushInput()
        print(f"  > 성공: 시리얼 포트({SERIAL_PORT})를 열었습니다.")
    except serial.SerialException as e:
        print(f"  > 실패: 시리얼 포트를 열 수 없습니다.")
        print(f"    오류 메시지: {e}")
        if "Permission denied" in str(e):
            print("    해결책: sudo를 사용하거나 'sudo usermod -a -G dialout $USER' 명령어로 사용자에게 권한을 부여하세요.")
        elif "No such file or directory" in str(e):
            print(f"    해결책: {SERIAL_PORT}가 올바른 포트 이름인지, raspi-config에서 시리얼 포트가 활성화되었는지 확인하세요.")
        return
    except Exception as e:
        print(f"  > 실패: 예상치 못한 오류가 발생했습니다.")
        print(f"    오류 메시지: {e}")
        return

    # --- 3단계: 설정 모드 진입 ---
    print("\n[3/5] LoRa 모듈을 설정 모드로 전환합니다...")
    GPIO.output(M0, GPIO.LOW)
    GPIO.output(M1, GPIO.HIGH)
    print("  > 완료: M0=LOW, M1=HIGH로 설정했습니다.")
    time.sleep(0.1)

    # --- 4단계: 설정 값 전송 및 응답 확인 (가장 중요) ---
    try:
        print("\n[4/5] 설정 값을 LoRa 모듈에 전송합니다...")
        ser.write(bytes(CFG_REG))
        print(f"  > 전송 완료: {len(CFG_REG)} 바이트의 설정 값을 보냈습니다.")
        
        print("  > 모듈의 응답을 1초간 기다립니다...")
        time.sleep(1)
        
        bytes_waiting = ser.inWaiting()
        if bytes_waiting > 0:
            response = ser.read(bytes_waiting)
            print(f"  > 성공: 모듈로부터 {len(response)} 바이트의 응답을 받았습니다!")
            # 응답 받은 데이터를 16진수로 보기 좋게 출력
            print(f"    응답 데이터: {' '.join([f'0x{b:02X}' for b in response])}")
            if response[0] == 0xC1:
                print("    진단: 응답의 첫 바이트가 0xC1으로, 정상적인 설정 응답으로 보입니다.")
            else:
                print("    진단: 응답의 첫 바이트가 0xC1이 아닙니다. 설정이 올바르게 적용되지 않았을 수 있습니다.")
        else:
            print("  > 실패: 모듈로부터 아무런 응답이 없습니다.")
            print("    진단: 이 경우, 문제는 거의 항상 하드웨어 연결 문제입니다.")
            print("      1. LoRa HAT이 라즈베리파이 GPIO에 완전히 꽂혔는지 확인하세요.")
            print("      2. 라즈베리파이와 LoRa 모듈에 안정적인 전원이 공급되는지 확인하세요.")
            print("      3. (드문 경우) LoRa 모듈 자체의 결함일 수 있습니다.")

    except Exception as e:
        print(f"  > 실패: 설정 값 전송/수신 중 오류가 발생했습니다.")
        print(f"    오류 메시지: {e}")

    # --- 5단계: 통신 모드 전환 및 종료 ---
    finally:
        print("\n[5/5] 진단을 종료하고 자원을 정리합니다...")
        GPIO.output(M0, GPIO.LOW)
        GPIO.output(M1, GPIO.LOW)
        if ser and ser.is_open:
            ser.close()
            print("  > 시리얼 포트를 닫았습니다.")
        GPIO.cleanup()
        print("  > GPIO 설정을 초기화했습니다.")
        print("\n--- 진단 완료 ---")

if __name__ == "__main__":
    main()
