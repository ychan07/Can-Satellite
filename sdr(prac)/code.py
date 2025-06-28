import time
import numpy as np
from scipy.fft import fft, fftshift
from rtlsdr import RtlSdr
import os # 파일 경로 및 디렉토리 관리를 위해 os 모듈 임포트

# matplotlib은 SSH 환경에서 바로 그림을 그릴 수 없으므로,
# 그래프 파일 저장 용도로만 사용하거나, 필요 없으면 주석 처리하여 설치 부담 줄이기
# import matplotlib.pyplot as plt

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
# 이 경로는 라즈베리파이 SD 카드 내의 특정 폴더를 의미합니다.
# 직접 생성하거나, 스크립트 실행 시 자동으로 생성하도록 할 수 있습니다.
# 예: '/home/pi/sdr_data'
DATA_SAVE_DIR = '/home/pi/sdr_data'

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
        
        # 진행 상황 표시
        if (i + 1) % (NUM_AVERAGES // 10) == 0:
            print(f"  {i+1}/{NUM_AVERAGES} 완료...")

    # 평균 스펙트럼 계산
    avg_spectrum = total_spectrum / NUM_AVERAGES
    
    # 주파수 축 생성
    freqs = np.fft.fftfreq(NUM_SAMPLES, d=1/SAMPLE_RATE)
    freqs = fftshift(freqs) + CENTER_FREQ # 중심 주파수 보정

    return freqs, avg_spectrum

# --- 메인 루프 ---
try:
    while True:
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

        # 2. (선택 사항) PNG 이미지 파일로 스펙트럼 그래프 저장
        # matplotlib이 설치되어 있어야 합니다. (SSH 환경에서 plt.show()는 작동 안함)
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

        print("-" * 30)
        time.sleep(10) # 다음 관측까지 대기 (조절 가능)

except KeyboardInterrupt:
    print("\nSDR 관측 중단.")
except Exception as e:
    print(f"예상치 못한 에러 발생: {e}")
finally:
    sdr.close() # SDR 동글 닫기
    print("SDR 프로그램 종료.")