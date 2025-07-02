import pandas as pd
import sys

# 기준 주파수 (21cm 수소선)
REST_FREQ = 1420.40575177  # MHz

def freq_to_velocity(freq):
    c = 299792.458  # km/s
    return c * (REST_FREQ - freq) / REST_FREQ

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    df = pd.read_csv(file_path)
    if 'frequency' not in df.columns:
        print("입력 파일에 'frequency' 열이 없습니다.")
        return

    df['velocity'] = freq_to_velocity(df['frequency'])
    df = df[['velocity', 'intensity']]
    output = file_path.replace(".csv", "_vel.csv")
    df.to_csv(output, index=False)
    print(f"축 변환 완료: {output}")

if __name__ == "__main__":
    main()
