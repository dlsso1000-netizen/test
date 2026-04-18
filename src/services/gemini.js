/**
 * Google Gemini AI 서비스
 * - 채널/영상 분석 자동 리포트
 * - 제목·썸네일 추천
 * - 트렌드 요약
 */
let genAI = null;
let model = null;

function init() {
  const key = process.env.GEMINI_API_KEY;
  if (!key || key.startsWith('여기에')) {
    return null;
  }
  if (!genAI) {
    try {
      const { GoogleGenerativeAI } = require('@google/generative-ai');
      genAI = new GoogleGenerativeAI(key);
      // gemini-1.5-flash는 빠르고 저렴, 분석엔 충분
      model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });
    } catch (e) {
      console.error('[Gemini] 초기화 실패:', e.message);
      return null;
    }
  }
  return model;
}

function isReady() {
  return init() !== null;
}

async function generate(prompt) {
  const m = init();
  if (!m) throw new Error('GEMINI_API_KEY가 설정되지 않았습니다.');
  const result = await m.generateContent(prompt);
  return result.response.text();
}

// --- 고수준 분석 프롬프트 ---

async function analyzeChannel(channel, recentVideos = []) {
  const videosSummary = recentVideos
    .slice(0, 10)
    .map((v, i) => `${i + 1}. "${v.snippet?.title}" (조회수 ${v.statistics?.viewCount || 0})`)
    .join('\n');

  const prompt = `
당신은 YouTube 채널 성장 전략 컨설턴트입니다.
아래 채널을 한국어로 간결하게 분석해 주세요.

## 채널 정보
- 이름: ${channel.snippet?.title}
- 구독자: ${Number(channel.statistics?.subscriberCount || 0).toLocaleString()}
- 총 조회수: ${Number(channel.statistics?.viewCount || 0).toLocaleString()}
- 영상 수: ${Number(channel.statistics?.videoCount || 0).toLocaleString()}
- 소개: ${(channel.snippet?.description || '').slice(0, 300)}
- 국가: ${channel.snippet?.country || '미공개'}

## 최근 영상 TOP 10
${videosSummary || '(데이터 없음)'}

## 분석 요청사항
다음 항목을 각각 2~3문장으로 간결히 작성하세요:
1. **채널 포지셔닝** - 어떤 분야/컨셉인지
2. **강점** - 성공 요인 3가지
3. **약점/개선점** - 보완할 부분 2가지
4. **타겟 시청자** - 주 시청자층 추정
5. **콘텐츠 전략 제안** - 실행 가능한 3가지 아이디어
6. **성장 전망** - 종합 평가 (100점 만점)
`;

  return generate(prompt);
}

async function analyzeTrend(videos, region = 'KR') {
  const list = videos
    .slice(0, 20)
    .map((v, i) => `${i + 1}. [${v.snippet?.channelTitle}] "${v.snippet?.title}" (${Number(v.statistics?.viewCount || 0).toLocaleString()}회)`)
    .join('\n');

  const prompt = `
당신은 YouTube 트렌드 분석 전문가입니다.
현재 **${region}** 지역 인기 영상 TOP 20을 아래와 같이 수집했습니다.

${list}

이 데이터를 바탕으로 한국어로 아래 항목을 분석해 주세요:
1. **현재 뜨는 주제** 3가지
2. **공통된 제목 패턴** (후킹 키워드, 길이 등)
3. **카테고리 분포 요약**
4. **추천 콘텐츠 아이디어** 3가지 (구체적 제목 예시 포함)
5. **한 줄 인사이트**

가능한 한 구체적인 숫자와 예시를 포함하세요.
`;
  return generate(prompt);
}

async function suggestTitles(topic, style = '일반') {
  const prompt = `
당신은 한국 YouTube 조회수 최적화 전문가입니다.
주제: "${topic}"
스타일: ${style}

위 주제로 시청자 클릭률(CTR)이 높은 영상 제목 **10개**를 제안하세요.
각 제목은 다음 조건을 충족:
- 한국어
- 30자 이내
- 궁금증/수치/감정 단어 중 하나 이상 포함
- 진부하지 않고 실제 유튜버가 쓸 법한 톤

출력 형식:
1. (제목) - 추천 이유 한 줄
2. ...
`;
  return generate(prompt);
}

async function compareChannels(channels) {
  const list = channels
    .map(
      (c, i) =>
        `${i + 1}. ${c.snippet?.title} — 구독자 ${Number(c.statistics?.subscriberCount || 0).toLocaleString()}, ` +
        `조회수 ${Number(c.statistics?.viewCount || 0).toLocaleString()}, 영상 ${Number(c.statistics?.videoCount || 0).toLocaleString()}개`
    )
    .join('\n');
  const prompt = `
아래 YouTube 채널들을 비교 분석해 주세요.

${list}

다음 항목으로 한국어 리포트를 작성하세요:
1. **각 채널의 차별점** (한 줄씩)
2. **수치 비교 요약** (구독자 대비 조회수 효율 등)
3. **승자/추천** - 카테고리별 (성장성, 안정성, 참여도)
4. **각 채널이 배울 점**
`;
  return generate(prompt);
}

module.exports = {
  isReady,
  generate,
  analyzeChannel,
  analyzeTrend,
  suggestTitles,
  compareChannels,
};
