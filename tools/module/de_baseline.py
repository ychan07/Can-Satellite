import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    df = pd.read_csv(file_path)
    if 'intensity' not in df.columns:
        print("intensity 열이 없습니다.")
        return

    baseline = df['intensity'].mean()
    df['intensity'] = df['intensity'] - baseline
    output = file_path.replace(".csv", "_debaselined.csv")
    df.to_csv(output, index=False)
    print(f"베이스라인 제거 완료: {output}")

if __name__ == "__main__":
    main()
