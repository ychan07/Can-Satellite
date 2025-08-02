import pandas as pd
import numpy as np
import os
import random
import tkinter as tk
from tkinter import filedialog

# --- 오차 생성 함수 (data_augmenter.py와 동일) ---

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

# --- 메인 처리 함수 ---

def augment_single_file(input_path, output_path, num_augmentations=5):
    """단일 원본 파일을 읽어 5개의 증강 열을 추가하고 저장합니다."""
    print(f"Reading original file: {input_path}")
    try:
        original_df = pd.read_csv(input_path, sep=r'\s+', header=None, comment='#')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if original_df.shape[1] < 3:
        print(f"Error: Input file must have at least 3 columns (velocity, flux, prebaselineflux).")
        return

    power_data_to_augment = original_df.iloc[:, 1] # 2번째 열 'flux'를 증강 대상으로 선택
    output_df = original_df.copy()

    print("Generating 5 augmented data columns...")
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

    try:
        output_df.to_csv(output_path, sep=' ', header=False, index=False)
        print(f"\nSuccessfully created test file!\nSaved to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")

# --- GUI 및 실행 로직 ---

def main():
    root = tk.Tk()
    root.withdraw()

    # 1. 입력 파일 선택
    print("파일 선택창을 엽니다... 오차를 적용할 원본 NRAO 데이터 파일을 선택하세요.")
    input_file = filedialog.askopenfilename(
        title="Select an Original NRAO CSV File",
        initialdir=os.path.join(os.getcwd(), "predata"),
        filetypes=(
            ("CSV Files", "*.csv"),
            ("All files", "*.*")
        )
    )

    if not input_file:
        print("파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    # 2. 출력 파일 경로 지정
    print("저장 위치 선택창을 엽니다... 생성될 테스트 파일을 저장할 위치와 이름을 지정하세요.")
    output_file = filedialog.asksaveasfilename(
        title="Save Augmented Test File As...",
        initialdir=os.getcwd(),
        initialfile=f"test_{os.path.basename(input_file)}",
        defaultextension=".csv",
        filetypes=(
            ("CSV Files", "*.csv"),
            ("All files", "*.*")
        )
    )

    if not output_file:
        print("저장 위치를 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    # 3. 메인 기능 실행
    augment_single_file(input_file, output_file)

if __name__ == '__main__':
    print("--- Single Test File Creator ---")
    main()
