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

# 환경 설정 및 API 로드
load_dotenv(dotenv_path='.env')

CONFIG = {
    "NAVER": {
        "CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "SECRET": os.getenv("NAVER_CLIENT_SECRET")
    },
    "GEMINI": {
        "API_KEY": os.getenv("GEMINI_API_KEY"),
        "MODEL": "gemini-2.5-flash"
    },
    "DART": {
        "API_KEY": os.getenv("DART_API_KEY")
    },
    "KIS": {
        "API_KEY": os.getenv("KIS_APP_KEY"),
        "API_SECRET": os.getenv("KIS_APP_SECRET"),
        "ACC_NO": os.getenv("KIS_ACC_NO"),
        "MOCK": True  # 모의투자 여부
    }
}

# 투자 성향별 페르소나 설정 (회원가입 시 결정될 투자 성향 반영)
PERSONA_CONFIG = {
    "1": {
        "name": "안정형",
        "weights": {
            "가치_저평가": 10.0, "실적_펀다맨탈": 2.0, "호재_모맨텀": 0.0, "악재_리스크": -20.0, "섹터_트렌드": 0.0
        },
        "gemini_persona": "원금을 절대 잃지 않는 보수적인 자산가",
        "criteria": "변동성이 극히 적고 배당수익률이 높은 방어주(통신, 금융, 지주사) 위주 선정. 뉴스보다는 PBR, 배당 성향 등 숫자가 기준.",
        "use_value_scout": True  # 뉴스가 없어도 재무 우량주 강제 발굴
    },
    "2": {
        "name": "안정추구형",
        "weights": {
            "가치_저평가": 5.0, "실적_펀다맨탈": 5.0, "호재_모맨텀": 1.0, "악재_리스크": -10.0, "섹터_트렌드": 1.0
        },
        "gemini_persona": "안정적인 성장을 추구하는 연기금 펀드매니저",
        "criteria": "재무가 탄탄하면서도 적당한 성장성이 있는 대형 우량주(Blue Chip). 저평가된 실적주를 선호.",
        "use_value_scout": True
    },
    "3": {
        "name": "위험중립형",
        "weights": {
            "가치_저평가": 2.0, "실적_펀다맨탈": 8.0, "호재_모맨텀": 3.0, "악재_리스크": -5.0, "섹터_트렌드": 3.0
        },
        "gemini_persona": "실적 기반의 정석 투자자",
        "criteria": "매출과 영업이익이 꾸준히 우상향하는 성장주. 산업의 트렌드를 따라가되, 실체가 없는 테마주는 배제.",
        "use_value_scout": False # 여기서부터는 뉴스/트렌드 비중 높임
    },
    "4": {
        "name": "적극투자형",
        "weights": {
            "가치_저평가": 0.0, "실적_펀다맨탈": 3.0, "호재_모맨텀": 7.0, "악재_리스크": -3.0, "섹터_트렌드": 5.0
        },
        "gemini_persona": "주도주에 올라타는 추세 추종 트레이더",
        "criteria": "현재 시장에서 가장 핫한 섹터(AI, 로봇 등)의 대장주. 신고가 갱신이나 거래량 급증 종목 적극 공략.",
        "use_value_scout": False
    },
    "5": {
        "name": "공격투자형",
        "weights": {
            "가치_저평가": -5.0, "실적_펀다맨탈": 0.0, "호재_모맨텀": 10.0, "악재_리스크": -1.0, "섹터_트렌드": 8.0
        },
        "gemini_persona": "상한가를 노리는 공격적인 스캘퍼",
        "criteria": "오늘 당장 이슈가 터진 급등주. 재무제표보다는 재료의 크기와 수급(거래량)이 최우선.",
        "use_value_scout": False
    }
}

# 데이터 탐색 키워드 및 필터
search_keywords = {
    "호재_모맨텀": ["체결", "수주", "공급", "세계최초", "승인", "인수", "합병", "MOU", "개발 성공"],
    "악재_리스크": ["유상증자", "횡령", "배임", "적자지속", "거래정지", "압수수색", "불성실공시"],
    "실적_펀다맨탈": ["어닝서프라이즈", "사상 최대", "영업이익 급증", "매출증가", "흑자전환", "점유율 1위"],
    "가치_저평가": ["저평가", "저PBR", "기업가치 제고", "밸류업", "배당 확대", "자사주 소각", "주주환원"],
    "섹터_트렌드": ["HBM", "AI", "로봇", "자율주행", "2차전지", "양자컴퓨터", "우주항공", "특징주"]
}

