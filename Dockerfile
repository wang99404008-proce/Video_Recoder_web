FROM python:3.11-slim

# 安裝 FFmpeg、NodeJS、Curl 與解壓縮工具
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Deno (解決 JS runtime 警告與簽章解析)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

WORKDIR /app

# 安裝 Python 套件
RUN pip install --no-cache-dir streamlit yt-dlp

COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
