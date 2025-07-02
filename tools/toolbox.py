import tkinter as tk
from tkinter import filedialog, messagebox
import os

# 모듈 불러오기
import module.axishifter as ax
import module.resampler as res
import module.de_baseline as db
import module.graph as graph
import module.fft as fft
import module.snr as snr
import module.doffler as doffler
import module.info as info

selected_file = None

def select_file():
    global selected_file
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        selected_file = file_path
        file_label.config(text=os.path.basename(file_path))
        messagebox.showinfo("파일 선택됨", f"선택된 파일:\n{file_path}")

def preprocess():
    if not selected_file:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")
        return
    try:
        # 1단계: 주파수 → 속도 축 변환
        ax.main(selected_file)
        shifted_file = selected_file.replace(".csv", "_shifted.csv")

        # 2단계: 리샘플링
        res.main(shifted_file)
        resampled_file = shifted_file.replace(".csv", "_resampled.csv")

        # 3단계: 베이스라인 제거
        db.main(resampled_file)
        final_file = resampled_file.replace(".csv", "_nobase.csv")

        messagebox.showinfo("전처리 완료", f"전처리 결과 파일:\n{final_file}")
    except Exception as e:
        messagebox.showerror("전처리 실패", str(e))

def view_graph():
    if selected_file:
        graph.main(selected_file)
    else:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")

def run_fft():
    if selected_file:
        fft.main(selected_file)
    else:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")

def calc_snr():
    if selected_file:
        snr.main(selected_file)
    else:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")

def run_doffler():
    if selected_file:
        doffler.main(selected_file)
    else:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")

def show_info():
    if selected_file:
        info.main(selected_file)
    else:
        messagebox.showerror("에러", "먼저 파일을 선택하세요.")

# GUI 구성
root = tk.Tk()
root.title("CanSat 1D Hydrogen Spectrum 분석 툴")
root.geometry("400x400")

tk.Button(root, text="파일 선택", command=select_file, width=30).pack(pady=10)
file_label = tk.Label(root, text="선택된 파일 없음")
file_label.pack()

tk.Button(root, text="전처리 (축변환→리샘플링→베이스라인)", command=preprocess, width=40).pack(pady=10)
tk.Button(root, text="그래프 보기", command=view_graph, width=40).pack(pady=5)
tk.Button(root, text="SNR 계산", command=calc_snr, width=40).pack(pady=5)
tk.Button(root, text="FFT 실행", command=run_fft, width=40).pack(pady=5)
tk.Button(root, text="도플러 제거 (NRAO 전용)", command=run_doffler, width=40).pack(pady=5)
tk.Button(root, text="메타정보 보기 (NRAO 전용)", command=show_info, width=40).pack(pady=5)

root.mainloop()
