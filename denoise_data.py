import torch
import pandas as pd
import numpy as np
import os
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
from train_denoiser import UNet1D # 학습 스크립트에서 모델 구조를 가져옵니다.
import tkinter as tk
from tkinter import filedialog
from scipy.signal import resample # 리샘플링을 위한 라이브러리

def denoise_spectrum_mc(model_path, input_csv_path, output_dir, mc_samples=30):
    """
    학습된 U-Net 모델과 몬테카를로 드롭아웃을 사용하여 스펙트럼의 노이즈를 제거하고,
    결과와 불확실성을 함께 저장 및 시각화합니다.
    """
    # --- 1. 설정 및 초기화 ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = UNet1D(in_channels=1, out_channels=1)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.train() # MC Dropout의 핵심: 추론 시에도 드롭아웃을 활성화

    os.makedirs(output_dir, exist_ok=True)

    # --- 2. 데이터 로드 및 전처리 ---
    try:
        # SyntaxWarning 해결: sep=r'\s+' -> sep=r'\s+'
        data = pd.read_csv(input_csv_path, sep=r'\s+', header=None, comment='#').values.astype(np.float32)
    except Exception as e:
        print(f"Error reading file {input_csv_path}: {e}")
        return

    # --- 입력 파일 형식에 따른 데이터 추출 로직 변경 ---
    if data.shape[1] == 2: # create_single_ai_input_file.py로 생성된 2열 파일
        velocity = data[:, 0]
        noisy_flux = data[:, 1]
        ground_truth_flux = None # 2열 파일에는 원본 정답이 없으므로 None
        print(f"Detected 2-column AI input file. Will only show noisy and denoised flux.")
    elif data.shape[1] >= 8: # data_augmenter.py로 생성된 8열 파일
        velocity = data[:, 0]
        ground_truth_flux = data[:, 1] # 원본 정답 (flux)
        aug_col_idx = random.randint(3, 7) # 5개의 증강 데이터 중 무작위 선택
        noisy_flux = data[:, aug_col_idx]
        print(f"Detected 8-column augmented file. Denoising column {aug_col_idx+1}.")
    else:
        print(f"Error: Input file {input_csv_path} has unsupported number of columns ({data.shape[1]}). Expected 2 or >=8.")
        return
    # --- 입력 파일 형식 로직 변경 끝 ---

    # 리샘플링 (학습 때와 동일하게 1024로 통일)
    TARGET_LENGTH = 1024 # train_denoiser.py의 TARGET_LENGTH와 동일하게 유지
    if len(noisy_flux) != TARGET_LENGTH:
        noisy_flux = resample(noisy_flux, TARGET_LENGTH)
        # ground_truth_flux가 None이 아닐 경우에만 리샘플링
        if ground_truth_flux is not None:
            ground_truth_flux = resample(ground_truth_flux, TARGET_LENGTH)
        velocity = resample(velocity, TARGET_LENGTH) # velocity도 리샘플링하여 길이 맞춤

    input_tensor = torch.from_numpy(noisy_flux.copy()).unsqueeze(0).unsqueeze(0).to(device)

    # --- 3. 몬테카를로 추론 (반복 실행) ---
    predictions = []
    with torch.no_grad():
        for _ in tqdm(range(mc_samples), desc="MC Sampling"):
            prediction = model(input_tensor)
            predictions.append(prediction.squeeze().cpu().numpy())

    predictions = np.array(predictions)
    
    # --- 4. 통계 계산 ---
    mean_prediction = np.mean(predictions, axis=0)
    std_prediction = np.std(predictions, axis=0)

    # --- 5. 결과 저장 및 시각화 ---
    base_filename = os.path.splitext(os.path.basename(input_csv_path))[0]
    output_csv_path = os.path.join(output_dir, f"denoised_mc_{base_filename}.csv")
    denoised_df = pd.DataFrame({
        'velocity': velocity,
        'denoised_flux_mean': mean_prediction,
        'uncertainty_std': std_prediction
    })
    denoised_df.to_csv(output_csv_path, sep=' ', header=False, index=False)
    print(f"Denoised data and uncertainty saved to {output_csv_path}")

    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(18, 8))
    
    # 불확실성 영역 (평균 ± 2*표준편차)을 먼저 그립니다.
    plt.fill_between(velocity, mean_prediction - 2 * std_prediction, mean_prediction + 2 * std_prediction,
                     color='#88d498', alpha=0.3, label='Uncertainty (±2 std)')

    # 원본 정답 플롯 (ground_truth_flux가 있을 때만 그림)
    if ground_truth_flux is not None:
        plt.plot(velocity, ground_truth_flux, label='Ground Truth (Original Flux)', color='#007ACC', linewidth=1.5, alpha=0.8)
    
    plt.plot(velocity, noisy_flux, label=f'Noisy Input', color='#FF5733', linestyle='--', alpha=0.6)
    plt.plot(velocity, mean_prediction, label='Denoised Output (Mean)', color='#006400', linewidth=2.5)
    
    plt.title(f'Monte Carlo Dropout Denoising Result\n(File: {os.path.basename(input_csv_path)})', fontsize=16)
    plt.xlabel("Velocity (km/s)", fontsize=12)
    plt.ylabel("Flux", fontsize=12)
    plt.legend(fontsize=10)
    plt.margins(x=0.02, y=0.05)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    output_png_path = os.path.join(output_dir, f"denoised_mc_{base_filename}.png")
    plt.savefig(output_png_path, dpi=150, bbox_inches='tight')
    print(f"Comparison graph saved to {output_png_path}")
    plt.close()

def main():
    root = tk.Tk()
    root.withdraw()

    print("파일 선택창을 엽니다... 추론할 증강 데이터 파일을 선택해주세요.")
    input_csv_file = filedialog.askopenfilename(
        title="Select an Augmented CSV File for MC Denoising",
        initialdir=os.path.join(os.getcwd(), "predata"), # predata 폴더에서 시작하도록 변경
        filetypes=([("CSV Files", "*.csv"), ("All files", "*.*")]),
    )

    if not input_csv_file:
        print("파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    # --- 설정 (사용자 수정 가능) ---
    # 학습된 모델(.pth 파일)의 전체 경로
    TRAINED_MODEL_PATH = r'C:\Users\chan2\Desktop\Can-Satellite\trained_models\best_model.pth'
    # 결과(복원된 CSV, 그래프)를 저장할 디렉토리 경로
    OUTPUT_DIR = r'C:\Users\chan2\Desktop\Can-Satellite\denoised_results_mc'
    # 몬테카를로 샘플링 횟수 (많을수록 안정적이지만 오래 걸림)
    MC_SAMPLES = 30

    print(f"Selected file: {input_csv_file}")
    print(f"Using model: {TRAINED_MODEL_PATH}")

    denoise_spectrum_mc(
        model_path=TRAINED_MODEL_PATH,
        input_csv_path=input_csv_file,
        output_dir=OUTPUT_DIR,
        mc_samples=MC_SAMPLES
    )

if __name__ == '__main__':
    print("--- Denoising with Monte Carlo Dropout ---")
    main()