# 뉴스 없이도 체크할 가치주 리스트 (가치방어형 선택 시 작동)
VALUE_WATCHLIST = [
    "KB금융", "하나금융지주", "현대차", "기아", "POSCO홀딩스", 
    "삼성물산", "KT&G", "기업은행", "DB손해보험", "우리금융지주"
]

STOP_WORDS = {"대상", "동방", "국보", "보물", "서원", "가비", "나라", "서울", "지주", "신세계"}

# 데이터 수집 클래스
class financeDataCollector:
    def __init__(self, config):
        self.config = config
        
        # Geimini 연결
        try:
            self.gemini_client = genai.Client(api_key=config["GEMINI"]["API_KEY"])
        except Exception as e:
            print(f"⚠️ Gemini 연결 실패: {e}")

        # DART 연걸
        try:
            self.dart = OpenDartReader(config["DART"]["API_KEY"])
            print("✅ DART API 연결")
        except:
            self.dart = None

        # KIS 연결
        try:
            self.broker = mojito.KoreaInvestment(
               api_key=config["KIS"]["API_KEY"],
                api_secret=config["KIS"]["API_SECRET"],
                acc_no=config["KIS"]["ACC_NO"],
                mock=config["KIS"]["MOCK"]
            )
            print("✅ 한투(KIS) API 연결")
        except:
            self.broker = None

        # 종목 코드 매핑 로딩 (KOSPI 200 + KOSDAQ 150)
        try:
            # KOSPI 전체 불러오기 -> 시가총액(Marcap) 내림차순 정렬 -> 상위 200개
            df_kospi = fdr.StockListing('KOSPI')
            df_kospi200 = df_kospi.sort_values('Marcap', ascending=False).head(200)
            
            # KOSDAQ 전체 불러오기 -> 시가총액(Marcap) 내림차순 정렬 -> 상위 150개
            df_kosdaq = fdr.StockListing('KOSDAQ')
            df_kosdaq150 = df_kosdaq.sort_values('Marcap', ascending=False).head(150)
            
            # 3. 합치기
            df_total = pd.concat([df_kospi200, df_kosdaq150])
            
            self.stock_map = dict(zip(df_total['Name'], df_total['Code']))
            print(f"✅ 종목 리스트 로딩 완료: {len(self.stock_map)}개 (KOSPI 200 + KOSDAQ 150)\n")
            
        except Exception as e:
            print(f"종목 리스트 로딩 실패: {e}")
            self.stock_map = {}

    # HTML 태그 및 특수문자 제거
    def clean_html(self, raw_html):
        if not raw_html: return ""
        return re.sub('<.*?>|&quot;|&amp;|&lt;|&gt;', '', raw_html)

    # 네이버 뉴스 API로 뉴스 수집
    def fetch_naver_news(self, keyword):
        url = "https://openapi.naver.com/v1/search/news.json"

        headers = {
            "X-Naver-Client-Id": self.config["NAVER"]["CLIENT_ID"],
            "X-Naver-Client-Secret": self.config["NAVER"]["SECRET"]
        }

        params = {"query": keyword, "display": 10, "sort": "date"}
        
        try:
            resp = requests.get(url, headers=headers, params=params)
            return resp.json().get('items', []) if resp.status_code == 200 else []
        except:
            return []

    # 뉴스 제목과 설명에서 종목명과 코드 탐지 (최대 매칭 방식)
    def detect_stock_code(self, title, description):
        if not self.stock_map: return None, None

        target_text = f"{title} {description}"
        found_name, found_code = None, None
        
        for name, code in self.stock_map.items():
            if name in STOP_WORDS: continue 
            if name in target_text:
                if found_name is None or len(name) > len(found_name):
                    found_name = name
                    found_code = code
        return found_name, found_code

    # KIS API로 시세 및 재무 데이터 조회
    def get_market_data(self, stock_code):
        if not self.broker: return {"status": "Error", "msg": "KIS 미연결"}

        try:
            stock_code = stock_code.zfill(6) # 종목 코드가 6자리가 되도록 앞에 0 채우기
            resp = self.broker.fetch_price(stock_code)

            # 응답 값 확인을 위한 프린트 추가
            if resp.get('rt_cd') == '0': # 성공 시 '0' 반환
                print(f"✅ {stock_code} 조회 성공!")
                d = resp['output']
                return {
                    "price": d['stck_prpr'],
                    "change": d['prdy_ctrt'],
                    "volume": d['acml_vol'],
                    "per": d.get('per', 'N/A'),
                    "pbr": d.get('pbr', 'NA'),
                    "status": "Success"
                }
            else:
                # 실패 시 메시지 출력
                print(f"   ❌ {stock_code} 조회 실패: {resp.get('msg1')}")
                return {"status": "Error", "msg": resp.get('msg1')}
        except Exception as e:
            return {"status": "Error", "msg": str(e)}

    # DART API로 최근 공시 정보 조회 (최근 3개월)
    def get_dart_info(self, stock_name):
        if not self.dart: return "DART 미연결"

        try:
            end_dt = datetime.now().strftime('%Y%m%d')
            start_dt = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
            report = self.dart.list(corp=stock_name, start=start_dt, end=end_dt)

            if report is not None and not report.empty:
                return " | ".join(report['report_nm'].head(3).tolist())
            return "최근 3개월 공시 없음"
        except:
            return "DART 조회 실패"
    
    # KIS API로 계좌 잔고 및 예수금 조회
    def get_balance(self):
        if not self.broker: return None
        try:
            # 계좌 잔고 및 예수금 조회 API 호출
            resp = self.broker.fetch_balance()
            
            # 1. 응답 데이터가 정상적으로 왔는지 확인
            if resp and 'output2' in resp and len(resp['output2']) > 0:
                # d2_csh_ast_amt (D+2 예수금) 또는 nrciv_blce (미수 제외 예수금)
                # 모의투자와 실전투자에 따라 필드명이 다를 수 있어 안전하게 get 사용
                data = resp['output2'][0]
                deposit = int(data.get('nrciv_blce', data.get('dnca_tot_amt', 0)))
                return deposit
            return 0
        except Exception as e:
            print(f"⚠️ 계좌 조회 실패: {e}")
            return 0

