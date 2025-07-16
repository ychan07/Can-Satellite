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

    # Read metadata from comments
    sample_rate_hz = None
    center_freq_hz = None
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('# sample_rate_hz:'):
                sample_rate_hz = float(line.split(':')[1].strip())
            elif line.startswith('# center_freq_hz:'):
                center_freq_hz = float(line.split(':')[1].strip())
            elif not line.startswith('#'): # Stop reading comments after header
                break

    if sample_rate_hz is None or center_freq_hz is None:
        print("Error: Missing sample_rate_hz or center_freq_hz in file header.")
        return

    # Read I/Q data
    df = pd.read_csv(file_path, comment='#', delim_whitespace=True, names=['I', 'Q'])
    
    # Combine I and Q into complex signal
    complex_signal = df['I'].values + 1j * df['Q'].values

    # Perform FFT
    N = len(complex_signal)
    yf = np.fft.fft(complex_signal)
    xf = np.fft.fftfreq(N, 1 / sample_rate_hz)

    # Shift zero frequency to center for plotting
    xf_shifted = np.fft.fftshift(xf)
    yf_shifted = np.fft.fftshift(yf)

    # Convert frequency to MHz for plotting
    freq_mhz = (xf_shifted + center_freq_hz) / 1e6

    # Calculate power spectrum in dB
    power_spectrum_db = 10 * np.log10(np.abs(yf_shifted)**2 / N)

    # Debugging prints
    print(f"Max Power (dB): {np.max(power_spectrum_db)}")
    print(f"Min Power (dB): {np.min(power_spectrum_db)}")
    print(f"Mean Power (dB): {np.mean(power_spectrum_db)}")

    # Plotting magnitude spectrum
    plt.figure(figsize=(10, 6))
    plt.plot(freq_mhz, power_spectrum_db)
    plt.title("Frequency Spectrum of Raw SDR Data (dB)")
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Power (dB)")
    
    # Adjust X-axis limit to focus on the peak
    plt.xlim(center_freq_hz/1e6 - sample_rate_hz/2e6, center_freq_hz/1e6 + sample_rate_hz/2e6)
    
    # Set Y-limit dynamically based on power spectrum
    plt.ylim(np.min(power_spectrum_db) - 5, np.max(power_spectrum_db) + 5)

    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()