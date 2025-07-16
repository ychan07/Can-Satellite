import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ✅ 현재 Python 스크립트가 있는 경로 기준으로 저장 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "mangaHI_csv_files_DR3")

# 🌐 CSV 파일이 있는 웹사이트 주소
BASE_URL = "https://www.gb.nrao.edu/GbtLegacyArchive/HI-MANGA/DR3/spectra/gbt/csv/"
MAX_THREADS = 50  # 병렬 다운로드 수 (인터넷 환경에 따라 조정)

# 📁 저장 폴더 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🌐 HTML에서 CSV 링크 가져오기
response = requests.get(BASE_URL)
soup = BeautifulSoup(response.text, "html.parser")
csv_links = [
    urljoin(BASE_URL, a['href']) for a in soup.find_all('a', href=True)
    if a['href'].endswith(".csv")
]

print(f"[INFO] 총 {len(csv_links)}개의 CSV 파일을 찾았습니다. 병렬 다운로드 시작...")

# ⬇️ 개별 파일 다운로드 함수
def download_csv(url):
    file_name = os.path.join(OUTPUT_DIR, os.path.basename(url))
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(file_name, 'wb') as f:
            f.write(r.content)
        return f"[OK] {file_name}"
    except Exception as e:
        return f"[FAIL] {file_name} - {e}"

# 🔁 병렬 다운로드 실행
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    future_to_url = {executor.submit(download_csv, url): url for url in csv_links}
    for i, future in enumerate(as_completed(future_to_url), 1):
        result = future.result()
        print(f"[{i}/{len(csv_links)}] {result}")

print("\n✅ 병렬 다운로드가 모두 완료되었습니다.")
