import pandas as pd
import matplotlib.pyplot as plt
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]

    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    df = pd.read_csv(file_path)
    plt.plot(df['velocity'], df['intensity'])
    plt.xlabel("Velocity (km/s)")
    plt.ylabel("Intensity")
    plt.title("1D Hydrogen Line Spectrum")
    plt.grid()
    plt.show()

if __name__ == "__main__":
    main()
