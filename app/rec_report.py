import os
import re
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
import OpenDartReader
import mojito
import FinanceDataReader as fdr

from sqlalchemy.orm import Session
from app.models import (
    Persona,
    SearchKeyword,
    ValueWatchlist,
    StopWord,
    RecommendationReport,
)


# 환경 설정 및 API 로드
load_dotenv(dotenv_path=".env")

CONFIG = {
    "NAVER": {
        "CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "SECRET": os.getenv("NAVER_CLIENT_SECRET"),
    },
    "GEMINI": {"API_KEY": os.getenv("GEMINI_API_KEY"), "MODEL": "gemini-2.5-flash"},
    "DART": {"API_KEY": os.getenv("DART_API_KEY")},
    "KIS": {
        "API_KEY": os.getenv("KIS_APP_KEY"),
        "API_SECRET": os.getenv("KIS_APP_SECRET"),
        "ACC_NO": os.getenv("KIS_ACC_NO"),
        "MOCK": True,  # 모의투자 여부
    },
}

# 투자 성향별 페르소나 설정 (회원가입 시 결정될 투자 성향 반영)


def get_persona_config(db: Session, persona_id: int) -> dict:
    persona = db.get(Persona, persona_id)
    if not persona:
        persona = db.get(Persona, 2)  # 기본값 : 안정추구형
    return {
        "name": persona.name,
        "gemini_persona": persona.gemini_persona,
        "criteria": persona.criteria,
        "weights": persona.weights,
        "use_value_scout": persona.use_value_scout,
    }


def get_search_keywords(db: Session) -> dict:
    """카테고리별 키워드 딕셔너리 반환"""
    rows = db.query(SearchKeyword).all()
    result = {}
    for row in rows:
        result.setdefault(row.category, []).append(row.keyword)
    return result


def get_value_watchlist(db: Session) -> list[str]:
    """가치주 watchlist 반환"""
    rows = db.query(ValueWatchlist).all()
    return [row.ticker_name for row in rows]


def get_stop_words(db: Session) -> set[str]:
    """종목명 오탐 방지 단어 반환"""
    rows = db.query(StopWord).all()
    return {row.word for row in rows}


def save_report(db: Session, user_id: int, persona_id: int, report: str):
    """추천 결과 DB 저장"""
    db.add(
        RecommendationReport(
            user_id=user_id,
            persona_id=persona_id,
            report=report,
        )
    )
    db.commit()


