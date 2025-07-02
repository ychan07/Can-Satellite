import pandas as pd
import numpy as np
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    # 공백으로 분리된 데이터 읽기 (헤더 없음)
    df = pd.read_csv(file_path, delim_whitespace=True, names=['velocity', 'intensity'])

    df = df.sort_values(by='velocity')
    min_v = df['velocity'].min()
    max_v = df['velocity'].max()
    new_velocity = np.arange(min_v, max_v, 5)  # 5 km/s 간격
    new_intensity = np.interp(new_velocity, df['velocity'], df['intensity'])

    new_df = pd.DataFrame({'velocity': new_velocity, 'intensity': new_intensity})
    output = file_path.replace(".csv", "_resampled.csv")
    
    # 다음 모듈 호환성을 위해 헤더 없이 공백으로 분리하여 저장
    new_df.to_csv(output, index=False, header=False, sep=' ')
    print(f"리샘플링 완료: {output}")

if __name__ == "__main__":
    main()
