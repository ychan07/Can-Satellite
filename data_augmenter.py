

import pandas as pd
import numpy as np
import os
import glob
import random
from tqdm import tqdm

def add_linear_error(data_series, max_slope=0.05, max_intercept=0.1):
    num_points = len(data_series)
    slope = random.uniform(-max_slope, max_slope)
    intercept = random.uniform(-max_intercept, max_intercept)
    linear_error = slope * np.arange(num_points) + intercept
    return data_series + linear_error

def add_peak_error(data_series, num_peaks=1, max_height=0.5, max_width=5.0):
    power_data = data_series.copy().values
    num_points = len(power_data)
    for _ in range(num_peaks):
        peak_position = random.randint(0, num_points - 1)
        peak_height = random.uniform(0.1, max_height)
        peak_width = random.uniform(1.0, max_width)
        x = np.arange(num_points)
        peak = peak_height * np.exp(-((x - peak_position) ** 2) / (2 * peak_width ** 2))
        power_data += peak
    return pd.Series(power_data, index=data_series.index)

def add_random_noise(data_series, noise_level=0.02):
    noise = np.random.normal(0, noise_level, len(data_series))
    return data_series + noise

def generate_augmented_data_columns(input_paths, output_path, num_augmentations=5):
    """
    여러 입력 경로의 모든 CSV 파일에 대해 오차를 추가하여 새로운 데이터셋을 생성합니다.
    파일명 중복을 피하기 위해 부모 폴더명을 파일명에 추가합니다.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created output directory: {output_path}")

    all_csv_files = []
    for path in input_paths:
        all_csv_files.extend(glob.glob(os.path.join(path, '*.csv')))

    if not all_csv_files:
        print(f"경고: {input_paths} 에서 CSV 파일을 찾을 수 없습니다.")
        return

    print(f"총 {len(all_csv_files)}개의 CSV 파일을 찾았습니다. 데이터 증강을 시작합니다.")

    for file_path in tqdm(all_csv_files, desc="Augmenting files"):
        try:
            original_df = pd.read_csv(file_path, delim_whitespace=True, header=None, comment='#')
            if original_df.shape[1] < 2:
                continue
            power_data_to_augment = original_df.iloc[:, 1]
        except Exception as e:
            continue

        parent_dir_name = os.path.basename(os.path.dirname(file_path))
        original_filename = os.path.basename(file_path)
        unique_filename = f"{parent_dir_name}_{original_filename}"
        
        output_df = original_df.copy()

        for i in range(num_augmentations):
            augmented_power = power_data_to_augment.copy()
            error_functions = [add_linear_error, add_peak_error, add_random_noise]
            num_errors_to_apply = random.randint(1, len(error_functions))
            chosen_errors = random.sample(error_functions, num_errors_to_apply)

            for error_func in chosen_errors:
                if error_func == add_peak_error:
                    augmented_power = error_func(augmented_power, num_peaks=random.randint(1, 3))
                else:
                    augmented_power = error_func(augmented_power)
            
            output_df[f'augmented_{i+1}'] = augmented_power

        output_file_path = os.path.join(output_path, unique_filename)
        output_df.to_csv(output_file_path, sep=' ', header=False, index=False)

    print(f"\n데이터 증강 완료. 결과가 '{output_path}'에 저장되었습니다.")

if __name__ == '__main__':
    # --- 설정 (사용자 수정 필요) ---

    # 1. 원본 CSV 파일이 있는 폴더들의 경로를 리스트로 지정합니다.
    # 예: 
    # input_dirs = [
    #     r'C:\Users\Me\Desktop\mangaHI_csv_files',
    #     r'C:\Users\Me\Desktop\mangaHI_csv_files_DR3'
    # ]
    input_dirs = [
        r'path/to/your/first_csv_folder',
        r'path/to/your/second_csv_folder'
    ]

    # 2. 생성된 파일을 저장할 단일 디렉토리 경로
    output_dir = r'path/to/your/single_output_folder'
    
    # --- 스크립트 실행 ---
    print("스크립트 사용법:")
    print("1. input_dirs 변수에 원본 CSV 폴더들의 경로를 리스트 형태로 모두 추가하세요.")
    print("2. output_dir 변수에 생성된 파일을 저장할 하나의 폴더 경로를 지정하세요.")
    print("3. 터미널에서 'python data_augmenter.py' 명령을 실행하세요.")

    if output_dir == r'path/to/your/single_output_folder':
         print("\n!!! 중요 !!!")
         print("스크립트 하단의 'input_dirs'와 'output_dir' 변수를 실제 경로로 수정해주세요.")
    else:
        generate_augmented_data_columns(input_dirs, output_dir)

