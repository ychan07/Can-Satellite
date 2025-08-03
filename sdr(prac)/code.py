import time
import numpy as np
from scipy.fft import fft, fftshift
from rtlsdr import RtlSdr
import os
import sys

# --- SDR Configuration ---
CENTER_FREQ = 1420.405751e6  # 21cm neutral hydrogen line frequency (Hz)
SAMPLE_RATE = 2.048e6       # Sample rate (SPS)
NUM_SAMPLES = 2**16         # Number of samples for each FFT
NUM_AVERAGES = 100          # Number of spectra to average for each save

# --- Data Storage ---
# Get the absolute path of the script's directory
sdr_prac_dir = os.path.dirname(os.path.abspath(__file__))
# Go one level up to the project root
project_root = os.path.dirname(sdr_prac_dir)
# Define the data save directory relative to the project root
DATA_SAVE_DIR = os.path.join(project_root, 'sdr_data')


def main():
    """Main function to run the SDR measurement loop."""
    
    # --- SDR Initialization ---
    try:
        sdr = RtlSdr()
        sdr.sample_rate = SAMPLE_RATE
        sdr.center_freq = CENTER_FREQ
        sdr.gain = 15  # Manual gain in dB. May need tuning.
        print(f"SDR Initialized: Freq={sdr.center_freq/1e6:.3f} MHz, Rate={sdr.sample_rate/1e6:.3f} MSps, Gain={sdr.gain:.1f} dB")
    except Exception as e:
        print(f"Error initializing SDR: {e}")
        sys.exit(1)

    # --- Data Directory Setup ---
    if not os.path.exists(DATA_SAVE_DIR):
        os.makedirs(DATA_SAVE_DIR)
        print(f"Created data directory: {DATA_SAVE_DIR}")

    # --- Main Measurement Loop ---
    print("Starting continuous SDR measurement...")
    total_spectrum = np.zeros(NUM_SAMPLES)
    measurement_count = 0

    try:
        while True:
            # Capture I/Q samples
            samples = sdr.read_samples(NUM_SAMPLES)
            
            # Perform FFT and calculate power spectrum
            spectrum = fftshift(fft(samples))
            power_spectrum = 10 * np.log10(np.abs(spectrum)**2 + 1e-12) # dB scale
            
            total_spectrum += power_spectrum
            measurement_count += 1

            # Average and save data periodically
            if measurement_count >= NUM_AVERAGES:
                avg_spectrum = total_spectrum / measurement_count
                
                # Generate frequency axis
                freqs = np.fft.fftfreq(NUM_SAMPLES, d=1/SAMPLE_RATE)
                freqs = fftshift(freqs) + CENTER_FREQ

                # Save the averaged spectrum to a CSV file
                timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
                csv_filename = os.path.join(DATA_SAVE_DIR, f"spectrum_{timestamp}.csv")
                np.savetxt(csv_filename, np.column_stack([freqs, avg_spectrum]), 
                           delimiter=',', header='Frequency_Hz,Power_dB', comments='')
                print(f"Saved averaged spectrum to {os.path.basename(csv_filename)}")

                # Reset for the next averaging period
                total_spectrum = np.zeros(NUM_SAMPLES)
                measurement_count = 0

    except KeyboardInterrupt:
        print("\nMeasurement loop interrupted by user (e.g., from main_pipeline).")
    except Exception as e:
        print(f"An error occurred during measurement: {e}")
    finally:
        sdr.close()
        print("SDR closed.")

if __name__ == "__main__":
    main()