# 데이터 수집 클래스
class financeDataCollector:
    def __init__(self, config, stop_words: set):
        self.config = config
        self.stop_words = stop_words
        # Geimini 연결
        try:
            self.gemini_client = genai.Client(api_key=config["GEMINI"]["API_KEY"])
            print("Gemini API 연결")
        except Exception as e:
            print(f"Gemini 연결 실패: {e}")

        # DART 연걸
        try:
            self.dart = OpenDartReader(config["DART"]["API_KEY"])
            print("DART API 연결")
        except:
            self.dart = None

        # KIS 연결
        try:
            self.broker = mojito.KoreaInvestment(
                api_key=config["KIS"]["API_KEY"],
                api_secret=config["KIS"]["API_SECRET"],
                acc_no=config["KIS"]["ACC_NO"],
                mock=config["KIS"]["MOCK"],
            )
            print("한투(KIS) API 연결")
        except Exception as e:
            print(f"한투(KIS) API 연결 실패 : {e}")
            self.broker = None

        # 종목 코드 매핑 로딩 (KOSPI 200 + KOSDAQ 150)
        # ip 차단 이슈?로 인해 KRX에서 직접 다운로드하는 방식으로 변경 (현재는 전체 종목 로딩)
        # 추후 확인 후 다시 라이브러리 사용 검토 예정 (코스피 200 + 코스닥 150 제한도 이때 다시 검토)
        try:
            # # KOSPI 전체 불러오기 -> 시가총액(Marcap) 내림차순 정렬 -> 상위 200개
            # df_kospi = fdr.StockListing('KOSPI')
            # df_kospi200 = df_kospi.sort_values('Marcap', ascending=False).head(200)

            # # KOSDAQ 전체 불러오기 -> 시가총액(Marcap) 내림차순 정렬 -> 상위 150개
            # df_kosdaq = fdr.StockListing('KOSDAQ')
            # df_kosdaq150 = df_kosdaq.sort_values('Marcap', ascending=False).head(150)

            # # 3. 합치기
            # df_total = pd.concat([df_kospi200, df_kosdaq150])

            # self.stock_map = dict(zip(df_total['Name'], df_total['Code']))
            # print(f"종목 리스트 로딩 완료: {len(self.stock_map)}개 (KOSPI 200 + KOSDAQ 150)\n")

            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://kind.krx.co.kr/corpgeneral/corpList.do?method=loadInitPage",
            }

            # KRX 상장종목 엑셀 다운로드 URL
            url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"

            # 직접 GET 요청
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                import io

                # 엑셀(HTML table) 데이터를 데이터프레임으로 변환
                df_all = pd.read_html(io.BytesIO(resp.content), header=0)[0]

                # 종목코드 6자리 포맷팅 (
                df_all["종목코드"] = df_all["종목코드"].astype(str).str.zfill(6)

                self.stock_map = dict(zip(df_all["회사명"], df_all["종목코드"]))
                print(f"종목 로딩 성공: {len(self.stock_map)}개")

                # df_all.to_csv('stock_list_backup.csv', index=False, encoding='utf-8-sig')
            else:
                raise Exception(f"서버 응답 에러: {resp.status_code}")

        except Exception as e:
            print(f"종목 리스트 로딩 실패: {e}")
            self.stock_map = {}

    # HTML 태그 및 특수문자 제거
    def clean_html(self, raw_html):
        if not raw_html:
            return ""
        return re.sub("<.*?>|&quot;|&amp;|&lt;|&gt;", "", raw_html)

    # 네이버 뉴스 API로 뉴스 수집
    def fetch_naver_news(self, keyword):
        url = "https://openapi.naver.com/v1/search/news.json"

        headers = {
            "X-Naver-Client-Id": self.config["NAVER"]["CLIENT_ID"],
            "X-Naver-Client-Secret": self.config["NAVER"]["SECRET"],
        }

        params = {"query": keyword, "display": 10, "sort": "date"}

        try:
            resp = requests.get(url, headers=headers, params=params)
            return resp.json().get("items", []) if resp.status_code == 200 else []
        except:
            return []

    # 뉴스 제목과 설명에서 종목명과 코드 탐지 (최대 매칭 방식)
    def detect_stock_code(self, title, description):
        if not self.stock_map:
            return None, None

        target_text = f"{title} {description}"
        found_name, found_code = None, None

        for name, code in self.stock_map.items():
            if name in self.stop_words:
                continue
            if name in target_text:
                if found_name is None or len(name) > len(found_name):
                    found_name = name
                    found_code = code
        return found_name, found_code

    # KIS API로 시세 및 재무 데이터 조회
    def get_market_data(self, stock_code):
        if not self.broker:
            return {"status": "Error", "msg": "KIS 미연결"}

        try:
            stock_code = stock_code.zfill(6)  # 종목 코드가 6자리가 되도록 앞에 0 채우기
            resp = self.broker.fetch_price(stock_code)

            # 응답 값 확인을 위한 프린트 추가
            if resp.get("rt_cd") == "0":  # 성공 시 '0' 반환
                print(f"{stock_code} 조회 성공!")
                d = resp["output"]
                return {
                    "price": d["stck_prpr"],
                    "change": d["prdy_ctrt"],
                    "volume": d["acml_vol"],
                    "per": d.get("per", "N/A"),
                    "pbr": d.get("pbr", "NA"),
                    "status": "Success",
                }
            else:
                # 실패 시 메시지 출력
                print(f"{stock_code} 조회 실패: {resp.get('msg1')}")
                return {"status": "Error", "msg": resp.get("msg1")}
        except Exception as e:
            return {"status": "Error", "msg": str(e)}

    # DART API로 최근 공시 정보 조회 (최근 3개월)
    def get_dart_info(self, stock_name):
        if not self.dart:
            return "DART 미연결"

        try:
            end_dt = datetime.now().strftime("%Y%m%d")
            start_dt = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
            report = self.dart.list(corp=stock_name, start=start_dt, end=end_dt)

            if report is not None and not report.empty:
                return " | ".join(report["report_nm"].head(3).tolist())
            return "최근 3개월 공시 없음"
        except:
            return "DART 조회 실패"

    # KIS API로 계좌 잔고 및 예수금 조회
    def get_balance(self):
        if not self.broker:
            return None
        try:
            # 계좌 잔고 및 예수금 조회 API 호출
            resp = self.broker.fetch_balance()

            # 1. 응답 데이터가 정상적으로 왔는지 확인
            if resp and "output2" in resp and len(resp["output2"]) > 0:
                # d2_csh_ast_amt (D+2 예수금) 또는 nrciv_blce (미수 제외 예수금)
                # 모의투자와 실전투자에 따라 필드명이 다를 수 있어 안전하게 get 사용
                data = resp["output2"][0]
                deposit = int(data.get("nrciv_blce", data.get("dnca_tot_amt", 0)))
                return deposit
            return 0
        except Exception as e:
            print(f"계좌 조회 실패: {e}")
            return 0

    # 시장 매크로 이슈 수집 (뉴스 키워드 기반)
    def fetch_macro(self):
        macro_keywords = ["전쟁", "금리", "환율", "유가", "원자재", "GDP", "실업률"]
        macro_news = []

        for kw in macro_keywords:
            news = self.fetch_naver_news(kw)
            if news:
                for item in news[:5]:  # 각 키워드당 최대 5개 뉴스만 처리
                    clean_title = self.clean_html(item["title"])
                    macro_news.append(clean_title)
            time.sleep(0.1)

        return " | ".join(set(macro_news))  # 중복 제거 후 연결


