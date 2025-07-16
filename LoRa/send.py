#!/usr/bin/python
# -*- coding: UTF-8 -*-

# 이 스크립트는 UART(시리얼 통신)를 통해 LoRa 모듈을 제어합니다.
# LoRa 모듈 자체에 펌웨어가 내장되어 있어, 복잡한 LoRa 파라미터(확산 인자, 코딩률 등) 설정 없이
# UART를 통해 직접 데이터를 송수신할 수 있습니다.
# 이 코드는 LoRaWAN 프로토콜을 지원하지 않습니다.

# Raspberry Pi 3B+, 4B, Zero 시리즈에서 ㅁ사용 가능합니다.

import sys
import sx126x  # 제조사에서 제공하는 sx126x 라이브러리 필요
import time
import select
import termios
import tty
# from threading import Timer # CPU 온도 전송 기능 제거로 Timer는 더 이상 필요 없음

# 터미널 입력 설정을 위한 변수 (논블로킹 문자 입력 처리용)
old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())

# --- LoRa 모듈 초기화 ---
# serial_num: Raspberry Pi Zero, Pi3B+, Pi4B는 일반적으로 "/dev/ttyS0" 사용
# freq: 주파수 (410 ~ 493MHz 또는 850 ~ 930MHz 범위)
# addr: 모듈 주소 (0 ~ 65535). 동일 주파수에서 통신하려면 주소가 같아야 합니다.
#       단, 65535 주소는 브로드캐스트 주소로, 다른 모든 주소(0~65534)의 메시지를 수신할 수 있습니다.
# power: 전송 출력 ({10, 13, 17, 22} dBm 중 선택)
# rssi: 수신 시 RSSI 값 출력 여부 (True 또는 False)
# air_speed: 공중 전송 속도 (bps). 송수신기 동일해야 함. (예: 2400bps)
# relay: 릴레이 기능 활성화 여부 (True 또는 False)
#
# 주의: M0, M1 점퍼는 제거된 상태(HIGH)여야 합니다. (제조사 권장)

# 캔위성(송신기) 설정 예시
# 지상국과 동일한 주파수와 air_speed를 사용해야 합니다.
node = sx126x.sx126x(serial_num="/dev/ttyS0", freq=433, addr=0, power=22, rssi=True, air_speed=2400, relay=False)

# --- 메시지 연속 전송 처리 함수 ---
def send_messages_continuously(fixed_target_address, fixed_target_frequency):
    print("\n--- 연속 메시지 전송 모드 ---")
    print(f"대상: 주소 {fixed_target_address}, 주파수 {fixed_target_frequency}MHz")
    print("메시지를 입력하고 Enter를 누르세요. 종료하려면 'exit' 입력 후 Enter 또는 Esc 키.")

    while True:
        sys.stdout.write("메시지 입력: ")
        sys.stdout.flush()
        
        get_rec = ""
        # 문자 하나씩 읽어서 입력 받기 (Enter 또는 Esc까지)
        while True:
            char = sys.stdin.read(1) # 문자 하나를 읽을 때까지 블록킹
            if char == '\x0a': # Enter 키 (줄바꿈)
                break
            if char == '\x1b': # Esc 키
                print("\n연속 전송 모드 종료.")
                return # 함수 종료 (메인 루프로 돌아감)
            
            get_rec += char
            sys.stdout.write(char) # 입력된 문자 터미널에 에코
            sys.stdout.flush()

        if get_rec.lower() == "exit":
            print("\n연속 전송 모드 종료.")
            break

        message_payload = get_rec

        # 주파수 오프셋 계산 (모듈 내부 계산 방식에 따름)
        # 850MHz 이상이면 850을 기준으로, 아니면 410을 기준으로 오프셋 계산
        offset_frequence = fixed_target_frequency - (850 if fixed_target_frequency > 850 else 410)

        # 전송 메시지 형식 (제조사 라이브러리 규격에 따름)
        # [수신 노드 고위 8비트 주소] + [수신 노드 저위 8비트 주소] + [수신 노드 주파수 오프셋] +
        # [자신 노드 고위 8비트 주소] + [자신 노드 저위 8비트 주소] + [자신 노드 주파수 오프셋] + 메시지 페이로드
        data = (
            bytes([fixed_target_address >> 8]) + bytes([fixed_target_address & 0xff]) +
            bytes([offset_frequence]) +
            bytes([node.addr >> 8]) + bytes([node.addr & 0xff]) +
            bytes([node.offset_freq]) +
            message_payload.encode()
        )

        node.send(data) # LoRa 모듈로 데이터 전송
        print(f"\n메시지 전송 완료: '{message_payload}'")
        # 다음 입력을 위해 이전 입력 줄을 지울 필요 없이 새로운 프롬프트가 덮어씀

