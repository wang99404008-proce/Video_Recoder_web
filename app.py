import os
import streamlit as st
import subprocess
import json
import signal

st.set_page_config(page_title="全能高畫質影片側錄器", layout="centered")

st.title("🎬 全能高畫質影片側錄器")
st.subheader("免開全螢幕 · 雲端極速無損擷取")

if "recording_pid" not in st.session_state:
    st.session_state.recording_pid = None

YTDLP_PATH = "yt-dlp"
FFMPEG_PATH = "ffmpeg"

mode = st.radio(
    "請選擇影片狀態：",
    ["1. 直播結束 (精準範圍裁切)", "2. 即將/正在直播 (放著讓它錄)"],
    horizontal=True,
    disabled=(st.session_state.recording_pid is not None)
)

video_url = st.text_input("請輸入影片或直播網址 (支援 YouTube/Twitch 等):", "")

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

def secs_to_str(secs):
    secs = max(0, secs)
    h, m = divmod(secs, 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

if "1." in mode and video_url:
    with st.spinner("正在獲取影片資訊..."):
        try:
            cmd = f'{YTDLP_PATH} "{video_url}" --dump-json --skip-download --allow-unplayable-formats'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(result.stderr)
                
            video_info = json.loads(result.stdout)
            duration = int(video_info.get('duration', 600))
            title = video_info.get('title', '未命名影片')
            
            st.success(f"🎬 成功載入影片：{title}")
            st.video(video_url)
            
            st.markdown("### ⏱️ 設定側錄範圍")
            col1, col2 = st.columns(2)
            with col1:
                input_start_str = st.text_input("1. 手動輸入【開始時間】:", "00:00:00")
            with col2:
                default_end = secs_to_str(min(10, duration))
                input_end_str = st.text_input("2. 手動輸入【結束時間】:", default_end)
            
            base_start_secs = str_to_seconds(input_start_str)
            base_end_secs = str_to_seconds(input_end_str)
            
            if base_start_secs is None or base_end_secs is None:
                st.error("⚠️ 時間格式輸入錯誤！請確保格式為 `時:分:秒`")
            else:
                fine_tune_start = st.slider("開始時間微調（秒）：", min_value=-30, max_value=30, value=0, step=1)
                fine_tune_end = st.slider("結束時間微調（秒）：", min_value=-30, max_value=30, value=0, step=1)
                
                final_start_secs = max(0, base_start_secs + fine_tune_start)
                final_end_secs = min(duration, base_end_secs + fine_tune_end)
                final_start_str = secs_to_str(final_start_secs)
                final_end_str = secs_to_str(final_end_secs)
                
                if final_end_secs <= final_start_secs:
                    st.error("❌ 警告：結束時間必須大於開始時間！")
                else:
                    st.info(f"📋 裁切範圍：`{final_start_str}` 至 `{final_end_str}`")
                    if st.button("🚀 開始背景裁切", type="primary"):
                        output_filename = "vod_output.mp4"
                        if os.path.exists(output_filename):
                            os.remove(output_filename)
                        
                        cmd_get_url = f'{YTDLP_PATH} -g "{video_url}"'
                        urls_result = subprocess.run(cmd_get_url, shell=True, capture_output=True, text=True)
                        
                        if urls_result.returncode == 0:
                            urls = urls_result.stdout.strip().split('\n')
                            headers = (
                                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
                                "Referer: https://www.youtube.com/\r\n"
                                "Origin: https://www.youtube.com\r\n"
                            )
                            net_args = f'-headers "{headers}" -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1'
                            transcode_args = "-c:v libx264 -preset ultrafast -b:v 3000k -c:a aac -b:a 128k"
                            
                            if len(urls) >= 2:
                                cmd_download = (
                                    f'{FFMPEG_PATH} {net_args} -ss {final_start_str} -to {final_end_str} -i "{urls[0]}" '
                                    f'{net_args} -ss {final_start_str} -to {final_end_str} -i "{urls[1]}" '
                                    f'{transcode_args} -y "{output_filename}"'
                                )
                            else:
                                cmd_download = f'{FFMPEG_PATH} {net_args} -ss {final_start_str} -to {final_end_str} -i "{urls[0]}" {transcode_args} -y "{output_filename}"'
                            
                            process_result = subprocess.run(cmd_download, shell=True, capture_output=True, text=True)
                            if process_result.returncode == 0 and os.path.exists(output_filename):
                                with open(output_filename, "rb") as file:
                                    st.download_button(
                                        label="💾 下載高畫質片段 (MP4)",
                                        data=file,
                                        file_name=f"clip_{final_start_str.replace(':','-')}.mp4",
                                        mime="video/mp4"
                                    )
                            else:
                                st.error("❌ 轉碼裁切失敗。")
                                st.code(process_result.stderr)
        except Exception as e:
            st.error(f"解析影片失敗: {e}")

elif "2." in mode and video_url:
    st.markdown("### 🔴 直播錄製設定")
    st.video(video_url)
    record_minutes = st.number_input("預計錄製時間 (分鐘):", min_value=1, value=5)
    output_filename = "live_output.mp4"
    
    if st.session_state.recording_pid is None:
        if st.button("🔴 開始雲端錄製直播", type="primary"):
            if os.path.exists(output_filename):
                os.remove(output_filename)
            seconds = record_minutes * 60
            cmd = f'{YTDLP_PATH} --no-part --downloader {FFMPEG_PATH} --downloader-args "ffmpeg:-t {seconds}" "{video_url}" -o "{output_filename}"'
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
            st.rerun()

    if os.path.exists(output_filename) and st.session_state.recording_pid is None:
        with open(output_filename, "rb") as file:
            st.download_button(
                label="💾 下載直播側錄檔",
                data=file,
                file_name="live_record.mp4",
                mime="video/mp4"
            )