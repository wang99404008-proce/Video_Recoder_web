FROM python:3.10-slim

# 安裝 FFmpeg 與 Node.js (用於 YouTube JS 簽章解析)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 套件
RUN pip install --no-cache-dir streamlit yt-dlp

COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]