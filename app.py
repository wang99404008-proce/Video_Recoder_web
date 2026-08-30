import os
import re
import streamlit as st
import streamlit.components.v1 as components
import subprocess
import json
import signal

st.set_page_config(page_title="全能高畫質影片側錄器", layout="centered")

st.title("🎬 全能高畫質影片側錄器")
st.subheader("免開全螢幕 · 雲端極速無損擷取 (全相容修復版)")

if "recording_pid" not in st.session_state:
    st.session_state.recording_pid = None

# 雲端通用指令名稱
YTDLP_PATH = "yt-dlp"
FFMPEG_PATH = "ffmpeg"

# 自動偵測是否存在 cookies.txt 避免 429 阻擋
COOKIES_ARG = "--cookies cookies.txt" if os.path.exists("cookies.txt") else ""
YTDLP_EXTRACTOR_ARGS = f'{COOKIES_ARG} --extractor-args "youtube:player_client=android,ios,web"'

# 輔助函式：自動提取 YouTube 影片 ID
def get_youtube_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|live\/|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# 輔助函式：安全渲染影片播放器（解決直播存檔無法預覽問題）
def render_video_player(url):
    yt_id = get_youtube_id(url)
    if yt_id:
        embed_html = f"""
        <iframe width="100%" height="420" 
                src="https://www.youtube.com/embed/{yt_id}" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
        </iframe>
        """
        components.html(embed_html, height=430)
    else:
        st.video(url)

# 輔助函式：將字串 "HH:MM:SS" 轉成總秒數
def str_to_seconds(time_str):
    try:
        time_str = time_str.strip()
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except:
        return None
    return None