# 뉴스 필터링 (점수 계산, 프롬프트 최적화)
def calculate_news_score(row, weight_map, search_keywords):
    score = 0
    text = (str(row["title"]) + " " + str(row["description"])).replace(" ", "")

    # 1. 키워드 매칭 점수 (성향별 가중치 적용)
    for category, keywords in search_keywords.items():
        current_weight = weight_map.get(category, 0)
        for kw in keywords:
            if kw in text:
                score += current_weight

    # 2. 최신성 가산점 (모든 성향 공통)
    time_diff = (datetime.now() - row["pubDate_clean"]).total_seconds()
    if time_diff < 3600 * 4:  # 4시간 이내
        score += 3

    return score


# 프롬프트 최적화: 뉴스 기반 종목과 스카우터 종목을 구분하여 정보 제공
def optimize_prompt(df_news, scout_data, persona_conf):
    context_blocks = []

    # 뉴스 기반 발굴 종목
    news_grouped = df_news[df_news["stock_code"].notnull()].groupby("stock_code")
    for code, group in news_grouped:
        first = group.iloc[0]
        name = first["stock_name"]
        m = first["market_data"]
        d = first["dart_data"]

        # None 체크 추가
        if not m or m.get("status") != "Success":
            continue

        titles = "\n".join([f"- {row['title']}" for _, row in group.iterrows()])
        m_txt = f"현재가: {m.get('price')}원 (등락: {m.get('change')}%) / 거래량: {m.get('volume')}"
        val_txt = f"PER: {m.get('per')}, PBR: {m.get('pbr')}"

        block = f"""
        [종목(뉴스기반): {name}]
        1. 📰 이슈: {titles}
        2. 📊 시세: {m_txt}
        3. 💰 밸류: {val_txt}
        4. 📜 공시: {d}
        """
        context_blocks.append(block)

    # 스카우터 발굴 종목 (가치형일 때만 존재)
    for s in scout_data:
        m = s["market_data"]
        if m["status"] != "Success":
            continue

        block = f"""
        [종목(스카우트): {s['name']}]
        1. 📰 이슈: 특이 뉴스 없음 (재무 스캔 발굴)
        2. 📊 시세: 현재가 {m.get('price')}원 (등락 {m.get('change')}%)
        3. 💰 밸류: PER {m.get('per')}, PBR {m.get('pbr')} (핵심 체크 포인트)
        """
        context_blocks.append(block)

    return "\n".join(context_blocks)


# Gemini API로 최적의 투자 포트폴리오 추천
def run_gemini(client, context, market_context, persona_conf, user_deposit=0):
    formatted_deposit = f"{user_deposit:,}원"

    prompt = f"""
    당신은 **{persona_conf['gemini_persona']}**입니다.

    [현재 시장 전체 상황 (Macro Context)]
    : {market_context}

    [사용자 자산 현황 (예수금)]
    : {formatted_deposit}

    [분석 데이터]
    : {context}

    [임무]
    현재 시장 상황({market_context})을 고려하여, 사용자의 자산{formatted_deposit}을 바탕으로 최적의 투자 포트폴리오 Top5을 추천하세요.
    추천 결과에는 각 종목에 대해 **전체 자산 대비 투자 비중(%)**과 **실제 매수 가능 수량**을 반드시 포함해야 합니다.
    
    **[제한 사항]:**
    1. 5개 종목의 투자 비중 합계는 100%가 넘지 않도록 하세요.
    2. 현금 보유 비중(약 5~10%)을 남겨두는 전략도 좋습니다.
    3. 주당 가격이 사용자의 잔고보다 비싼 종목은 절대 추천하지 마세요.
    4. 사용자의 자산 규모에 맞는 '가성비'와 '안정성'을 동시에 고려하세요.

    **[전쟁 및 특수 상황 대응 지침]:**
    1. 시장이 불안정(전쟁, 유가 급등 등)하다면 보수적인 관점에서 '방어주'나 '안전자산 성격의 종목' 비중을 높이세요.
    2. 공격적인 페르소나라도 시장 급락기에는 무리한 풀매수보다 현금 비중(20~30%) 확보를 권장하세요.
    3. 거시 상황과 개별 종목의 재료가 상충할 경우(예: 전쟁 중인데 테마주 호재), 리스크 관점에서의 의견을 반드시 덧붙이세요.

    **[당신의 종목 선정 기준]:**
    "{persona_conf['criteria']}"

    **[작성 원칙]**
    1. 추천 사유는 반드시 **데이터(뉴스재료, PER/PBR, 거래량)**에 근거해야 합니다.
    2. 당신의 성향에 맞지 않는 종목(예: 가치투자자인데 급등 테마주)은 과감히 제외하세요.
    3. 뉴스에 종목명이 없더라도 내용을 보고 수혜주를 추론하세요.

    [출력 양식]
    ## 🏆 {persona_conf['name']}의 맞춤형 포트폴리오
    ## 💰 총 투자 가능 금액:** {formatted_deposit}

    ### 1. [종목명] (현재가 / 등락률)
    * **🎯 선정 이유:** (당신의 페르소나 관점에서 분석)
    * **📋 핵심 데이터:**
        * {'밸류에이션' if '가치' in persona_conf['name'] else '재료/수급'}: (PER/PBR 또는 뉴스/거래량 분석)
        * 리스크: (주의할 점)
    * **📊 매수 가이드:**
        - **권장 투자 금액:** 약 000,000원
        - **권장 매수 수량:** 약 0주 (현재가 기준 계산)
    * **📈 전략:** (매수 / 관망 / 비중확대)

    ---
    """
    try:
        resp = client.models.generate_content(
            model=CONFIG["GEMINI"]["MODEL"], contents=prompt
        )
        return resp.text
    except Exception as e:
        return f"Gemini Error: {e}"


