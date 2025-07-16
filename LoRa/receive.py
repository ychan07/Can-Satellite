#!/usr/bin/python
# -*- coding: UTF-8 -*-

# 이 스크립트는 UART(시리얼 통신)를 통해 LoRa 모듈을 제어합니다.
# LoRa 모듈 자체에 펌웨어가 내장되어 있어, 복잡한 LoRa 파라미터(확산 인자, 코딩률 등) 설정 없이
# UART를 통해 직접 데이터를 송수신할 수 있습니다.
# 이 코드는 LoRaWAN 프로토콜을 지원하지 않습니다.

# Raspberry Pi 3B+, 4B, Zero 시리즈에서 사용 가능합니다.
# PC/노트북에서는 GPIO 제어가 불가능하므로, 다른 설정이 필요합니다 (pc_main.py 참조).

import sys
import sx126x # 제조사에서 제공하는 sx126x 라이브러리 필요
import time
import select
import termios
import tty
from threading import Timer # 이 코드에서는 Timer를 직접 사용하지 않지만, 원본 코드에 있었으므로 남겨둠

# 터미널 입력 설정을 위한 변수 (수신기에서는 필요 없을 수 있으나, 원본 코드에 있었으므로 남겨둠)
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# Raspberry Pi CPU 온도 가져오기 함수 (수신기에서는 필요 없을 수 있으나, 원본 코드에 있었으므로 남겨둠)
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as tempFile:
            cpu_temp = tempFile.read()
        return float(cpu_temp) / 1000
    except FileNotFoundError:
        return 0.0

# --- LoRa 모듈 초기화 ---
# serial_num: Raspberry Pi Zero, Pi3B+, Pi4B는 일반적으로 "/dev/ttyS0" 사용
# freq: 주파수 (410 ~ 493MHz 또는 850 ~ 930MHz 범위)
# addr: 모듈 주소 (0 ~ 65535). 동일 주파수에서 통신하려면 주소가 같아야 합니다.
#       단, 65535 주소는 브로드캐스트 주소로, 다른 모든 주소(0~65534)의 메시지를 수신할 수 있습니다.
# power: 전송 출력 ({10, 13, 17, 22} dBm 중 선택) - 수신기에서는 전송을 하지 않으므로 중요하지 않음
# rssi: 수신 시 RSSI 값 출력 여부 (True 또는 False)
# air_speed: 공중 전송 속도 (bps). 송수신기 동일해야 함. (예: 2400bps)
# relay: 릴레이 기능 활성화 여부 (True 또는 False)
#
# 주의: M0, M1 점퍼는 제거된 상태(HIGH)여야 합니다. (제조사 권장)

# 지상국(수신기) 설정 예시
# 캔위성(송신기)과 동일한 주파수와 air_speed를 사용해야 합니다.
# 수신기는 모든 주소의 메시지를 받기 위해 addr=65535 (브로드캐스트)로 설정하거나,
# 송신기와 동일한 주소(addr=0)로 설정할 수 있습니다. 여기서는 캔위성과 동일하게 433MHz, addr=0으로 설정합니다.
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=True, air_speed=2400, relay=False)

# --- 메인 루프 ---
try:
    time.sleep(1) # 모듈 초기화 대기
    print("--------------------------------------------------")
    print("LoRa 수신기 모드 시작. 메시지 수신 대기 중...")
    print("종료하려면 Ctrl+C를 누르세요.")
    print("--------------------------------------------------")
    
    while True:
        # LoRa 모듈로부터 메시지 수신
        # sx126x 라이브러리의 receive() 함수가 메시지를 수신하고 처리합니다.
        # 이 함수는 수신된 메시지를 내부적으로 처리하고,
        # RSSI가 True로 설정되어 있으면 RSSI 값을 함께 출력합니다.
        node.receive() 
        
        # CPU 사용률을 줄이기 위해 짧은 대기
        time.sleep(0.1) 

except KeyboardInterrupt:
    print("\n프로그램 종료 요청.")
except Exception as e:
    print(f"\n예상치 못한 오류 발생: {e}")
finally:
    # 프로그램 종료 시 터미널 설정 복구
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print("\n프로그램이 종료되었습니다.")