# 輔助函式：將總秒數轉回字串格式 (HH:MM:SS)
def secs_to_str(secs):
    secs = max(0, secs)
    h, m = divmod(secs, 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# 1. 影片狀態選擇
mode = st.radio(
    "請選擇影片狀態：",
    ["1. 直播結束 (精準範圍裁切)", "2. 即將/正在直播 (放著讓它錄)"],
    horizontal=True,
    disabled=(st.session_state.recording_pid is not None)
)

video_url = st.text_input("請輸入影片或直播網址 (支援 YouTube/Twitch 等):", "")

# =====================================================================
# 模式 1：直播結束 (精準範圍裁切)
# =====================================================================
if "1." in mode and video_url:
    with st.spinner("正在獲取影片資訊..."):
        try:
            cmd = f'{YTDLP_PATH} {YTDLP_EXTRACTOR_ARGS} "{video_url}" --dump-json --skip-download --allow-unplayable-formats'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(result.stderr)
                
            video_info = json.loads(result.stdout)
            duration = int(video_info.get('duration', 600))
            title = video_info.get('title', '未命名影片')
            
            st.success(f"🎬 成功載入影片：{title}")
            render_video_player(video_url)
            
            st.markdown("### ⏱️ 設定側錄範圍")
            st.caption("請直接在欄位中輸入時間（格式為 時:分:秒 或 分:秒）")
            
            col1, col2 = st.columns(2)
            with col1:
                input_start_str = st.text_input("1. 手動輸入【開始時間】:", "00:00:00", help="例如 01:23:45")
            with col2:
                default_end = secs_to_str(min(10, duration))
                input_end_str = st.text_input("2. 手動輸入【結束時間】:", default_end, help="例如 01:25:00")
            
            base_start_secs = str_to_seconds(input_start_str)
            base_end_secs = str_to_seconds(input_end_str)
            
            if base_start_secs is None or base_end_secs is None:
                st.error("⚠️ 時間格式輸入錯誤！請確保格式為 `時:分:秒` (例如 00:01:30)")
            else:
                st.markdown("#### 🔍 範圍微調")
                fine_tune_start = st.slider("開始時間微調（秒）：", min_value=-30, max_value=30, value=0, step=1)
                fine_tune_end = st.slider("結束時間微調（秒）：", min_value=-30, max_value=30, value=0, step=1)
                
                final_start_secs = max(0, base_start_secs + fine_tune_start)
                final_end_secs = min(duration, base_end_secs + fine_tune_end)
                
                final_start_str = secs_to_str(final_start_secs)
                final_end_str = secs_to_str(final_end_secs)
                
                if final_end_secs <= final_start_secs:
                    st.error("❌ 警告：最終結束時間必須大於開始時間！")
                else:
                    st.info(f"📋 最終裁切範圍：`{final_start_str}` 至 `{final_end_str}` (總計 {final_end_secs - final_start_secs} 秒)")
                    
                    if st.button("🚀 開始高畫質背景裁切", type="primary"):
                        output_filename = "vod_output.mp4"
                        if os.path.exists(output_filename):
                            os.remove(output_filename)
                        
                        status_placeholder = st.empty()
                        status_placeholder.markdown("⏳ **正在安全解析高畫質即時串流 URL...**")
                        
                        cmd_get_url = f'{YTDLP_PATH} {YTDLP_EXTRACTOR_ARGS} -g "{video_url}"'
                        urls_result = subprocess.run(cmd_get_url, shell=True, capture_output=True, text=True)
                        
                        if urls_result.returncode == 0:
                            urls = urls_result.stdout.strip().split('\n')
                            status_placeholder.markdown("⚡ **URL 解析成功！正在啟動雲端轉碼裁切中...**")
                            
                            headers = (
                                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
                                "Referer: https://www.youtube.com/\r\n"
                                "Origin: https://www.youtube.com\r\n"
                            )
                            net_args = f'-headers "{headers}" -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1'
                            transcode_args = "-c:v libx264 -preset ultrafast -b:v 3000k -c:a aac -b:a 128k"
                            
                            if len(urls) >= 2:
                                video_stream_url = urls[0]
                                audio_stream_url = urls[1]
                                cmd_download = (
                                    f'{FFMPEG_PATH} {net_args} -ss {final_start_str} -to {final_end_str} -i "{video_stream_url}" '
                                    f'{net_args} -ss {final_start_str} -to {final_end_str} -i "{audio_stream_url}" '
                                    f'{transcode_args} -y "{output_filename}"'
                                )
                            else:
                                cmd_download = f'{FFMPEG_PATH} {net_args} -ss {final_start_str} -to {final_end_str} -i "{urls[0]}" {transcode_args} -y "{output_filename}"'
                            
                            process_result = subprocess.run(cmd_download, shell=True, capture_output=True, text=True)
                            
                            if process_result.returncode == 0 and os.path.exists(output_filename):
                                status_placeholder.empty()
                                st.success("🎉 側錄成功！高畫質 MP4 影片已生成。")
                                with open(output_filename, "rb") as file:
                                    st.download_button(
                                        label="💾 下載高畫質片段 (MP4)",
                                        data=file,
                                        file_name=f"clip_{final_start_str.replace(':','-')}.mp4",
                                        mime="video/mp4"
                                    )
                            else:
                                status_placeholder.empty()
                                st.error("❌ FFMPEG 轉碼裁切失敗。")
                                st.code(process_result.stderr)
                        else:
                            status_placeholder.empty()
                            st.error("❌ 無法從該網址解析影音串流。")
                            st.code(urls_result.stderr)
                            
        except Exception as e:
            st.error(f"解析影片失敗: {e}")

# =====================================================================
# 模式 2：即將/正在直播 (放著讓它錄)
# =====================================================================
elif "2." in mode and video_url:
    st.markdown("### 🔴 直播錄製設定")
    render_video_player(video_url)
    
    record_minutes = st.number_input("預計錄製時間 (分鐘)，輸入 0 代表手動停止:", min_value=0, value=5)
    output_filename = "live_output.mp4"
    
    if st.session_state.recording_pid is None:
        if st.button("🔴 開始雲端錄製直播", type="primary"):
            if os.path.exists(output_filename):
                os.remove(output_filename)
                
            cmd = f'{YTDLP_PATH} {YTDLP_EXTRACTOR_ARGS} --no-part "{video_url}" -o "{output_filename}"'
            if record_minutes > 0:
                seconds = record_minutes * 60
                cmd = f'{YTDLP_PATH} {YTDLP_EXTRACTOR_ARGS} --no-part --downloader {FFMPEG_PATH} --downloader-args "ffmpeg:-t {seconds}" "{video_url}" -o "{output_filename}"'
            
            process = subprocess.Popen(cmd, shell=True)
            st.session_state.recording_pid = process.pid
            st.rerun()
    else:
        st.warning("⏳ 雲端正在側錄中...")
        if st.button("⏹️ 停止側錄並存檔", type="secondary"):
            try:
                os.kill(st.session_state.recording_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            st.session_state.recording_pid = None
            st.success("側錄已停止！")
            st.rerun()

    if os.path.exists(output_filename) and st.session_state.recording_pid is None:
        st.markdown("---")
        with open(output_filename, "rb") as file:
            st.download_button(
                label="💾 下載直播側錄檔",
                data=file,
                file_name="live_record.mp4",
                mime="video/mp4"
            )
