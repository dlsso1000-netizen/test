# 🎬 종합사용툴 (Jonghap Tool)

YouTube Data API v3 + Gemini AI 기반 **유튜브 트렌드 분석 대시보드**

> 참고 사이트: [NoxInfluencer](https://kr.noxinfluencer.com/) · [Playboard](https://playboard.co/) · [Vling](https://vling.net/)

---

## ✨ 주요 기능

- 🌍 **국가별 인기 영상 TOP 50** (한국/일본/미국/영국/독일/프랑스/브라질/인도)
- 📊 **조회수/좋아요/댓글 통계** 실시간 표시
- 🔎 **영상 검색** (키워드 기반)
- 📺 **채널 상세 정보** 조회 (구독자, 총 조회수, 영상 수)
- 🤖 **(준비 중) Gemini AI 자동 분석 리포트**

---

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/dlsso1000-netizen/test.git
cd test
```

### 2. 의존성 설치
```bash
npm install
```

### 3. 환경변수 설정
```bash
# .env.example을 복사해서 .env 만들기
cp .env.example .env

# .env 파일을 열어 API 키 입력
# YOUTUBE_API_KEY=발급받은_키
# GEMINI_API_KEY=발급받은_키 (선택)
```

### 4. 서버 실행
```bash
npm start
```

### 5. 브라우저 접속
👉 http://localhost:3000

---

## 🔑 API 키 발급 방법

### YouTube Data API v3 (필수)
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성
3. "YouTube Data API v3" 활성화
4. 사용자 인증 정보 → API 키 생성
5. **무료 할당량: 10,000 유닛/일** (매일 한국시간 오후 5시 리셋)

### Gemini API (선택 - AI 분석용)
1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
2. API 키 생성
3. `.env`의 `GEMINI_API_KEY`에 입력

---

## 📊 API 유닛 소모량

| 기능 | 엔드포인트 | 소모 유닛 |
|---|---|---|
| 인기 영상 TOP 50 | `/api/trending` | **1** |
| 채널 정보 | `/api/channel/:id` | **1** |
| 영상 검색 | `/api/search?q=...` | **100** 🔥 |
| 상태 확인 | `/api/health` | 0 |

💡 **팁**: 검색은 유닛을 많이 소모하니 자주 사용하지 마세요!

---

## 📁 프로젝트 구조

```
종합사용툴/
├── src/
│   └── server.js          # 메인 서버 (Express + YouTube API)
├── public/
│   └── index.html         # 대시보드 UI
├── samples/               # 샘플 데이터 (에러 재현용)
├── docs/
│   └── cursor-share.md    # Cursor AI 공유용 문서
├── scripts/
│   └── make-zip.sh        # 종합사용툴.zip 패키징
├── .github/workflows/
│   └── package-zip.yml    # GitHub Actions 자동 빌드
├── .env.example           # 환경변수 예시
├── .gitignore             # Git 제외 목록
├── package.json
└── README.md
```

---

## 📦 ZIP 다운로드 (`종합사용툴.zip`)

### 방법 1: 로컬에서 생성 (추천)
```bash
bash scripts/make-zip.sh
# → 프로젝트 루트에 "종합사용툴.zip" 생성됨
```

### 방법 2: GitHub에서 소스 다운로드
1. 저장소 우측 상단 **"Code" → "Download ZIP"** 클릭
2. 다운로드 후 압축 해제
3. 이름 변경: `test-main` → `종합사용툴`

---

## 🛠️ 기술 스택

- **Backend**: Node.js + Express
- **Frontend**: Vanilla HTML/CSS/JS (빌드 없음, 즉시 실행)
- **API**: YouTube Data API v3 + Gemini API
- **배포**: GitHub Pages / Vercel / Cloudflare (선택)

---

## ⚠️ 주의사항

- **`.env` 파일은 절대 커밋하지 마세요!** (`.gitignore`에 이미 포함됨)
- API 키 유출 시 즉시 Google Cloud Console에서 재발급
- YouTube API 약관 준수: 데이터 재판매 금지, 크레딧 표시 권장

---

## 📝 라이선스

MIT License

## 👤 제작자

[@dlsso1000-netizen](https://github.com/dlsso1000-netizen)
