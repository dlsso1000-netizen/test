# 📱 SNS 스크래퍼 (TikTok / Instagram) 주의사항

## 개요
본 프로젝트의 `src/services/tiktok.js`, `src/services/instagram.js` 는 각 플랫폼의 **공개 웹페이지에 이미 노출된 메타데이터**(`og:title`, `og:description`, `og:image`, 공개 JSON 스크립트)만 파싱합니다. 로그인/보호된 데이터는 가져오지 않습니다.

## 반드시 지켜야 할 것
1. **상업적 재배포 금지** — 교육/개인 연구 목적으로만 사용.
2. **호출 빈도 제한** — 서버에 15분 캐시가 있지만, 같은 프로필을 분당 수십 번씩 호출하지 마세요.
3. **robots.txt / 이용약관 준수** — 각 플랫폼의 약관을 어기면 IP 차단 혹은 법적 책임이 따를 수 있습니다.
4. **정식 데이터가 필요하면 공식 API 사용**
   - TikTok: https://developers.tiktok.com
   - Instagram Graph API: https://developers.facebook.com/docs/instagram-api

## 기대 가능한 실패 유형
| 증상 | 원인 | 대응 |
|---|---|---|
| HTTP 302 → `/login` 으로 리다이렉트 | 로그인 강제 (주로 Instagram) | 로그인 상태의 쿠키가 없으면 공개 메타도 가끔 숨겨짐. 재시도 / Graph API 전환 |
| 타임아웃(10초 초과) | 플랫폼 CDN 지연 | 재시도 / 다른 계정으로 확인 |
| `stats`가 비어 있음 | 플랫폼이 SIGI/JSON 구조 변경 | `src/services/tiktok.js` 내 `extractSIGI()` 패턴 업데이트 |
| HTTP 429 | 너무 자주 호출 | 캐시 TTL을 늘리거나 IP 회피 없이 기다리기 |

## 구조 변경이 잦습니다
TikTok/Instagram은 분기마다 내부 JSON 키 이름이 바뀝니다. 작동이 멈추면 `docs/cursor-share.md`에 "SNS 파서 깨짐, `extractSIGI` 패턴 확인 필요" 같은 메모만 남기고 커밋해 주시면 Cursor/AI 로 빠르게 패치 가능합니다.

## 대안: 공식 API 연동 예시 (TODO)
- TikTok Login Kit + Research API: 국가·주제별 영상 검색 허용 (승인 필요)
- Instagram Business Login → Graph API: 본인 소유 비즈니스 계정의 통계만 가능
