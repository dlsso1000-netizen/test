# 📋 Cursor 공유용 - 종합사용툴 프로젝트 현황

> **한 줄 요약**: 종합사용툴 v1.0 초기 세팅 완료 (YouTube API v3 + 대시보드), `.env`에 `YOUTUBE_API_KEY` 설정 후 `npm start` 실행

**브랜치**: `main`
**최근 커밋**: 초기 프로젝트 세팅 (종합사용툴 v1.0)
**작업 환경**: GenSpark → 같은 레포 push

---

## 🎯 이번 작업에서 한 것

### ✅ 완료
1. **프로젝트 구조 생성**
   - `src/server.js` - Express 서버 + YouTube API 래퍼
   - `public/index.html` - 대시보드 UI (국가 선택 + 영상 검색)
   - `package.json` - 의존성 정의
   - `.env.example` - 환경변수 템플릿
   - `.gitignore` - 민감정보/빌드 결과 제외

2. **API 엔드포인트 (4개)**
   - `GET /api/health` - 서버 + API 키 상태 확인
   - `GET /api/trending?region=KR` - 국가별 인기 영상 TOP 50 (1 유닛)
   - `GET /api/channel/:channelId` - 채널 상세 정보 (1 유닛)
   - `GET /api/search?q=키워드` - 영상 검색 (100 유닛 🔥 주의)

3. **ZIP 패키징**
   - `scripts/make-zip.sh` - 로컬에서 `종합사용툴.zip` 생성

4. **문서화**
   - `README.md` - 설치/실행 가이드
   - `docs/cursor-share.md` - 이 파일

---

## 🔑 환경변수 필요

`.env` 파일에 다음 입력:
```
YOUTUBE_API_KEY=AIzaSy...        # 필수
GEMINI_API_KEY=AIzaSy...         # 선택 (AI 분석용)
PORT=3000                         # 선택 (기본 3000)
DEFAULT_REGION=KR                 # 선택 (기본 KR)
```

**API 키 발급처**:
- YouTube: https://console.cloud.google.com/
- Gemini: https://aistudio.google.com/apikey

---

## 🧪 로컬 테스트 방법

```bash
# 1. 클론
git clone https://github.com/dlsso1000-netizen/test.git
cd test

# 2. 설치
npm install

# 3. 환경변수 설정
cp .env.example .env
# .env 파일 열어서 YOUTUBE_API_KEY 값 입력

# 4. 실행
npm start

# 5. 브라우저
# http://localhost:3000
```

---

## 📝 Cursor에서 봐야 할 파일

| 파일 | 역할 | 수정 시 주의 |
|---|---|---|
| `src/server.js` | 메인 서버, API 라우트 | YouTube API 호출 로직 |
| `public/index.html` | 대시보드 UI | 디자인/UX 개선 |
| `package.json` | 의존성 | 패키지 추가 시 `npm install` 필수 |
| `.env.example` | 환경변수 템플릿 | 키 이름만, 값 X |
| `scripts/make-zip.sh` | ZIP 패키징 | 파일명 변경 시 수정 |

---

## 🚧 다음 작업 후보 (TODO)

### Phase 2 - 데이터 수집 자동화
- [ ] 매일 자정 국가별 TOP 100 수집 → `data/` 폴더에 JSON 저장
- [ ] SQLite 또는 JSON DB로 히스토리 추적
- [ ] 구독자/조회수 추이 그래프 (Chart.js)

### Phase 3 - Gemini AI 연동
- [ ] `/api/analyze` 엔드포인트 추가
- [ ] "이 채널 성공 요인 분석" AI 리포트
- [ ] 영상 제목/썸네일 추천 기능

### Phase 4 - 플랫폼 확장
- [ ] Instagram 스크래핑 (NoxInfluencer 스타일)
- [ ] TikTok 스크래핑
- [ ] 다중 플랫폼 통합 대시보드

---

## 🐛 알려진 이슈

### 이슈 1: `.env` 없이 실행 시 500 에러
- **증상**: `/api/trending` 호출 시 "YOUTUBE_API_KEY가 설정되지 않았습니다"
- **해결**: `.env` 파일 생성 + 키 입력
- **재현 파일**: `samples/kie-error-example.json` (향후 추가)

### 이슈 2: 검색 기능 유닛 소모 큼
- **증상**: `/api/search` 1회 = 100 유닛
- **해결**: 검색 결과 캐싱 (Phase 2에서 구현 예정)

---

## 🔗 참고 링크

- **레포**: https://github.com/dlsso1000-netizen/test
- **YouTube API 문서**: https://developers.google.com/youtube/v3/docs
- **Gemini API 문서**: https://ai.google.dev/docs
- **참고 서비스**:
  - https://kr.noxinfluencer.com/
  - https://playboard.co/
  - https://vling.net/

---

## 📦 ZIP 다운로드 (`종합사용툴.zip`)

### 로컬 빌드 (추천)
```bash
bash scripts/make-zip.sh
# → 프로젝트 루트에 "종합사용툴.zip" 생성
```

### GitHub에서 소스 다운로드
- 저장소 우측 상단 "Code → Download ZIP" 클릭
- 기본 이름: `test-main.zip` → `종합사용툴.zip`으로 변경해 사용

---

**마지막 업데이트**: 2026-04-18 (초기 세팅)
