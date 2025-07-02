import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로가 필요합니다.")
        return

    df = pd.read_csv(file_path)
    # 예시: 도플러 보정 인자 -10 km/s
    df['velocity'] = df['velocity'] - 10  
    output = file_path.replace(".csv", "_corrected.csv")
    df.to_csv(output, index=False)
    print(f"도플러 보정 완료: {output}")