# 메인 함수: 투자 성향에 따른 맞춤형 포트폴리오 추천 / db버전
def get_ai_recommendation(db: Session, user_id: int, persona_id: int) -> str:
    # DB에서 전부 가져오기
    p_conf = get_persona_config(db, persona_id)
    search_keywords = get_search_keywords(db)
    value_watchlist = get_value_watchlist(db)
    stop_words = get_stop_words(db)

    collector = financeDataCollector(CONFIG, stop_words)

    market_status = collector.fetch_macro()

    user_cash = collector.get_balance()
    if not user_cash:
        user_cash = 1_000_000

    # [Step 1] 뉴스 수집
    all_news = []
    for _, keywords in search_keywords.items():
        for kw in keywords:
            all_news.extend(collector.fetch_naver_news(kw))

    if not all_news:
        return "현재 수집된 시장 데이터가 없어 분석을 진행할 수 없습니다."

    # 데이터프레임 처리
    df = pd.DataFrame(all_news)
    df["title"] = df["title"].apply(collector.clean_html)
    df["description"] = df["description"].apply(collector.clean_html)
    df["pubDate_clean"] = pd.to_datetime(df["pubDate"]).dt.tz_localize(None)
    df.drop_duplicates(subset=["title"], keep="first", inplace=True)
    df["score"] = df.apply(
        lambda row: calculate_news_score(row, p_conf["weights"], search_keywords),
        axis=1,
    )
    df_top = df.nlargest(15, "score").copy()

    # [Step 2] 종목 식별 및 시세 조회
    df_top["stock_name"] = None
    df_top["stock_code"] = None
    df_top["market_data"] = None
    df_top["dart_data"] = None
    df_top = df_top.astype({"market_data": "object", "dart_data": "object"})

    data_cache = {}

    for idx, row in df_top.iterrows():
        name, code = collector.detect_stock_code(row["title"], row["description"])
        df_top.at[idx, "stock_name"] = name
        df_top.at[idx, "stock_code"] = code

        if code and code not in data_cache:
            m_data = collector.get_market_data(code)
            time.sleep(0.5)
            d_data = collector.get_dart_info(name)
            time.sleep(0.5)
            if m_data.get("status") == "Success":
                data_cache[code] = {"market": m_data, "dart": d_data}
            time.sleep(0.7)

        if code in data_cache:
            df_top.at[idx, "market_data"] = data_cache[code].get("market", {})
            df_top.at[idx, "dart_data"] = data_cache[code].get("dart", "데이터 없음")

    # [Step 3] 가치주 스카우팅
    scout_list = []
    if p_conf["use_value_scout"]:
        for v_name in value_watchlist:
            v_code = collector.stock_map.get(v_name)
            if v_code:
                v_data = collector.get_market_data(v_code)
                if v_data.get("status") == "Success":
                    scout_list.append({"name": v_name, "market_data": v_data})

    # [Step 4] Gemini 분석
    final_context = optimize_prompt(df_top, scout_list, p_conf)
    report = run_gemini(
        collector.gemini_client, final_context, market_status, p_conf, user_cash
    )

    # [Step 5] 결과 DB 저장
    save_report(db, user_id=user_id, persona_id=persona_id, report=report)

    return report
