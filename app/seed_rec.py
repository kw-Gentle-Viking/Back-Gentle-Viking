# app/seed_persona.py
from app.db import get_db
from app.models import Persona, SearchKeyword, ValueWatchlist, StopWord

PERSONA_DATA = [
    {
        "id": 1,
        "name": "안정형",
        "gemini_persona": "원금을 절대 잃지 않는 보수적인 자산가",
        "criteria": "변동성이 극히 적고 배당수익률이 높은 방어주(통신, 금융, 지주사) 위주 선정. 뉴스보다는 PBR, 배당 성향 등 숫자가 기준.",
        "weights": {
            "가치_저평가": 10.0,
            "실적_펀다맨탈": 2.0,
            "호재_모맨텀": 0.0,
            "악재_리스크": -20.0,
            "섹터_트렌드": 0.0,
        },
        "use_value_scout": True,
    },
    {
        "id": 2,
        "name": "안정추구형",
        "gemini_persona": "안정적인 성장을 추구하는 연기금 펀드매니저",
        "criteria": "재무가 탄탄하면서도 적당한 성장성이 있는 대형 우량주(Blue Chip). 저평가된 실적주를 선호.",
        "weights": {
            "가치_저평가": 5.0,
            "실적_펀다맨탈": 5.0,
            "호재_모맨텀": 1.0,
            "악재_리스크": -10.0,
            "섹터_트렌드": 1.0,
        },
        "use_value_scout": True,
    },
    {
        "id": 3,
        "name": "위험중립형",
        "gemini_persona": "실적 기반의 정석 투자자",
        "criteria": "매출과 영업이익이 꾸준히 우상향하는 성장주. 산업의 트렌드를 따라가되, 실체가 없는 테마주는 배제.",
        "weights": {
            "가치_저평가": 2.0,
            "실적_펀다맨탈": 8.0,
            "호재_모맨텀": 3.0,
            "악재_리스크": -5.0,
            "섹터_트렌드": 3.0,
        },
        "use_value_scout": False,
    },
    {
        "id": 4,
        "name": "적극투자형",
        "gemini_persona": "주도주에 올라타는 추세 추종 트레이더",
        "criteria": "현재 시장에서 가장 핫한 섹터(AI, 로봇 등)의 대장주. 신고가 갱신이나 거래량 급증 종목 적극 공략.",
        "weights": {
            "가치_저평가": 0.0,
            "실적_펀다맨탈": 3.0,
            "호재_모맨텀": 7.0,
            "악재_리스크": -3.0,
            "섹터_트렌드": 5.0,
        },
        "use_value_scout": False,
    },
    {
        "id": 5,
        "name": "공격투자형",
        "gemini_persona": "상한가를 노리는 공격적인 스캘퍼",
        "criteria": "오늘 당장 이슈가 터진 급등주. 재무제표보다는 재료의 크기와 수급(거래량)이 최우선.",
        "weights": {
            "가치_저평가": -5.0,
            "실적_펀다맨탈": 0.0,
            "호재_모맨텀": 10.0,
            "악재_리스크": -1.0,
            "섹터_트렌드": 8.0,
        },
        "use_value_scout": False,
    },
]


KEYWORD_DATA = [
    {"category": "호재_모맨텀", "keyword": "체결"},
    {"category": "호재_모맨텀", "keyword": "수주"},
    {"category": "호재_모맨텀", "keyword": "공급"},
    {"category": "호재_모맨텀", "keyword": "세계최초"},
    {"category": "호재_모맨텀", "keyword": "승인"},
    {"category": "호재_모맨텀", "keyword": "인수"},
    {"category": "호재_모맨텀", "keyword": "합병"},
    {"category": "호재_모맨텀", "keyword": "MOU"},
    {"category": "호재_모맨텀", "keyword": "개발 성공"},
    {"category": "악재_리스크", "keyword": "유상증자"},
    {"category": "악재_리스크", "keyword": "횡령"},
    {"category": "악재_리스크", "keyword": "배임"},
    {"category": "악재_리스크", "keyword": "적자지속"},
    {"category": "악재_리스크", "keyword": "거래정지"},
    {"category": "악재_리스크", "keyword": "압수수색"},
    {"category": "악재_리스크", "keyword": "불성실공시"},
    {"category": "실적_펀다맨탈", "keyword": "어닝서프라이즈"},
    {"category": "실적_펀다맨탈", "keyword": "사상 최대"},
    {"category": "실적_펀다맨탈", "keyword": "영업이익 급증"},
    {"category": "실적_펀다맨탈", "keyword": "매출증가"},
    {"category": "실적_펀다맨탈", "keyword": "흑자전환"},
    {"category": "실적_펀다맨탈", "keyword": "점유율 1위"},
    {"category": "가치_저평가", "keyword": "저평가"},
    {"category": "가치_저평가", "keyword": "저PBR"},
    {"category": "가치_저평가", "keyword": "기업가치 제고"},
    {"category": "가치_저평가", "keyword": "밸류업"},
    {"category": "가치_저평가", "keyword": "배당 확대"},
    {"category": "가치_저평가", "keyword": "자사주 소각"},
    {"category": "가치_저평가", "keyword": "주주환원"},
    {"category": "섹터_트렌드", "keyword": "HBM"},
    {"category": "섹터_트렌드", "keyword": "AI"},
    {"category": "섹터_트렌드", "keyword": "로봇"},
    {"category": "섹터_트렌드", "keyword": "자율주행"},
    {"category": "섹터_트렌드", "keyword": "2차전지"},
    {"category": "섹터_트렌드", "keyword": "양자컴퓨터"},
    {"category": "섹터_트렌드", "keyword": "우주항공"},
    {"category": "섹터_트렌드", "keyword": "특징주"},
]

VALUE_DATA = [
    "KB금융",
    "하나금융지주",
    "현대차",
    "기아",
    "POSCO홀딩스",
    "삼성물산",
    "KT&G",
    "기업은행",
    "DB손해보험",
    "우리금융지주",
]

STOP_WORD_DATA = [
    "대상",
    "동방",
    "국보",
    "보물",
    "서원",
    "가비",
    "나라",
    "서울",
    "지주",
    "신세계",
]


def seed_personas():
    db = next(get_db())
    try:
        for data in PERSONA_DATA:
            persona = db.get(Persona, data["id"])
            if not persona:
                db.add(Persona(**data))
                # SearchKeyword
        if db.query(SearchKeyword).count() == 0:
            for data in KEYWORD_DATA:
                db.add(SearchKeyword(**data))

        # ValueWatchlist
        if db.query(ValueWatchlist).count() == 0:
            for name in VALUE_DATA:
                db.add(ValueWatchlist(ticker_name=name))

        # StopWord
        if db.query(StopWord).count() == 0:
            for word in STOP_WORD_DATA:
                db.add(StopWord(word=word))

        db.commit()
        print("Persona 시드 완료")
    except Exception as e:
        db.rollback()
        print(f"시드 실패: {e}")


if __name__ == "__main__":
    seed_personas()
