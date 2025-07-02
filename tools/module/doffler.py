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
    
    # 예시: 도플러 보정 인자 -10 km/s
    df['velocity'] = df['velocity'] - 10  
    output = file_path.replace(".csv", "_corrected.csv")
    df.to_csv(output, index=False, header=False, sep=' ')
    print(f"도플러 보정 완료: {output}")