# 뉴스 필터링 (점수 계산, 프롬프트 최적화)
def calculate_news_score(row, weight_map):
    score = 0
    text = (str(row['title']) + " " + str(row['description'])).replace(" ", "")
    
    # 1. 키워드 매칭 점수 (성향별 가중치 적용)
    for category, keywords in search_keywords.items():
        current_weight = weight_map.get(category, 0)
        for kw in keywords:
            if kw in text:
                score += current_weight
                
    # 2. 최신성 가산점 (모든 성향 공통)
    time_diff = (datetime.now() - row['pubDate_cle링an']).total_seconds()
    if time_diff < 3600 * 4: # 4시간 이내
        score += 3
        
    return score

# 프롬프트 최적화: 뉴스 기반 종목과 스카우터 종목을 구분하여 정보 제공
def optimize_prompt(df_news, scout_data, persona_conf):
    context_blocks = []
    
    # 뉴스 기반 발굴 종목
    news_grouped = df_news[df_news['stock_code'].notnull()].groupby('stock_code')
    for code, group in news_grouped:
        first = group.iloc[0]
        name = first['stock_name']
        m = first['market_data']
        d = first['dart_data']
        
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
        m = s['market_data']
        if m['status'] != 'Success': continue
        
        block = f"""
        [종목(스카우트): {s['name']}]
        1. 📰 이슈: 특이 뉴스 없음 (재무 스캔 발굴)
        2. 📊 시세: 현재가 {m.get('price')}원 (등락 {m.get('change')}%)
        3. 💰 밸류: PER {m.get('per')}, PBR {m.get('pbr')} (핵심 체크 포인트)
        """
        context_blocks.append(block)

    return "\n".join(context_blocks)

