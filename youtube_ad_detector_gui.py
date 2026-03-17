#!/usr/bin/env python3
"""
YouTube 광고 구간 탐지기 - GUI 버전
링크만 붙여넣고 버튼 누르면 끝!
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from youtube_ad_detector import (
    extract_video_id,
    fetch_youtube_page,
    extract_ytInitialPlayerResponse,
    extract_all_ads,
    extract_ad_slots_from_html,
    get_player_response_via_api,
    get_sponsorblock_segments,
    get_video_info,
    format_time,
)


class YouTubeAdDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 광고 구간 탐지기")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        self._build_ui()

    def _build_ui(self):
        # 상단 프레임: 입력
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="YouTube 링크 또는 영상 ID:", font=("", 11)).pack(anchor=tk.W)

        input_frame = ttk.Frame(top_frame)
        input_frame.pack(fill=tk.X, pady=(5, 0))

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var, font=("", 11))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", lambda e: self._on_analyze())

        self.analyze_btn = ttk.Button(input_frame, text="분석하기", command=self._on_analyze)
        self.analyze_btn.pack(side=tk.RIGHT)

        # 붙여넣기 버튼
        paste_btn = ttk.Button(top_frame, text="클립보드에서 붙여넣기", command=self._paste_clipboard)
        paste_btn.pack(anchor=tk.E, pady=(5, 0))

        # 진행 상태
        self.status_var = tk.StringVar(value="YouTube 링크를 입력하고 '분석하기'를 누르세요.")
        ttk.Label(self.root, textvariable=self.status_var, foreground="gray", padding=(10, 5)).pack(
            fill=tk.X
        )

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=10)

        # 결과 표시
        result_frame = ttk.Frame(self.root, padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _paste_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.url_var.set(text.strip())
        except tk.TclError:
            messagebox.showinfo("알림", "클립보드가 비어있습니다.")

    def _set_result(self, text: str):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _on_analyze(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("경고", "YouTube 링크를 입력해주세요.")
            return

        try:
            video_id = extract_video_id(url)
        except ValueError:
            messagebox.showerror("오류", "올바른 YouTube 링크 또는 영상 ID가 아닙니다.")
            return

        self.analyze_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self._set_result("")
        self.status_var.set(f"분석 중... (ID: {video_id})")

        thread = threading.Thread(target=self._analyze_worker, args=(video_id,), daemon=True)
        thread.start()

    def _analyze_worker(self, video_id: str):
        lines = []
        all_ads = []
        player_response = {}

        # 1. YouTube 웹페이지 분석
        self.root.after(0, lambda: self.status_var.set("[1/3] YouTube 웹페이지 분석 중..."))
        try:
            html = fetch_youtube_page(video_id)
            player_response = extract_ytInitialPlayerResponse(html)
            total_length_ms = int(
                player_response.get("videoDetails", {}).get("lengthSeconds", 0)
            ) * 1000
            page_ads = extract_all_ads(player_response, total_length_ms)
            html_ads = extract_ad_slots_from_html(html, total_length_ms)
            seen = set()
            for a in page_ads + html_ads:
                if a["time_ms"] not in seen:
                    seen.add(a["time_ms"])
                    all_ads.append(a)
        except Exception as e:
            lines.append(f"[웹페이지 분석 실패: {e}]")

        # 2. InnerTube API
        self.root.after(0, lambda: self.status_var.set("[2/3] InnerTube API 분석 중..."))
        try:
            api_response = get_player_response_via_api(video_id)
            if not player_response:
                player_response = api_response
            total_length_ms = int(
                api_response.get("videoDetails", {}).get("lengthSeconds", 0)
            ) * 1000
            api_ads = extract_all_ads(api_response, total_length_ms)
            seen = {a["time_ms"] for a in all_ads}
            for a in api_ads:
                if a["time_ms"] not in seen:
                    seen.add(a["time_ms"])
                    all_ads.append(a)
        except Exception as e:
            lines.append(f"[API 분석 실패: {e}]")

        all_ads.sort(key=lambda x: x["time_ms"])
        video_info = get_video_info(player_response)

        # 3. SponsorBlock
        self.root.after(0, lambda: self.status_var.set("[3/3] SponsorBlock 조회 중..."))
        sponsors = []
        try:
            sponsors = get_sponsorblock_segments(video_id)
        except Exception as e:
            lines.append(f"[SponsorBlock 조회 실패: {e}]")

        # 결과 조합
        result = self._format_results(video_id, video_info, all_ads, sponsors, lines)
        self.root.after(0, lambda: self._finish(result))

    def _finish(self, result: str):
        self.progress.stop()
        self.analyze_btn.config(state=tk.NORMAL)
        self.status_var.set("분석 완료!")
        self._set_result(result)

    def _format_results(
        self,
        video_id: str,
        video_info: dict,
        ads: list,
        sponsors: list,
        extra_lines: list,
    ) -> str:
        lines = []
        lines.append("=" * 55)
        lines.append("  YouTube 광고 구간 탐지 결과")
        lines.append("=" * 55)
        lines.append(f"  영상: {video_info['title']}")
        lines.append(f"  채널: {video_info['author']}")
        lines.append(f"  길이: {video_info['length_formatted']}")
        lines.append(f"  조회수: {video_info['view_count']}")
        lines.append(f"  ID: {video_id}")
        lines.append("=" * 55)

        # 광고 슬롯
        total_ms = video_info["length_seconds"] * 1000
        preroll = [a for a in ads if a["time_ms"] == 0]
        midroll = [a for a in ads if 0 < a["time_ms"] < total_ms]
        postroll = [a for a in ads if a["time_ms"] >= total_ms and a["time_ms"] > 0]

        lines.append(f"\n[ 광고 슬롯 ] 총 {len(ads)}개")
        lines.append("-" * 40)

        if preroll:
            lines.append(f"\n  [프리롤 광고] {len(preroll)}개")
            for i, a in enumerate(preroll, 1):
                lines.append(f"    {i}. 영상 시작 전 (00:00)")

        if midroll:
            lines.append(f"\n  [미드롤 광고] {len(midroll)}개")
            for i, m in enumerate(midroll, 1):
                lines.append(
                    f"    {i}. {m['time_formatted']}  (영상 시작 후 {m['time_ms'] // 1000}초)"
                )

        if postroll:
            lines.append(f"\n  [포스트롤 광고] {len(postroll)}개")
            for i, a in enumerate(postroll, 1):
                lines.append(f"    {i}. 영상 종료 후")

        if not ads:
            lines.append("  광고 슬롯이 감지되지 않았습니다.")
            lines.append("  (광고 비활성화 또는 비로그인 상태 제한)")

        # SponsorBlock
        lines.append(f"\n[ SponsorBlock 스폰서 구간 ] {len(sponsors)}개")
        lines.append("-" * 40)
        if sponsors:
            for i, s in enumerate(sponsors, 1):
                lines.append(
                    f"  {i}. [{s['category_label']}] "
                    f"{s['start_formatted']} ~ {s['end_formatted']} "
                    f"({s['duration_sec']}초, 투표: {s['votes']})"
                )
        else:
            lines.append("  SponsorBlock에 등록된 구간이 없습니다.")

        # 타임라인
        if ads or sponsors:
            lines.append(f"\n[ 타임라인 ]")
            lines.append("-" * 40)
            total_sec = video_info["length_seconds"]
            if total_sec > 0:
                bar_width = 50
                timeline = list("-" * bar_width)

                for a in ads:
                    pos = max(0, min(int((a["time_ms"] / 1000) / total_sec * (bar_width - 1)), bar_width - 1))
                    timeline[pos] = "V"

                for s in sponsors:
                    sp = max(0, min(int((s["start_ms"] / 1000) / total_sec * (bar_width - 1)), bar_width - 1))
                    ep = max(0, min(int((s["end_ms"] / 1000) / total_sec * (bar_width - 1)), bar_width - 1))
                    for p in range(sp, ep + 1):
                        timeline[p] = "X" if timeline[p] == "V" else "#"

                lines.append(f"  [{''.join(timeline)}]")
                lines.append(
                    f"  0:00{' ' * (bar_width - 8)}{video_info['length_formatted']}"
                )
                lines.append(f"\n  V = 광고 슬롯  # = 스폰서 구간  X = 둘 다")

        if extra_lines:
            lines.append("\n[참고]")
            lines.extend(extra_lines)

        if not ads and not sponsors:
            lines.append("\n참고: YouTube는 비로그인 상태에서 광고 데이터를 제한적으로 제공합니다.")

        return "\n".join(lines)


def main():
    root = tk.Tk()
    YouTubeAdDetectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
