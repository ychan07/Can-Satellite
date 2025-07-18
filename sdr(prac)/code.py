# sdr_observation_with_lora.py
# SDR 관측 데이터를 수집하고 처리하며, LoRa를 통해 진행 상황을 전송하는 코드입니다.

import time
import numpy as np
from scipy.fft import fft, fftshift
from rtlsdr import RtlSdr
import os # 파일 경로 및 디렉토리 관리를 위해 os 모듈 임포트

<<<<<<< HEAD
# LoRa 통신 모듈 임포트
# 이 파일과 같은 디렉토리에 lora_comms.py와 sx126x.py가 있어야 합니다.
from LoRa_module import LoRaComms 


# --- LoRa 모듈 설정 ---
# LoRaComms 객체를 생성합니다. 모든 LoRa 통신 파라미터는 lora_comms.py 내부에 고정되어 있습니다.
lora_handler = LoRaComms()

=======
>>>>>>> a4d54c02ae7d8760bbf8bfaa488406fff722495e
# --- SDR 설정 ---
# 21cm 중성수소선 주파수 (Hz)
CENTER_FREQ = 1420.405751e6 # 1420.405751 MHz

# 샘플링 속도 (SPS, Samples Per Second)
SAMPLE_RATE = 2.048e6 # 2.048 MSps

# 수집할 샘플 개수
NUM_SAMPLES = 2**16 # 65536 샘플 (FFT 해상도 결정)

# 수집할 스펙트럼 평균 횟수 (잡음 감소 목적)
NUM_AVERAGES = 100 # 100회 평균 (신호 대 잡음비 향상)

# 데이터 저장 디렉토리 설정
# 이 부분을 현재 사용자 (firsttoken)의 홈 디렉토리로 변경합니다.
DATA_SAVE_DIR = '/home/firsttoken/sdr_data'

# --- SDR 초기화 ---
sdr = RtlSdr()

# SDR 파라미터 설정
sdr.sample_rate = SAMPLE_RATE
sdr.center_freq = CENTER_FREQ
sdr.gain = 49.6 # 수동 게인 (dB). 최적 게인 찾기 위해 테스트 필요. (LNA 사용 시 조절)

print(f"SDR 설정: 주파수={sdr.center_freq/1e6:.3f} MHz, 샘플링 속도={sdr.sample_rate/1e6:.3f} MSps, 게인={sdr.gain:.1f} dB")
print(f"데이터는 '{DATA_SAVE_DIR}'에 저장됩니다.")

# 데이터 저장 디렉토리 확인 및 생성
if not os.path.exists(DATA_SAVE_DIR):
    os.makedirs(DATA_SAVE_DIR)
    print(f"데이터 저장 디렉토리 '{DATA_SAVE_DIR}'를 생성했습니다.")


# --- 데이터 수집 및 처리 함수 ---
def capture_and_process_spectrum():
    print(f"샘플 {NUM_SAMPLES}개씩 {NUM_AVERAGES}회 수집 및 평균 중...")
    
    total_spectrum = np.zeros(NUM_SAMPLES)

    for i in range(NUM_AVERAGES):
        # I/Q 데이터 수집 (복소수 배열)
        samples = sdr.read_samples(NUM_SAMPLES)
        
        # FFT 수행 (시간 영역 -> 주파수 영역)
        spectrum = fftshift(fft(samples))
        
        # 파워 스펙트럼 계산 (크기의 제곱, dB 스케일로 변환)
        power_spectrum = 10 * np.log10(np.abs(spectrum)**2 + 1e-12) # 0 방지
        
        total_spectrum += power_spectrum
        
        # 진행 상황 표시 및 LoRa 전송
        if (i + 1) % (NUM_AVERAGES // 10) == 0: # 10% 진행될 때마다 출력 및 전송
            progress_message = f"SDR Progress: {i+1}/{NUM_AVERAGES} completed."
            print(f"  {progress_message}")
            
            # LoRa 모듈이 성공적으로 초기화되었다면 메시지 전송
            if lora_handler.node:
                lora_handler.send_message(progress_message)
            else:
                print("LoRa 모듈이 초기화되지 않아 진행 상황을 전송할 수 없습니다.")

    # 평균 스펙트럼 계산
    avg_spectrum = total_spectrum / NUM_AVERAGES
    
    # 주파수 축 생성
    freqs = np.fft.fftfreq(NUM_SAMPLES, d=1/SAMPLE_RATE)
    freqs = fftshift(freqs) + CENTER_FREQ # 중심 주파수 보정

    return freqs, avg_spectrum

<<<<<<< HEAD
# --- 메인 실행 블록 ---
try:
    print("SDR 관측 프로그램 시작.")
    
    # LoRa 모듈 초기화 실패 시, SDR 관측은 계속 진행할지 여부를 결정할 수 있습니다.
    # 여기서는 LoRa 초기화 실패 시에도 SDR 관측은 시도하도록 합니다.
    if not lora_handler.node:
        print("경고: LoRa 모듈 초기화에 실패했습니다. SDR 진행 상황을 전송할 수 없습니다.")

    start_time = time.time()
    freqs, power_spectrum_db = capture_and_process_spectrum()
    end_time = time.time()
    
    print(f"데이터 수집 및 처리 시간: {end_time - start_time:.2f} 초")

    # --- 데이터 저장 ---
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime()) # UTC 시간 사용 권장
    
    # 1. CSV 파일로 스펙트럼 데이터 저장
    csv_filename = os.path.join(DATA_SAVE_DIR, f"spectrum_data_{timestamp}.csv")
    np.savetxt(csv_filename, np.column_stack([freqs, power_spectrum_db]), 
               delimiter=',', header='Frequency_Hz,Power_dB', comments='')
    print(f"스펙트럼 데이터 '{csv_filename}'에 저장 완료.")

    # SDR 관측 완료 메시지 LoRa 전송
    if lora_handler.node:
        lora_handler.send_message(f"SDR Observation Completed. Data saved to {os.path.basename(csv_filename)}")
    
    try:
        import matplotlib.pyplot as plt
        png_filename = os.path.join(DATA_SAVE_DIR, f"spectrum_plot_{timestamp}.png")
        plt.figure(figsize=(12, 6))
        plt.plot(freqs / 1e6, power_spectrum_db) # 주파수를 MHz 단위로 표시
        plt.title(f'Average Power Spectrum @ {CENTER_FREQ/1e6:.3f} MHz (Avg: {NUM_AVERAGES})')
        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Power (dB)')
        plt.grid(True)
        # 21cm 라인 주변에 마커 표시 (도플러 효과 고려하여 범위 지정)
        plt.axvline(CENTER_FREQ/1e6, color='r', linestyle='--', label='21cm Hydrogen Line (Ideal)')
        plt.axvspan((CENTER_FREQ-200e3)/1e6, (CENTER_FREQ+200e3)/1e6, color='yellow', alpha=0.3, label='Expected Doppler Range') # 예시 범위
        plt.legend()
        plt.tight_layout()
        plt.savefig(png_filename)
        plt.close() # 플롯 창 닫기 (메모리 관리)
        print(f"스펙트럼 플롯 '{png_filename}' 저장 완료.")
    except ImportError:
        print("matplotlib이 설치되지 않아 그래프를 저장할 수 없습니다. 'pip3 install matplotlib'로 설치해주세요.")
    except Exception as e:
        print(f"그래프 저장 중 오류 발생: {e}")