# --- 메인 루프 ---
try:
    time.sleep(1) # 모듈 초기화 대기
    print("--------------------------------------------------")
    print("Press \033[1;32mEsc\033[0m to exit the program")
    print("Press \033[1;32mi\033[0m   to start sending custom messages")
    print("--------------------------------------------------")
    
    while True:
        # 키보드 입력 감지 (논블로킹)
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            c = sys.stdin.read(1) # 단일 문자 읽기

            # Esc 키 감지 (프로그램 종료)
            if c == '\x1b':
                break
            
            # 'i' 키 감지 (메시지 전송 모드 시작)
            if c == '\x69':
                print("\n")
                print("첫 메시지 전송을 위한 '대상주소,대상주파수,메시지' 형식으로 입력하세요.")
                print("예: \033[1;32m0,433,Hello World\033[0m")
                sys.stdout.write("입력 후 Enter 키를 누르세요: ")
                sys.stdout.flush()

                initial_input = ""
                # 첫 입력 받기 (Enter까지 블록킹)
                while True:
                    char = sys.stdin.read(1)
                    if char == '\x0a': # Enter
                        break
                    initial_input += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

                try:
                    parts = initial_input.split(",")
                    if len(parts) != 3:
                        print("\n잘못된 입력 형식입니다. '주소,주파수,메시지' 형식으로 입력하세요.")
                        # 입력 줄을 지우고 커서를 원래 위치로 돌려보내기 (선택 사항)
                        sys.stdout.write('\x1b[1A\r' + ' ' * 100 + '\r\x1b[1A')
                        sys.stdout.flush()
                        continue # 메인 루프로 돌아가 다시 입력 대기
                    
                    fixed_target_address = int(parts[0])
                    fixed_target_frequency = int(parts[1])
                    first_message_payload = parts[2]

                    # 첫 메시지 전송
                    offset_frequence = fixed_target_frequency - (850 if fixed_target_frequency > 850 else 410)
                    data = (
                        bytes([fixed_target_address >> 8]) + bytes([fixed_target_address & 0xff]) +
                        bytes([offset_frequence]) +
                        bytes([node.addr >> 8]) + bytes([node.addr & 0xff]) +
                        bytes([node.offset_freq]) +
                        first_message_payload.encode()
                    )
                    node.send(data)
                    print(f"\n첫 메시지 전송 완료: '{first_message_payload}' (대상: 주소 {fixed_target_address}, 주파수 {fixed_target_frequency}MHz)")

                    # 연속 전송 모드 진입
                    send_messages_continuously(fixed_target_address, fixed_target_frequency)

                except ValueError:
                    print("\n입력 값이 올바르지 않습니다. 주소, 주파수는 숫자로 입력하세요.")
                except Exception as e:
                    print(f"\n메시지 전송 중 오류 발생: {e}")

            sys.stdout.flush() # 키 입력 처리 후 버퍼 비우기
            
        node.receive() # 키보드 입력이 없을 때도 LoRa 메시지 수신 대기
        
        time.sleep(0.1) # CPU 사용률을 줄이기 위한 짧은 대기

except Exception as e:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print(f"\n예상치 못한 오류 발생: {e}")
finally:
    # 프로그램 종료 시 터미널 설정 복구
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    print("\n프로그램이 종료되었습니다.")

