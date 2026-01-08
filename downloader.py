import customtkinter as ctk
import yt_dlp
import os
import subprocess
import threading
from datetime import datetime

# ==========================================
# 디자인 설정 (다크 모드 & 블루 테마)
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SimpleDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 창 기본 설정
        self.title("유튜브 & 인스타 & 틱톡 분석기")
        self.geometry("600x550")
        self.resizable(False, False)

        # 1. 제목 라벨
        self.label_title = ctk.CTkLabel(self, text="유튜브 & 인스타 & 틱톡 통합 분석기", font=("나눔고딕", 22, "bold"))
        self.label_title.pack(pady=20)

        # 2. 링크 입력칸
        self.entry_url = ctk.CTkEntry(self, width=500, height=45, placeholder_text="유튜브/인스타/틱톡 링크를 붙여넣으세요 (Ctrl+V)")
        self.entry_url.pack(pady=10)

        # 3. 옵션 (자동 캡처 여부)
        self.check_var = ctk.BooleanVar(value=True)
        self.checkbox_capture = ctk.CTkCheckBox(self, text="다운로드 후 '1초 단위' 이미지 자동 추출",
                                                variable=self.check_var, font=("맑은 고딕", 12))
        self.checkbox_capture.pack(pady=10)

        # 4. 실행 버튼
        self.btn_start = ctk.CTkButton(self, text="분석 시작하기", width=250, height=50,
                                       font=("맑은 고딕", 16, "bold"), command=self.start_thread)
        self.btn_start.pack(pady=20)

        # 5. 상태 로그 창
        self.textbox_log = ctk.CTkTextbox(self, width=550, height=220, corner_radius=15)
        self.textbox_log.pack(pady=10)

        # 초기 안내 메시지
        self.log("프로그램 준비 완료!")
        self.log("지원 플랫폼: 유튜브, 인스타그램, 틱톡")
        self.log("틱톡은 워터마크 없이 다운로드됩니다.")

    def log(self, message):
        """로그 창에 글씨를 출력하는 함수"""
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.textbox_log.insert("end", timestamp + message + "\n")
        self.textbox_log.see("end")

    def start_thread(self):
        """버튼 클릭 시 프로그램이 멈추지 않도록 별도 쓰레드 실행"""
        url = self.entry_url.get().strip()
        if not url:
            self.log("링크가 비어있습니다!")
            return

        self.btn_start.configure(state="disabled", text="작업 진행 중...")
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
        else:
            return 'unknown'

    def get_ydl_opts(self, platform):
        """플랫폼별 최적화된 yt-dlp 옵션 반환"""

        # 공통 옵션
        base_opts = {
            'noplaylist': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'quiet': True,
        }

        if platform == 'tiktok':
            # 틱톡 전용 옵션
            return {
                **base_opts,
                'format': 'best',
                'outtmpl': '%(title).50s_%(id)s.%(ext)s',  # 제목 50자 제한 + ID
                # 틱톡 차단 우회를 위한 헤더 설정
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.tiktok.com/',
                },
                # 틱톡 추출기 설정
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                    }
                },
            }

        elif platform == 'instagram':
            # 인스타그램 옵션
            return {
                **base_opts,
                'format': 'best[ext=mp4]/best',
                'outtmpl': '%(title).50s_%(id)s.%(ext)s',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
            }

        else:
            # 유튜브 및 기타 플랫폼
            return {
                **base_opts,
                'format': 'best[ext=mp4]/best',
                'outtmpl': '%(title)s.%(ext)s',
            }

    def run_process(self, url):
        """실제 다운로드 및 캡처 로직"""
        try:
            # 플랫폼 감지
            platform = self.detect_platform(url)
            platform_names = {
                'tiktok': '틱톡',
                'instagram': '인스타그램',
                'youtube': '유튜브',
                'unknown': '알 수 없는 플랫폼'
            }
            self.log(f"감지된 플랫폼: {platform_names[platform]}")

            # ---------------------------------------------------------
            # 1단계: 다운로드
            # ---------------------------------------------------------
            self.log(f"다운로드 시작... ({url[:40]}...)")

            ydl_opts = self.get_ydl_opts(platform)

            filename = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info:
                    filename = ydl.prepare_filename(info)
                    self.log(f"다운로드 성공! 파일명: {filename}")
                else:
                    self.log("다운로드 실패 (링크 확인 또는 비공개 영상일 수 있음)")
                    self.log_troubleshoot(platform)
                    return

            # ---------------------------------------------------------
            # 2단계: 캡처 (FFmpeg 사용)
            # ---------------------------------------------------------
            if self.check_var.get() and filename and os.path.exists(filename):
                self.run_ffmpeg_capture(filename)

            self.log("모든 작업이 끝났습니다! 폴더를 확인하세요.")

        except Exception as e:
            self.log(f"오류 발생: {e}")
            self.log_troubleshoot(self.detect_platform(url))

        finally:
            self.btn_start.configure(state="normal", text="분석 시작하기")

    def log_troubleshoot(self, platform):
        """플랫폼별 문제 해결 팁 출력"""
        if platform == 'tiktok':
            self.log("--- 틱톡 문제 해결 팁 ---")
            self.log("1. 최신 yt-dlp 설치: pip install -U yt-dlp")
            self.log("2. 짧은 URL 대신 전체 URL 사용")
            self.log("3. 비공개 영상은 다운로드 불가")

    def run_ffmpeg_capture(self, video_path):
        """FFmpeg를 사용하여 1초 단위 캡처"""
        self.log("이미지 추출 시작 (FFmpeg 엔진)...")

        # 1. 저장할 폴더 생성
        folder_name = os.path.splitext(video_path)[0] + "_캡처본"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # 2. 저장 파일 패턴
        output_pattern = os.path.join(folder_name, "img_%04d.jpg")

        # 3. FFmpeg 명령어 실행
        command = f'ffmpeg -i "{video_path}" -vf fps=1 "{output_pattern}" -y -loglevel error'

        try:
            subprocess.run(command, shell=True, check=True)
            self.log(f"캡처 완료! 저장 경로: {folder_name}")
        except subprocess.CalledProcessError:
            self.log("FFmpeg 캡처 실패. (FFmpeg 설치가 필요합니다)")
            self.log("터미널에 'winget install Gyan.FFmpeg' 입력")

if __name__ == "__main__":
    app = SimpleDownloaderApp()
    app.mainloop()
