import pandas as pd
import matplotlib.pyplot as plt
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]

    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    # MaNGA 파일 형식에 맞게 주석(#)을 무시하고, 공백으로 분리된 데이터를 읽음
    df = pd.read_csv(file_path, comment='#', delim_whitespace=True, names=['velocity', 'intensity', 'pre_baseline_intensity'])
    plt.plot(df['velocity'], df['intensity'])
    plt.xlabel("Velocity (km/s)")
    plt.ylabel("Intensity")
    plt.title("1D Hydrogen Line Spectrum")
    plt.grid()
    plt.show()

if __name__ == "__main__":
    main()