=======
# --- 메인 실행 블록 (단일 측정) ---
try:
    start_time = time.time()
    freqs, power_spectrum_db = capture_and_process_spectrum()
    end_time = time.time()
    
    print(f"데이터 수집 및 처리 시간: {end_time - start_time:.2f} 초")

    # --- 데이터 저장 ---
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime()) # UTC 시간 사용 권장
    
    # 1. CSV 파일로 스펙트럼 데이터 저장
    csv_filename = os.path.join(DATA_SAVE_DIR, f"spectrum_data_{timestamp}.csv")
    np.savetxt(csv_filename, np.column_stack([freqs, power_spectrum_db]), 
               delimiter=',', header='Frequency_Hz,Power_dB', comments='')
    print(f"스펙트럼 데이터 '{csv_filename}'에 저장 완료.")

    
    try:
        import matplotlib.pyplot as plt
        png_filename = os.path.join(DATA_SAVE_DIR, f"spectrum_plot_{timestamp}.png")
        plt.figure(figsize=(12, 6))
        plt.plot(freqs / 1e6, power_spectrum_db) # 주파수를 MHz 단위로 표시
        plt.title(f'Average Power Spectrum @ {CENTER_FREQ/1e6:.3f} MHz (Avg: {NUM_AVERAGES})')
        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Power (dB)')
        plt.grid(True)
        # 21cm 라인 주변에 마커 표시 (도플러 효과 고려하여 범위 지정)
        plt.axvline(CENTER_FREQ/1e6, color='r', linestyle='--', label='21cm Hydrogen Line (Ideal)')
        plt.axvspan((CENTER_FREQ-200e3)/1e6, (CENTER_FREQ+200e3)/1e6, color='yellow', alpha=0.3, label='Expected Doppler Range') # 예시 범위
        plt.legend()
        plt.tight_layout()
        plt.savefig(png_filename)
        plt.close() # 플롯 창 닫기 (메모리 관리)
        print(f"스펙트럼 플롯 '{png_filename}' 저장 완료.")
    except ImportError:
        print("matplotlib이 설치되지 않아 그래프를 저장할 수 없습니다. 'pip3 install matplotlib'로 설치해주세요.")
    except Exception as e:
        print(f"그래프 저장 중 오류 발생: {e}")

>>>>>>> a4d54c02ae7d8760bbf8bfaa488406fff722495e
    print("-" * 30)

except Exception as e:
    print(f"예상치 못한 에러 발생: {e}")
    # 오류 발생 시 LoRa로 오류 메시지 전송
    if lora_handler.node:
        lora_handler.send_message(f"SDR Error: {e}")
finally:
    sdr.close() # SDR 동글 닫기
    print("SDR 프로그램 종료.")
    # LoRa 통신 자원 정리
    if lora_handler.node:
        lora_handler.cleanup()

