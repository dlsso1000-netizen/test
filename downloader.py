import customtkinter as ctk
import yt_dlp
import os
import subprocess
import threading
from datetime import datetime
from tkinter import filedialog, messagebox
import shutil

# 테마 설정
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SimpleDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 창 설정
        self.title("Video Downloader Pro - 쿠키 지원판")
        self.geometry("650x800")
        self.resizable(False, False)
        self.download_path = os.getcwd()

        # 1. FFmpeg 찾기
        self.ffmpeg_path = self.check_ffmpeg()

        # 제목
        self.label_title = ctk.CTkLabel(self, text="Video Downloader Pro", font=("나눔고딕", 24, "bold"))
        self.label_title.pack(pady=15)

        # 2. 상태 표시
        if self.ffmpeg_path:
            status_text = "✅ FFmpeg 연결됨 (모든 기능 정상)"
            status_color = "#4CAF50" # 초록색
        else:
            status_text = "⚠️ FFmpeg 없음 (썸네일/고화질 불가)"
            status_color = "#FF5252" # 빨간색

        self.label_status = ctk.CTkLabel(self, text=status_text, font=("맑은 고딕", 12, "bold"), text_color=status_color)
        self.label_status.pack(pady=5)

        self.label_subtitle = ctk.CTkLabel(self, text="유튜브(쇼츠) | 틱톡 | 인스타 | 트위터", font=("맑은 고딕", 12), text_color="gray")
        self.label_subtitle.pack(pady=0)

        # URL 입력창
        self.entry_url = ctk.CTkEntry(self, width=550, height=45, placeholder_text="링크를 붙여넣으세요 (Ctrl+V)")
        self.entry_url.pack(pady=15)

        # 옵션 구역
        self.options_frame = ctk.CTkFrame(self, width=550)
        self.options_frame.pack(pady=10, padx=20, fill="x")

        self.label_quality = ctk.CTkLabel(self.options_frame, text="화질:", font=("맑은 고딕", 12))
        self.label_quality.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # 화질 기본값 1080p
        self.quality_var = ctk.StringVar(value="1080p")
        self.quality_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["best", "1080p", "720p", "480p", "audio_only"],
            variable=self.quality_var,
            width=120,
        )
        self.quality_menu.grid(row=0, column=1, padx=10, pady=10)

        # 썸네일 체크박스 (기본 체크)
        self.thumb_var = ctk.BooleanVar(value=True)
        self.checkbox_thumb = ctk.CTkCheckBox(self.options_frame, text="썸네일 저장", variable=self.thumb_var)
        self.checkbox_thumb.grid(row=0, column=2, padx=20, pady=10)

        self.capture_var = ctk.BooleanVar(value=False)
        self.checkbox_capture = ctk.CTkCheckBox(self.options_frame, text="1초 단위 캡처", variable=self.capture_var)
        self.checkbox_capture.grid(row=0, column=3, padx=10, pady=10)

        # 쿠키 옵션 구역
        self.cookie_frame = ctk.CTkFrame(self, width=550)
        self.cookie_frame.pack(pady=10, padx=20, fill="x")

        self.label_cookie = ctk.CTkLabel(self.cookie_frame, text="쿠키:", font=("맑은 고딕", 12))
        self.label_cookie.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.cookie_var = ctk.StringVar(value="사용 안 함")
        self.cookie_menu = ctk.CTkOptionMenu(
            self.cookie_frame,
            values=["사용 안 함", "chrome", "edge", "firefox", "opera", "brave", "쿠키 파일 선택..."],
            variable=self.cookie_var,
            width=160,
            command=self.on_cookie_change,
        )
        self.cookie_menu.grid(row=0, column=1, padx=10, pady=10)

        self.label_cookie_hint = ctk.CTkLabel(
            self.cookie_frame,
            text="⬅ YouTube 봇 차단 시 브라우저 선택",
            font=("맑은 고딕", 10),
            text_color="#FFD700"
        )
        self.label_cookie_hint.grid(row=0, column=2, padx=10, pady=10)

        self.cookie_file_path = None

        # 경로 설정
        self.path_frame = ctk.CTkFrame(self, width=550)
        self.path_frame.pack(pady=10, padx=20, fill="x")

        self.entry_path = ctk.CTkEntry(self.path_frame, width=350, height=35)
        self.entry_path.insert(0, self.download_path)
        self.entry_path.grid(row=0, column=1, padx=5, pady=10)

        self.btn_browse = ctk.CTkButton(self.path_frame, text="폴더 변경", width=80, command=self.browse_folder)
        self.btn_browse.grid(row=0, column=2, padx=10, pady=10)

        # 진행바
        self.progress_bar = ctk.CTkProgressBar(self, width=550, height=15)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self, text="대기 중...", font=("맑은 고딕", 11))
        self.progress_label.pack()

        # 시작 버튼
        self.btn_start = ctk.CTkButton(self, text="다운로드 시작", width=280, height=50,
                                       font=("맑은 고딕", 16, "bold"), command=self.start_thread)
        self.btn_start.pack(pady=20)

        # 로그창
        self.textbox_log = ctk.CTkTextbox(self, width=600, height=150, corner_radius=15)
        self.textbox_log.pack(pady=10)

        self.log("프로그램 준비 완료!")

        if not self.ffmpeg_path:
             self.log("❌ 경고: FFmpeg가 없습니다. 썸네일/고화질 기능이 제한됩니다.")

    def on_cookie_change(self, choice):
        if choice == "쿠키 파일 선택...":
            file_path = filedialog.askopenfilename(
                title="쿠키 파일 선택",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if file_path:
                self.cookie_file_path = file_path
                self.log(f"쿠키 파일 선택됨: {os.path.basename(file_path)}")
            else:
                self.cookie_var.set("사용 안 함")
                self.cookie_file_path = None

    def check_ffmpeg(self):
        current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
        local_ffmpeg = os.path.join(current_dir, 'ffmpeg.exe')
        if os.path.exists(local_ffmpeg): return local_ffmpeg

        cwd_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg.exe')
        if os.path.exists(cwd_ffmpeg): return cwd_ffmpeg

        return shutil.which('ffmpeg')

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path = folder
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, folder)

    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.textbox_log.insert("end", timestamp + message + "\n")
        self.textbox_log.see("end")

    def update_progress(self, d):
        if d["status"] == "downloading":
            if "total_bytes" in d:
                p = d["downloaded_bytes"] / d["total_bytes"]
                self.progress_bar.set(p)
                self.progress_label.configure(text=f"다운로드 중... {p*100:.1f}%")
            elif "_percent_str" in d:
                try:
                    p = float(d["_percent_str"].replace("%","")) / 100
                    self.progress_bar.set(p)
                    self.progress_label.configure(text=f"다운로드 중... {d['_percent_str']}")
                except: pass
        elif d["status"] == "finished":
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="다운로드 완료! (파일 처리 중...)")

    def start_thread(self):
        url = self.entry_url.get().strip()
        if not url: return
        self.ffmpeg_path = self.check_ffmpeg()
        self.btn_start.configure(state="disabled", text="처리 중...")
        self.progress_bar.set(0)
        threading.Thread(target=self.run_process, args=(url,), daemon=True).start()

    def detect_platform(self, url):
        url_lower = url.lower()
        if "tiktok.com" in url_lower: return "tiktok"
        if "instagram.com" in url_lower: return "instagram"
        if "youtube.com" in url_lower or "youtu.be" in url_lower: return "youtube"
        if "twitter.com" in url_lower or "x.com" in url_lower: return "twitter"
        if "facebook.com" in url_lower or "fb.watch" in url_lower: return "facebook"
        return "unknown"

    def get_format_string(self):
        quality = self.quality_var.get()
        format_map = {
            "best": "bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1920]+bestaudio[ext=m4a]/bestvideo[height<=1920]+bestaudio/best[height<=1920]/best",
            "720p": "bestvideo[height<=1280]+bestaudio[ext=m4a]/bestvideo[height<=1280]+bestaudio/best[height<=1280]/best",
            "480p": "bestvideo[height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "audio_only": "bestaudio[ext=m4a]/bestaudio/best",
        }
        return format_map.get(quality, "bestvideo+bestaudio/best")

    def run_process(self, url):
        try:
            platform = self.detect_platform(url)
            self.log(f"다운로드 시작: {platform}")

            # [썸네일 JPG 변환]
            postprocessors = []
            if self.thumb_var.get():
                postprocessors.append({
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                })

            ydl_opts = {
                'outtmpl': os.path.join(self.download_path, '%(title).100s_%(id)s.%(ext)s'),
                'noplaylist': True,
                'format': self.get_format_string(),
                'merge_output_format': 'mp4',
                'progress_hooks': [self.update_progress],
                'writethumbnail': self.thumb_var.get(),
                'postprocessors': postprocessors,
                'no_warnings': True,
                'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
            }

            # 쿠키 옵션 적용
            cookie_choice = self.cookie_var.get()
            if cookie_choice == "쿠키 파일 선택..." and self.cookie_file_path:
                ydl_opts['cookiefile'] = self.cookie_file_path
                self.log(f"쿠키 파일 사용: {os.path.basename(self.cookie_file_path)}")
            elif cookie_choice not in ("사용 안 함", "쿠키 파일 선택..."):
                ydl_opts['cookiesfrombrowser'] = (cookie_choice,)
                self.log(f"브라우저 쿠키 사용: {cookie_choice}")

            if platform == "tiktok":
                 ydl_opts['format'] = 'best'

            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = self.ffmpeg_path

            filename = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                base, _ = os.path.splitext(filename)
                if os.path.exists(base + ".mp4"): filename = base + ".mp4"
                elif os.path.exists(base + ".mkv"): filename = base + ".mkv"

                self.log(f"✅ 다운로드 성공!")
                self.log(f"파일: {os.path.basename(filename)}")

            if self.capture_var.get() and filename and self.ffmpeg_path:
                self.run_capture(filename)

            self.log("🎉 모든 작업 완료!")
            self.progress_label.configure(text="완료!")

        except Exception as e:
            error_msg = str(e)
            self.log(f"오류: {error_msg}")
            if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                self.log("💡 팁: 위 '쿠키' 옵션에서 브라우저를 선택한 뒤 다시 시도하세요!")
                self.log("💡 해당 브라우저에서 YouTube에 로그인되어 있어야 합니다.")
            elif "tiktok" in error_msg.lower():
                self.log("💡 팁: pip install -U yt-dlp 명령어로 업데이트 하세요.")

        # [여기가 핵심!] 작업이 끝나거나 오류가 나도 버튼을 다시 켜주는 코드
        finally:
            self.btn_start.configure(state="normal", text="다운로드 시작")

    def run_capture(self, video_path):
        self.log("이미지 캡처 중...")
        folder = os.path.splitext(video_path)[0] + "_img"
        os.makedirs(folder, exist_ok=True)
        cmd = f'"{self.ffmpeg_path}" -i "{video_path}" -vf fps=1 "{folder}/img_%04d.jpg" -y -loglevel error'
        subprocess.run(cmd, shell=True)
        self.log(f"캡처 완료! ({len(os.listdir(folder))}장)")

if __name__ == "__main__":
    app = SimpleDownloaderApp()
    app.mainloop()
