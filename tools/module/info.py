import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로가 필요합니다.")
        return

    df = pd.read_csv(file_path)
    print("열 이름:", df.columns.tolist())
    print("행 수:", len(df))
    print("샘플 데이터:\n", df.head())
