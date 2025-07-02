import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로가 필요합니다.")
        return

    df = pd.read_csv(file_path)
    y = df['intensity'].values
    N = len(y)
    Y = np.abs(np.fft.fft(y - np.mean(y)))
    freq = np.fft.fftfreq(N, d=5.0)  # d=샘플링 간격, 여기선 5 km/s 기준

    plt.plot(freq[:N//2], Y[:N//2])
    plt.title("FFT of Spectrum")
    plt.xlabel("Frequency (1/km/s)")
    plt.ylabel("Amplitude")
    plt.grid()
    plt.show()
