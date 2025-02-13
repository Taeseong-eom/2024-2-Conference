# Linux 기반 Python 이미지 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt .

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 컨테이너에서 사용할 포트 노출
EXPOSE 5000

# Gunicorn으로 실행
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
