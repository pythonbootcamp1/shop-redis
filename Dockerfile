# Python 3.12 slim 이미지를 베이스로 사용
# slim은 불필요한 패키지를 제거한 경량 버전
FROM python:3.12-slim

# 작업 디렉토리 설정
# 컨테이너 내부에서 /app 디렉토리에서 작업
WORKDIR /app

# Python이 .pyc 파일을 생성하지 않도록 설정
# 컨테이너는 휘발성이므로 캐시 파일 불필요
ENV PYTHONDONTWRITEBYTECODE=1

# Python 출력을 즉시 표시 (버퍼링 안 함)
# 로그를 실시간으로 확인하기 위해 필요
ENV PYTHONUNBUFFERED=1

# 시스템 패키지 업데이트 및 필수 패키지 설치
# PostgreSQL 클라이언트 라이브러리 등
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사
# 의존성이 변경되지 않으면 Docker 캐시를 활용
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 전체 복사
COPY . .

# 8000번 포트 노출
# 실제로 포트를 열지는 않고, 문서화 용도
EXPOSE 8000

# Gunicorn으로 Django 실행
# 0.0.0.0:8000에서 워커 2개로 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "config.wsgi:application"]
