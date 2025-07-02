import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def generate_synthetic_hi_spectrum(
    center_freq_mhz=1420.0,
    bandwidth_mhz=1.0,
    num_points=2048,
    line_center_mhz=1420.3,
    line_width_mhz=0.02,
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

    # CSV 저장 (주파수, 파워)
    df = pd.DataFrame({0: freqs, 1: spectrum})
    df.to_csv(output_file, index=False, header=False)
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