# Gemini API로 최적의 투자 포트폴리오 추천
def run_gemini(client, context, persona_conf, user_deposit=0):
    formatted_deposit = f"{user_deposit:,}원"

    prompt = f"""
    당신은 **{persona_conf['gemini_persona']}**입니다.

    [사용자 자산 현황]
    - 현재 매수 가능 금액(예수금): {formatted_deposit}

    [분석 데이터]
    {context}
황
    [임무]
    사용자의 자산({formatted_deposit})을 바탕으로 최적의 투자 포트폴리오 **Top5**을 추천하세요.
    추천 결과에는 각 종목에 대해 **전체 자산 대비 투자 비중(%)**과 **실제 매수 가능 수량**을 반드시 포함해야 합니다.
    
    **[제한 사항]:**
    1. 5개 종목의 투자 비중 합계는 100%가 넘지 않도록 하세요.
    2. 현금 보유 비중(약 5~10%)을 남겨두는 전략도 좋습니다.
    3. 주당 가격이 사용자의 잔고보다 비싼 종목은 절대 추천하지 마세요.
    4. 사용자의 자산 규모에 맞는 '가성비'와 '안정성'을 동시에 고려하세요.

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
            model=CONFIG["GEMINI"]["MODEL"], 
            contents=prompt
        )
        return resp.text
    except Exception as e:
        return f"Gemini Error: {e}"


# 메인 함수: 투자 성향에 따른 맞춤형 포트폴리오 추천
def get_ai_recommendation(choice: str):
    if choice not in PERSONA_CONFIG:
        choice = "2" # 기본값 안정추구형 (나중에 회원가입 시 선택된 성향으로 변경)
        
    p_conf = PERSONA_CONFIG[choice]
    collector = financeDataCollector(CONFIG)
    
    # 계좌 잔고 확인 (KIS 연결 실패 시 100만원 가정)
    user_cash = collector.get_balance()
    if user_cash is None:
        user_cash = 1000000 

    # [Step 1] 뉴스 수집
    all_news = []
    for _, keywords in search_keywords.items():
        for kw in keywords:
            all_news.extend(collector.fetch_naver_news(kw))
            
    if not all_news:
        return "현재 수집된 시장 데이터가 없어 분석을 진행할 수 없습니다."

    # 데이터프레임 처리
    df = pd.DataFrame(all_news)
    df['title'] = df['title'].apply(collector.clean_html)
    df['description'] = df['description'].apply(collector.clean_html)
    df['pubDate_clean'] = pd.to_datetime(df['pubDate']).dt.tz_localize(None)
    df.drop_duplicates(subset=['title'], keep='first', inplace=True)
    df['score'] = df.apply(lambda row: calculate_news_score(row, p_conf['weights']), axis=1)
    
    df_top = df.nlargest(15, 'score').copy()
    
    # [Step 2] 종목 식별 및 시세 조회
    df_top['stock_name'] = None
    df_top['stock_code'] = None
    df_top['market_data'] = None
    df_top['dart_data'] = None

    df_top = df_top.astype({'market_data': 'object', 'dart_data': 'object'})

    data_cache = {} # 조회 결과를 담을 캐시 딕셔너리

    # 뉴스 기반 종목 데이터 채우기
    for idx, row in df_top.iterrows():
        name, code = collector.detect_stock_code(row['title'], row['description'])
        
        df_top.at[idx, 'stock_name'] = name
        df_top.at[idx, 'stock_code'] = code
        
        # 캐시에 없는 새로운 종목인 경우에만 API 호출
        if code and code not in data_cache:
            m_data = collector.get_market_data(code)
            time.sleep(0.5)

            d_data = collector.get_dart_info(name)
            time.sleep(0.5)
            
            # 시세 조회가 성공했을 때만 캐시에 저장
            if m_data.get('status') == 'Success':
                data_cache[code] = {'market': m_data, 'dart': d_data}

            # 초당 거래건수 제한 방지
            time.sleep(0.7)

        # 캐시에서 데이터를 꺼내와서 데이터프레임에 할당 (에러 방지용)
        if code in data_cache:
            df_top.at[idx, 'market_data'] = data_cache[code].get('market', {})
            df_top.at[idx, 'dart_data'] = data_cache[code].get('dart', "데이터 없음")

    # [Step 3] 가치주 스카우팅
    scout_list = []
    if p_conf['use_value_scout']:
        for v_name in VALUE_WATCHLIST:
            v_code = collector.stock_map.get(v_name)
            if v_code:
                v_data = collector.get_market_data(v_code)
                if v_data.get('status') == 'Success':
                    scout_list.append({'name': v_name, 'market_data': v_data})

    # [Step 4] Gemini 분석
    final_context = optimize_prompt(df_top, scout_list, p_conf)
    report = run_gemini(collector.gemini_client, final_context, p_conf, user_cash)

    # 결과 저장 (csv 파일로 저장 -> )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    df_top.to_csv(f'stock_analysis_{choice}_{timestamp}.csv', index=False, encoding='utf-8-sig')

    return report