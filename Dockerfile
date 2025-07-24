# 베이스 이미지 선택 (파이썬 포함된 OS)
FROM python:3.9-slim

# 작업 디렉토리 생성 및 설정
WORKDIR /app

# 로컬 파일 복사
COPY . .

# pip 의존성 설치 # git 및 ffmpeg 설치 # 필요한 도구 설치: git, ffmpeg, gcc, g++, python3-dev
RUN apt-get update && apt-get install -y git ffmpeg gcc g++ python3-dev && pip install --no-cache-dir -r requirements.txt

# 포트 열기
EXPOSE 8888

# 서버 실행 명령
CMD ["python", "main.py"]