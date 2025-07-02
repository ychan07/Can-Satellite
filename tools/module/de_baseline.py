import pandas as pd
import sys

def main(file_path=None):
    if file_path is None and len(sys.argv) > 1:
        file_path = sys.argv[1]
    if not file_path:
        print("파일 경로를 입력하세요.")
        return

    # 공백으로 분리된 데이터 읽기 (헤더 없음)
    df = pd.read_csv(file_path, delim_whitespace=True, names=['velocity', 'intensity'])

    baseline = df['intensity'].mean()
    df['intensity'] = df['intensity'] - baseline
    
    output = file_path.replace(".csv", "_debaselined.csv")
    
    # 다음 모듈 호환성을 위해 헤더 없이 공백으로 분리하여 저장
    df.to_csv(output, index=False, header=False, sep=' ')
    print(f"베이스라인 제거 완료: {output}")

if __name__ == "__main__":
    main()
