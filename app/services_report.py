# app/services_report.py
import os
from google import genai
from app.models import RecommendationReport

SYSTEM_PROMPT = """당신은 한국 주식 시장 AI 예측 분석가입니다.
TFT(Temporal Fusion Transformer) 딥러닝 모델이 생성한 주가 예측 결과와
모델 내부의 피처 중요도·어텐션 데이터를 바탕으로,
투자자가 이해할 수 있는 예측 보고서를 작성합니다.

보고서 작성 원칙:
- 모델이 왜 해당 예측을 내렸는지 근거 중심으로 서술한다.
- 투자 결정을 강요하지 않으며, 분석 근거를 중립적으로 제시한다.
- 기술 용어는 괄호 안에 간단한 설명을 병기한다.
- 수치는 반드시 해석과 함께 제시한다 (숫자만 나열하지 않는다).
- 보고서 말미에는 반드시 투자 유의사항을 포함한다."""

# 피처 해석 매핑
FEATURE_DESC = {
    "rsi_14": ("RSI(14)", lambda v: "과매도 구간" if v < 30 else "과매수 구간" if v > 70 else "중립 구간"),
    "log_ret": ("직전 봉 로그 수익률", lambda v: "직전 봉 상승" if v > 0 else "직전 봉 하락"),
    "disparity_5": ("5봉 이동평균 이격도", lambda v: "단기 과열" if v > 1.03 else "단기 침체" if v < 0.97 else "중립"),
    "disparity_20": ("20봉 이동평균 이격도", lambda v: "중기 과열" if v > 1.05 else "중기 침체" if v < 0.95 else "이동평균 근접"),
    "disparity_60": ("60봉 이동평균 이격도", lambda v: "장기 과열" if v > 1.1 else "장기 침체" if v < 0.9 else "중립"),
    "bb_position": ("볼린저밴드 위치", lambda v: "상단 돌파" if v > 0.8 else "하단 접근" if v < 0.2 else "중앙 구간"),
    "vol_ratio": ("거래량 비율", lambda v: "거래량 급증" if v > 2.0 else "거래량 급감" if v < 0.5 else "보통"),
    "macd_ratio": ("MACD/현재가 비율", lambda v: "상승 모멘텀" if v > 0 else "하락 모멘텀"),
    "kospi_ret": ("KOSPI 당일 등락률", lambda v: f"KOSPI {'상승' if v > 0 else '하락'} {abs(v)*100:.2f}%"),
    "kosdaq_ret": ("KOSDAQ 당일 등락률", lambda v: f"KOSDAQ {'상승' if v > 0 else '하락'} {abs(v)*100:.2f}%"),
    "prop_foreign": ("외국인 순매수 비율", lambda v: "외국인 순매수" if v > 0 else "외국인 순매도"),
    "prop_individual": ("개인 순매수 비율", lambda v: "개인 순매수" if v > 0 else "개인 순매도"),
    "prop_institution": ("기관 순매수 비율", lambda v: "기관 순매수" if v > 0 else "기관 순매도"),
    "per": ("PER", lambda v: f"PER {v:.1f}"),
    "pbr": ("PBR", lambda v: "청산가치 이하" if v < 1 else f"PBR {v:.2f}"),
    "vix_chg": ("VIX 변동", lambda v: "불확실성 증가" if v > 0 else "시장 안도"),
    "usd_krw_chg": ("원달러 환율 변동", lambda v: "원화 약세" if v > 0 else "원화 강세"),
}

EVENT_DESC = {
    "time_progress": "장 진행률",
    "is_bok": "금통위",
    "is_fomc": "FOMC",
    "is_witching_kr": "선물만기(한국)",
    "is_witching_us": "선물만기(미국)",
}


def _format_unknown_past(features: list) -> str:
    """unknown_past 피처를 해석 텍스트로 변환"""
    lines = []
    for f in features:
        name = f["feature"]
        importance = f["importance"]
        value = f.get("current_value")

        desc_name, interpreter = FEATURE_DESC.get(name, (name, lambda v: str(v)))

        if value is not None:
            interpretation = interpreter(value)
            lines.append(f"{f['rank']}위. {desc_name} — 현재값: {value} ({interpretation}), 중요도: {importance:.1%}")
        else:
            lines.append(f"{f['rank']}위. {desc_name} — 중요도: {importance:.1%}")

    return "\n".join(lines)


