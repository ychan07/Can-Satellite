import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import random
import tkinter as tk
from tkinter import filedialog

def create_comparison_plot(csv_path, output_dir):
    """
    증강된 데이터 파일 하나를 읽어, 원본과 증강된 데이터를 비교하는 그래프를 생성합니다.
    """
    try:
        data = pd.read_csv(csv_path, sep=r'\s+', header=None, comment='#')
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다 - {csv_path}")
        return
    except Exception as e:
        print(f"오류: {csv_path} 파일을 읽는 중 문제가 발생했습니다: {e}")
        return

    if data.shape[1] < 8:
        print(f"오류: {csv_path} 파일은 증강 데이터 열(8개)을 포함하고 있지 않습니다.")
        return

    velocity = data.iloc[:, 0]
    original_flux = data.iloc[:, 1]
    aug_col_idx = random.randint(3, 7)
    augmented_flux = data.iloc[:, aug_col_idx]

    print(f"파일 '{os.path.basename(csv_path)}'을 시각화합니다.")
    print(f"  - 원본 데이터: 2번 열 (flux)")
    print(f"  - 비교할 증강 데이터: {aug_col_idx + 1}번 열")

    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(18, 8))

    plt.plot(velocity, original_flux, label='Original Clean Flux (Ground Truth)', color='#007ACC', linewidth=2, alpha=0.9)
    plt.plot(velocity, augmented_flux, label=f'Augmented Noisy Flux (Column {aug_col_idx + 1})', color='#FF5733', linestyle='--', alpha=0.8)

    plt.title(f'Original vs. Augmented Data Comparison\n(File: {os.path.basename(csv_path)})', fontsize=16)
    plt.xlabel("Velocity (km/s)", fontsize=12)
    plt.ylabel("Flux", fontsize=12)
    plt.legend(fontsize=10)
    plt.margins(x=0.02, y=0.05)

    os.makedirs(output_dir, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(csv_path))[0]
    output_filepath = os.path.join(output_dir, f"comparison_{base_filename}_col{aug_col_idx+1}.png")
    
    plt.savefig(output_filepath, dpi=150, bbox_inches='tight')
    print(f"\n그래프가 성공적으로 저장되었습니다: {output_filepath}")
    plt.close()

def main():
    """GUI 파일 선택창을 띄우고 메인 로직을 실행하는 함수"""
    # --- GUI 파일 선택창 설정 ---
    root = tk.Tk()
    root.withdraw() # 메인 tk 창은 숨깁니다.

    print("파일 선택창을 엽니다... 비교할 증강 데이터 파일을 선택해주세요.")

    # 파일 탐색기 창 열기
    input_csv_file = filedialog.askopenfilename(
        title="Select an Augmented CSV File to Visualize",
        initialdir=os.path.join(os.getcwd(), "augmented_data"), # 스크립트 실행 위치의 'augmented_data' 폴더에서 시작
        filetypes=([
            ("Augmented CSV Files", "*.csv"),
            ("All files", "*.*")
        ])
    )

    # --- 파일 선택 후 처리 ---
    if not input_csv_file:
        print("파일을 선택하지 않았습니다. 프로그램을 종료합니다.")
        return

    print(f"선택된 파일: {input_csv_file}")

    # 그래프를 저장할 폴더 설정
    output_graph_dir = r'C:\Users\chan2\Desktop\Can-Satellite\comparison_graphs'

    # 메인 기능 호출
    create_comparison_plot(
        csv_path=input_csv_file,
        output_dir=output_graph_dir
    )

if __name__ == '__main__':
    print("--- Data Comparison Visualizer (GUI) ---")
    main()