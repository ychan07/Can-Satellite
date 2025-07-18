# lora_comms.py
# LoRa 통신 기능을 모듈화한 파일입니다.
# 모든 LoRa 설정 및 메시지 대상 파라미터가 이 모듈 내부에 고정됩니다.

import sx126x # 제조사에서 제공하는 sx126x 라이브러리 필요
import time
import sys

class LoRaComms:
    """
    SX126x 기반 LoRa 모듈과의 UART 통신을 위한 클래스입니다.
    이 클래스는 LoRa 모듈을 초기화하고 메시지 송수신 기능을 제공합니다.
    모든 LoRa 설정 파라미터는 이 클래스 내부에 고정됩니다.
    """
    
    # --- LoRa 모듈 자체의 고정 설정 ---
    # 캔위성 및 지상국 모듈의 시리얼 포트, 주파수, 주소, 전력, RSSI, Air Speed, 릴레이 기능
    # 이 값들은 LoRa 모듈의 실제 설정 및 통신하려는 상대방과 일치해야 합니다.
    _SERIAL_PORT = "/dev/ttyS0"  # Raspberry Pi의 시리얼 포트
    _FREQ = 433                  # LoRa 통신 주파수 (MHz)
    _ADDR = 0                    # LoRa 모듈 주소 (0-65535)
    _POWER = 22                  # 전송 출력 (dBm)
    _RSSI = True                 # 수신 시 RSSI 값 출력 여부
    _AIR_SPEED = 2400            # 공중 전송 속도 (bps)
    _RELAY = False               # 릴레이 기능 활성화 여부

    # --- 메시지 전송 시 사용할 고정 대상 파라미터 ---
    # 캔위성(송신기)이 지상국(수신기)으로 보낼 때의 대상 주소와 주파수입니다.
    # 지상국 수신기의 _ADDR 및 _FREQ와 일치해야 합니다.
    _TARGET_ADDRESS = 0          # 메시지를 보낼 대상 LoRa 모듈의 주소
    _TARGET_FREQUENCY = 433      # 메시지를 보낼 대상 주파수 (MHz)

    def __init__(self):
        """
        LoRa 통신 모듈을 초기화합니다.
        모든 설정은 클래스 내부에 고정된 값을 사용합니다.
        """
        self.node = None
        try:
            self.node = sx126x.sx126x(
                serial_num=self._SERIAL_PORT,
                freq=self._FREQ,
                addr=self._ADDR,
                power=self._POWER,
                rssi=self._RSSI,
                air_speed=self._AIR_SPEED,
                relay=self._RELAY
            )
            time.sleep(1) # 모듈 초기화 대기
            print("LoRaComms: LoRa 모듈 초기화 완료.")
        except Exception as e:
            print(f"LoRaComms: LoRa 모듈 초기화 실패: {e}")
            self.node = None # 초기화 실패 시 node를 None으로 설정

    def send_message(self, message_payload):
        """
        고정된 대상 주소와 주파수로 LoRa 메시지를 전송합니다.

        Args:
            message_payload (str): 전송할 텍스트 메시지.

        Returns:
            bool: 메시지 전송 성공 여부.
        """
        if not self.node:
            print("LoRaComms: LoRa 모듈이 초기화되지 않았습니다. 메시지를 보낼 수 없습니다.")
            return False

        try:
            # 고정된 대상 주소와 주파수 사용
            target_address = self._TARGET_ADDRESS
            target_frequency = self._TARGET_FREQUENCY

            # 주파수 오프셋 계산 (sx126x 라이브러리 내부 로직에 따름)
            offset_frequence = target_frequency - (850 if target_frequency > 850 else 410)

            # 전송 데이터 패킷 구성 (제조사 라이브러리 규격에 따름)
            # [수신 노드 고위 8비트 주소] + [수신 노드 저위 8비트 주소] + [수신 노드 주파수 오프셋] +
            # [자신 노드 고위 8비트 주소] + [자신 노드 저위 8비트 주소] + [자신 노드 주파수 오프셋] + 메시지 페이로드
            data = (
                bytes([target_address >> 8]) + bytes([target_address & 0xff]) +
                bytes([offset_frequence]) +
                bytes([self.node.addr >> 8]) + bytes([self.node.addr & 0xff]) +
                bytes([self.node.offset_freq]) +
                message_payload.encode('utf-8') # 메시지를 UTF-8 바이트로 인코딩
            )

            self.node.send(data)
            print(f"LoRaComms: 메시지 전송 완료: '{message_payload}' (대상: 주소 {target_address}, 주파수 {target_frequency}MHz)")
            return True
        except Exception as e:
            print(f"LoRaComms: 메시지 전송 중 오류 발생: {e}")
            return False

    def receive_messages(self):
        """
        LoRa 모듈로부터 메시지를 수신 대기하고 처리합니다.
        (sx126x 라이브러리의 receive() 함수가 수신된 데이터를 내부적으로 처리하고 출력합니다.)
        """
        if not self.node:
            print("LoRaComms: LoRa 모듈이 초기화되지 않았습니다. 메시지를 수신할 수 없습니다.")
            return

        # sx126x.receive() 함수는 수신된 메시지를 내부적으로 처리하고,
        # RSSI가 True로 설정되어 있으면 RSSI 값을 함께 출력합니다.
        self.node.receive()
        # CPU 사용률을 줄이기 위한 짧은 대기
        time.sleep(0.01)

    def cleanup(self):
        """
        LoRa 모듈과의 통신을 종료하고 자원을 정리합니다.
        (sx126x 라이브러리가 시리얼 포트 정리를 내부적으로 처리한다고 가정합니다.)
        """
        if self.node:
            print("LoRaComms: LoRa 모듈 정리 완료.")
        # termios 설정은 이 모듈이 아닌 메인 애플리케이션에서 관리합니다.

