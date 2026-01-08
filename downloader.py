import customtkinter as ctk
import yt_dlp
import os
import subprocess
import threading
from datetime import datetime
from tkinter import filedialog

# ==========================================
# 디자인 설정 (다크 모드 & 블루 테마)
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SimpleDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 창 기본 설정
        self.title("Video Downloader Pro - 유튜브/인스타/틱톡/트위터")
        self.geometry("650x700")
        self.resizable(False, False)

        # 다운로드 경로 (기본값: 현재 폴더)
        self.download_path = os.getcwd()

        # 1. 제목 라벨
        self.label_title = ctk.CTkLabel(self, text="Video Downloader Pro", font=("나눔고딕", 24, "bold"))
        self.label_title.pack(pady=15)

        self.label_subtitle = ctk.CTkLabel(self, text="유튜브 | 인스타그램 | 틱톡 | 트위터(X) | 페이스북",
                                           font=("맑은 고딕", 12), text_color="gray")
        self.label_subtitle.pack(pady=0)

        # 2. 링크 입력칸
        self.entry_url = ctk.CTkEntry(self, width=550, height=45,
                                      placeholder_text="영상 링크를 붙여넣으세요 (Ctrl+V)")
        self.entry_url.pack(pady=15)

        # 3. 옵션 프레임
        self.options_frame = ctk.CTkFrame(self, width=550)
        self.options_frame.pack(pady=10, padx=20, fill="x")

        # 3-1. 품질 선택
        self.label_quality = ctk.CTkLabel(self.options_frame, text="화질:", font=("맑은 고딕", 12))
        self.label_quality.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.quality_var = ctk.StringVar(value="best")
        self.quality_menu = ctk.CTkOptionMenu(self.options_frame,
                                              values=["best", "1080p", "720p", "480p", "360p", "audio_only"],
                                              variable=self.quality_var, width=120)
        self.quality_menu.grid(row=0, column=1, padx=10, pady=10)

        # 3-2. 썸네일 다운로드
        self.thumb_var = ctk.BooleanVar(value=False)
        self.checkbox_thumb = ctk.CTkCheckBox(self.options_frame, text="썸네일 저장",
                                              variable=self.thumb_var, font=("맑은 고딕", 11))
        self.checkbox_thumb.grid(row=0, column=2, padx=20, pady=10)

        # 3-3. 캡처 옵션
        self.capture_var = ctk.BooleanVar(value=False)
        self.checkbox_capture = ctk.CTkCheckBox(self.options_frame, text="1초 단위 캡처",
                                                variable=self.capture_var, font=("맑은 고딕", 11))
        self.checkbox_capture.grid(row=0, column=3, padx=10, pady=10)

        # 4. 다운로드 경로 프레임
        self.path_frame = ctk.CTkFrame(self, width=550)
        self.path_frame.pack(pady=10, padx=20, fill="x")

        self.label_path = ctk.CTkLabel(self.path_frame, text="저장 경로:", font=("맑은 고딕", 12))
        self.label_path.grid(row=0, column=0, padx=10, pady=10)

        self.entry_path = ctk.CTkEntry(self.path_frame, width=350, height=35)
        self.entry_path.insert(0, self.download_path)
        self.entry_path.grid(row=0, column=1, padx=5, pady=10)

        self.btn_browse = ctk.CTkButton(self.path_frame, text="찾아보기", width=80,
                                        command=self.browse_folder)
        self.btn_browse.grid(row=0, column=2, padx=10, pady=10)

        # 5. 진행률 바
        self.progress_bar = ctk.CTkProgressBar(self, width=550, height=15)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self, text="대기 중...", font=("맑은 고딕", 11))
        self.progress_label.pack()

        # 6. 실행 버튼
        self.btn_start = ctk.CTkButton(self, text="다운로드 시작", width=280, height=50,
                                       font=("맑은 고딕", 16, "bold"), command=self.start_thread)
        self.btn_start.pack(pady=20)

        # 7. 상태 로그 창
        self.textbox_log = ctk.CTkTextbox(self, width=600, height=180, corner_radius=15)
        self.textbox_log.pack(pady=10)

        # 초기 안내 메시지
        self.log("프로그램 준비 완료!")
        self.log("지원: 유튜브, 인스타그램, 틱톡, 트위터(X), 페이스북")
        self.log("팁: 틱톡은 워터마크 없이 다운로드됩니다!")

    def browse_folder(self):
        """폴더 선택 다이얼로그"""
        folder = filedialog.askdirectory()
        if folder:
            self.download_path = folder
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, folder)

    def log(self, message):
        """로그 창에 글씨를 출력하는 함수"""
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.textbox_log.insert("end", timestamp + message + "\n")
        self.textbox_log.see("end")

    def update_progress(self, d):
        """다운로드 진행률 업데이트 (yt-dlp 훅)"""
        if d['status'] == 'downloading':
            # 퍼센트 추출
            if 'downloaded_bytes' in d and 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes']
                self.progress_bar.set(percent)
                self.progress_label.configure(text=f"다운로드 중... {percent*100:.1f}%")
            elif '_percent_str' in d:
                percent_str = d['_percent_str'].strip().replace('%', '')
                try:
                    percent = float(percent_str) / 100
                    self.progress_bar.set(percent)
                    self.progress_label.configure(text=f"다운로드 중... {percent_str}%")
                except ValueError:
                    pass
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="다운로드 완료! 처리 중...")

    def start_thread(self):
        """버튼 클릭 시 별도 쓰레드 실행"""
        url = self.entry_url.get().strip()
        if not url:
            self.log("링크가 비어있습니다!")
            return

        # 다운로드 경로 업데이트
        self.download_path = self.entry_path.get().strip()
        if not os.path.exists(self.download_path):
            self.log("저장 경로가 존재하지 않습니다!")
            return

        self.btn_start.configure(state="disabled", text="다운로드 중...")
        self.progress_bar.set(0)
        threading.Thread(target=self.run_process, args=(url,), daemon=True).start()

    def detect_platform(self, url):
        """URL을 분석하여 플랫폼 감지"""
        url_lower = url.lower()
        if 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
            return 'tiktok'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
            return 'facebook'
        else:
            return 'unknown'

    def get_format_string(self):
        """선택한 품질에 따른 format 문자열 반환"""
        quality = self.quality_var.get()

        format_map = {
            'best': 'best[ext=mp4]/best',
            '1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]',
            '720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            '480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            '360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            'audio_only': 'bestaudio/best',
        }
        return format_map.get(quality, 'best')

    def get_ydl_opts(self, platform):
        """플랫폼별 최적화된 yt-dlp 옵션 반환"""

        # 공통 User-Agent
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

        # 파일명 템플릿
        outtmpl = os.path.join(self.download_path, '%(title).80s_%(id)s.%(ext)s')

        # 공통 옵션
        base_opts = {
            'noplaylist': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'outtmpl': outtmpl,
            'format': self.get_format_string(),
            'progress_hooks': [self.update_progress],
            'writethumbnail': self.thumb_var.get(),
        }

        if platform == 'tiktok':
            # 틱톡 전용 옵션
            return {
                **base_opts,
                'format': 'best',  # 틱톡은 best만 사용
                'http_headers': {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.tiktok.com/',
                },
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                    }
                },
            }

        elif platform == 'instagram':
            return {
                **base_opts,
                'http_headers': {
                    'User-Agent': user_agent,
                },
            }

        elif platform == 'twitter':
            return {
                **base_opts,
                'http_headers': {
                    'User-Agent': user_agent,
                },
            }

        elif platform == 'facebook':
            return {
                **base_opts,
                'http_headers': {
                    'User-Agent': user_agent,
                },
            }

        else:
            # 유튜브 및 기타
            return base_opts

    def run_process(self, url):
        """실제 다운로드 및 캡처 로직"""
        try:
            # 플랫폼 감지
            platform = self.detect_platform(url)
            platform_names = {
                'tiktok': '틱톡',
                'instagram': '인스타그램',
                'youtube': '유튜브',
                'twitter': '트위터(X)',
                'facebook': '페이스북',
                'unknown': '알 수 없음 (자동 감지)'
            }
            self.log(f"감지된 플랫폼: {platform_names[platform]}")
            self.log(f"선택 품질: {self.quality_var.get()}")

            # 다운로드 시작
            self.log(f"다운로드 시작...")

            ydl_opts = self.get_ydl_opts(platform)

            filename = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info:
                    filename = ydl.prepare_filename(info)
                    self.log(f"다운로드 성공!")
                    self.log(f"파일: {os.path.basename(filename)}")

                    # 영상 정보 출력
                    if 'duration' in info and info['duration']:
                        duration = info['duration']
                        mins, secs = divmod(duration, 60)
                        self.log(f"길이: {int(mins)}분 {int(secs)}초")

                    if 'view_count' in info and info['view_count']:
                        self.log(f"조회수: {info['view_count']:,}회")
                else:
                    self.log("다운로드 실패!")
                    self.log_troubleshoot(platform)
                    return

            # 캡처 실행
            if self.capture_var.get() and filename and os.path.exists(filename):
                self.run_ffmpeg_capture(filename)

            self.log("모든 작업 완료!")
            self.progress_label.configure(text="완료!")

        except Exception as e:
            self.log(f"오류 발생: {e}")
            self.log_troubleshoot(self.detect_platform(url))

        finally:
            self.btn_start.configure(state="normal", text="다운로드 시작")

    def log_troubleshoot(self, platform):
        """플랫폼별 문제 해결 팁"""
        self.log("--- 문제 해결 팁 ---")
        self.log("1. yt-dlp 업데이트: pip install -U yt-dlp")

        if platform == 'tiktok':
            self.log("2. 전체 URL 사용 (짧은 URL 말고)")
            self.log("3. 비공개 영상은 다운로드 불가")
        elif platform == 'instagram':
            self.log("2. 공개 계정의 영상만 가능")
            self.log("3. 릴스/스토리는 전체 URL 필요")
        elif platform == 'twitter':
            self.log("2. 트윗 URL 전체를 복사하세요")

    def run_ffmpeg_capture(self, video_path):
        """FFmpeg를 사용하여 1초 단위 캡처"""
        self.log("이미지 추출 시작...")
        self.progress_label.configure(text="이미지 추출 중...")

        folder_name = os.path.splitext(video_path)[0] + "_captures"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        output_pattern = os.path.join(folder_name, "frame_%04d.jpg")
        command = f'ffmpeg -i "{video_path}" -vf fps=1 "{output_pattern}" -y -loglevel error'

        try:
            subprocess.run(command, shell=True, check=True)
            # 생성된 이미지 개수 확인
            image_count = len([f for f in os.listdir(folder_name) if f.endswith('.jpg')])
            self.log(f"캡처 완료! {image_count}장 생성")
            self.log(f"저장 위치: {folder_name}")
        except subprocess.CalledProcessError:
            self.log("FFmpeg 캡처 실패")
            self.log("FFmpeg 설치: winget install Gyan.FFmpeg")
        except FileNotFoundError:
            self.log("FFmpeg가 설치되어 있지 않습니다")

if __name__ == "__main__":
    app = SimpleDownloaderApp()
    app.mainloop()
