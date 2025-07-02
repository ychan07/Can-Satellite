import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def generate_synthetic_hi_spectrum(
    center_freq_mhz=1418.0,  # 중심 주파수 조정
    bandwidth_mhz=10.0,      # 대역폭을 10배로 늘림
    num_points=2048,
    line_center_mhz=1416.5,  # 새로운 대역폭에 맞게 라인 위치 조정
    line_width_mhz=0.2,      # 라인 폭 조정
    line_depth=0.005,
    noise_std=0.001,
    output_file="fake_sdr_data.csv",
    plot=True
):
    # 주파수 축 생성
    freqs = np.linspace(center_freq_mhz - bandwidth_mhz / 2,
                        center_freq_mhz + bandwidth_mhz / 2,
                        num_points)

    # 평탄한 스펙트럼 (단위: Jy)
    spectrum = np.ones_like(freqs) * 1.0

    # 인공 HI absorption line 추가 (가우시안 dip)
    line = line_depth * np.exp(-0.5 * ((freqs - line_center_mhz) / line_width_mhz) ** 2)
    spectrum -= line

    # 가우시안 노이즈 추가
    noise = np.random.normal(0, noise_std, size=num_points)
    spectrum += noise

    # axishifter.py 호환성을 위해 3열 데이터프레임 생성
    # 열: frequency, intensity, pre_baseline_intensity (더미)
    df = pd.DataFrame({
        'frequency': freqs,
        'intensity': spectrum,
        'pre_baseline_intensity': spectrum  # 더미 데이터
    })

    # MaNGA 형식에 맞게 주석 헤더와 함께 공백으로 분리된 파일로 저장
    with open(output_file, 'w') as f:
        f.write("# freq intensity pre_baseline_intensity\n")  # 헤더
    df.to_csv(output_file, index=False, header=False, sep=' ', mode='a')
    print(f"[✓] 생성 완료: {output_file}")

    # 시각화
    if plot:
        plt.plot(freqs, spectrum)
        plt.title("Synthetic HI Spectrum (Raw SDR Style)")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Signal (Jy)")
        plt.grid(True)
        plt.show()

if __name__ == "__main__":
    generate_synthetic_hi_spectrum()