def _format_known_future(features: list) -> str:
    """known_future 이벤트 피처 텍스트 변환"""
    events = []
    has_event = False

    for f in features:
        name = f["feature"]
        value = f.get("current_value", 0)
        desc = EVENT_DESC.get(name, name)

        if name == "time_progress":
            pct = value * 100
            minutes = int(value * 390)  # 09:00~15:30 = 390분
            events.append(f"장 진행률: {pct:.1f}% (09:00 이후 약 {minutes}분 경과)")
        elif value == 1:
            has_event = True
            events.append(f"{desc}: 해당")
        else:
            events.append(f"{desc}: 없음")

    if not has_event:
        return events[0] + "\n특별한 이벤트 없음 (금통위 · FOMC · 선물만기일 해당 없음)"

    return "\n".join(events)


def _format_attention(peaks: list) -> str:
    """어텐션 피크 텍스트 변환"""
    parts = [f"{p['minutes_ago']}분 전 봉 (어텐션 {p['attention']*100:.1f}%)" for p in peaks]
    return " — ".join(parts)


def _get_confidence_text(prob: float) -> str:
    if prob >= 0.8:
        return "모델이 높은 확신을 보이고 있습니다"
    elif prob >= 0.6:
        return "모델이 다소 우세한 방향성을 제시합니다"
    else:
        return "방향성이 불명확하여 신중한 접근이 필요합니다"


def _get_direction_emoji(pred_str: str, max_prob: float) -> str:
    if pred_str == "매수" and max_prob > 0.6:
        return "🟢"
    elif pred_str == "매도" and max_prob > 0.6:
        return "🔴"
    else:
        return "🟡"


def build_user_prompt(result: dict, ticker_name: str = "") -> str:
    """AI 추론 결과로 Gemini 프롬프트 생성"""
    ticker = result["ticker"]
    interp = result.get("interpretability", {})
    top_features = interp.get("top_features", {})

    unknown_past = _format_unknown_past(top_features.get("unknown_past", []))
    known_future = _format_known_future(top_features.get("known_future", []))
    attention = _format_attention(interp.get("attention_peak", []))

    static = top_features.get("static", [])
    sector_desc = ""
    market_desc = ""
    for s in static:
        if s["feature"] == "sector_id":
            sector_desc = f"{s.get('description', '알 수 없음')} (중요도: {s['importance']:.1%})"
        elif s["feature"] == "market_id":
            market_desc = s.get("description", "알 수 없음")

    display_name = f"{ticker_name}({ticker})" if ticker_name else ticker

    return f"""다음 데이터를 바탕으로 {display_name} 예측 보고서를 작성해 주세요.

─────────────────────────────────────────
[예측 기준 시각]
{result.get('trade_datetime', '')}

[모델 예측 결과]
예측: {result['pred_str']}
매수 확률: {result['prob_buy']*100:.1f}%
관망 확률: {result['prob_hold']*100:.1f}%
매도 확률: {result['prob_sell']*100:.1f}%

[모델이 주목한 주요 피처 (상위 5개)]
{unknown_past}

[이벤트 피처]
{known_future}

[모델이 집중한 시점 (어텐션 상위)]
{attention}

[종목 정보]
섹터: {sector_desc}
시장: {market_desc}
─────────────────────────────────────────

아래 보고서 형식에 맞춰 작성해 주세요."""


def generate_report(result: dict, ticker_name: str = "") -> str:
    """Gemini API로 보고서 생성"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    user_prompt = build_user_prompt(result, ticker_name)

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={"system_instruction": SYSTEM_PROMPT},
        )
        return resp.text
    except Exception as e:
        return f"보고서 생성 실패: {e}"


def save_report(db, user_id: int, persona_id: int, report: str):
    """보고서 DB 저장"""
    db.add(RecommendationReport(
        user_id=user_id,
        persona_id=persona_id,
        report=report,
    ))
    db.commit()