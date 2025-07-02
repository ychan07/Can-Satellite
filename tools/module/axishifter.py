import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    # MaNGA 파일 형식에 맞게 주석(#)을 무시하고, 공백으로 분리된 데이터를 읽음
    # 열 이름: freq, intensity, pre_baseline_intensity
    df = pd.read_csv(file_path, comment='#', delim_whitespace=True, names=['frequency', 'intensity', 'pre_baseline_intensity'])

    # 물리 상수 정의
    C_KMS = 299792.458  # 빛의 속도 (km/s)
    HI_REST_FREQ_MHZ = 1420.40575  # 중성수소 정지 주파수 (MHz)

    # 주파수(MHz)를 속도(km/s)로 변환
    # 비상대론적 도플러 공식: v = c * (f_rest - f_obs) / f_rest
    df['velocity'] = C_KMS * (HI_REST_FREQ_MHZ - df['frequency']) / HI_REST_FREQ_MHZ
    
    # 필요한 열(velocity, intensity)만 선택
    df = df[['velocity', 'intensity']]
    
    output = file_path.replace(".csv", "_vel.csv")
    
    # 다음 모듈에서 쉽게 읽을 수 있도록 헤더 없이, 공백으로 분리된 파일로 저장
    df.to_csv(output, index=False, header=False, sep=' ')
    print(f"파일 정리 및 변환 완료: {output}")

if __name__ == "__main__":
    main()
