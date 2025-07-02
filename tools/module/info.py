import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로가 필요합니다.")
        return

    # MaNGA 파일 형식에 맞게 주석(#)을 무시하고, 공백으로 분리된 데이터를 읽음
    df = pd.read_csv(file_path, comment='#', delim_whitespace=True, names=['velocity', 'intensity', 'pre_baseline_intensity'])
    print("열 이름:", df.columns.tolist())
    print("행 수:", len(df))
    print("샘플 데이터:\n", df.head())
