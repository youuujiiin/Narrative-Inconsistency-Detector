@echo off

echo AI 환경 설정 시작

python -m venv .venv

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo 설치 완료
echo 가상환경 활성화:
echo .venv\Scripts\activate

pause