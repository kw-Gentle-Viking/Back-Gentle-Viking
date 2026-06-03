import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

router = APIRouter()

BASE_URL      = "https://openapivts.koreainvestment.com:29443"  # 모의투자
REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"        # 실전 (시세조회용)
APP_KEY    = os.getenv("KIS_APP_KEY", "")
APP_SECRET = os.getenv("KIS_APP_SECRET", "")

print(f"[KIS] .env 경로: {_env_path}")
print(f"[KIS] APP_KEY 로드 여부: {'OK' if APP_KEY else 'EMPTY'}")
_ACC_NO = os.getenv("KIS_ACC_NO", "")  # "50158327-01"
CANO, ACNT_PRDT_CD = (_ACC_NO.split("-") + ["01"])[:2]

# ── 토큰 캐시 (모의 / 실전 분리) ──────────────────────────────────────────────
_token_cache: dict      = {"token": None, "expires_at": None}
_real_token_cache: dict = {"token": None, "expires_at": None}


async def get_real_access_token() -> str:
    now = datetime.now()
    if _real_token_cache["token"] and _real_token_cache["expires_at"] and _real_token_cache["expires_at"] > now:
        return _real_token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{REAL_BASE_URL}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": APP_KEY,
                "appsecret": APP_SECRET,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"KIS 실전 토큰 발급 실패: {resp.text}")
        data = resp.json()
        _real_token_cache["token"] = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        _real_token_cache["expires_at"] = now + timedelta(seconds=expires_in - 60)
        return _real_token_cache["token"]


async def get_access_token() -> str:
    now = datetime.now()
    if _token_cache["token"] and _token_cache["expires_at"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": APP_KEY,
                "appsecret": APP_SECRET,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 실패: {resp.text}")
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        expires_in = int(data.get("expires_in", 86400))
        _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 60)
        return _token_cache["token"]


def _base_headers(token: str, tr_id: str) -> dict:
    return {
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
        "Content-Type": "application/json",
    }


def _date_range(range_key: str) -> tuple[str, str, str]:
    """(시작일 YYYYMMDD, 종료일 YYYYMMDD, 기간구분코드 D/W/M)
    거래일 기준 캔들 수:
      1D  → 약 20개 (달력 30일)
      1W  → 약 40개 (달력 60일)
      3M  → 약 65개 (달력 95일)
      1Y  → 약 52개 주봉 (달력 365일)
      5Y  → 약 60개 월봉 (달력 5년)
      ALL → 약 120개 월봉 (달력 10년)
    """
    today = datetime.now()
    end = today.strftime("%Y%m%d")
    mapping = {
        "1D":  (today - timedelta(days=30),     "D"),
        "1W":  (today - timedelta(days=60),     "D"),
        "3M":  (today - timedelta(days=95),     "D"),
        "1Y":  (today - timedelta(days=365),    "W"),
        "5Y":  (today - timedelta(days=365*5),  "M"),
        "ALL": (today - timedelta(days=365*10), "M"),
    }
    start_dt, period = mapping.get(range_key, (today - timedelta(days=95), "D"))
    return start_dt.strftime("%Y%m%d"), end, period


# ── 현재가 조회 ───────────────────────────────────────────────────────────────
# GET /prices/current?code=005930
# KIS: GET /uapi/domestic-stock/v1/quotations/inquire-price
#      tr_id: VHKST01010100 (모의)
@router.get("/prices/current")
async def get_current_price(code: str):
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=_base_headers(token, "VHKST01010100"),
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── 일별 차트 데이터 조회 ──────────────────────────────────────────────────────
# GET /prices/chart?code=005930&range=3M
# KIS: GET /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
#      tr_id: FHKST03010100
@router.get("/prices/chart")
async def get_chart(code: str, range: str = "3M"):
    token = await get_access_token()
    start, end, period = _date_range(range)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            headers=_base_headers(token, "FHKST03010100"),
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": start,
                "FID_INPUT_DATE_2": end,
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "0",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── 분봉(당일 intraday) 차트 조회 ────────────────────────────────────────────
# GET /prices/intraday?code=005930
# KIS: GET /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice
#      tr_id: FHKST03010200
#      1회 30건 반환 → 전체 거래일(09:00~15:30) 커버까지 최대 13회 반복 호출
@router.get("/prices/intraday")
async def get_intraday(code: str):
    token = await get_access_token()
    now = datetime.now()

    # 장중이면 현재 시각, 마감 후면 153000 기준
    current_hms = now.strftime("%H%M%S")
    reference_time = current_hms if "090000" <= current_hms <= "153000" else "153000"

    all_items: list = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(13):
            resp = await client.get(
                f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                headers=_base_headers(token, "FHKST03010200"),
                params={
                    "FID_ETC_CLS_CODE": "",
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": code,
                    "FID_INPUT_HOUR_1": reference_time,
                    "FID_PW_DATA_INCU_YN": "N",  # 당일 데이터만
                },
            )
            if resp.status_code != 200:
                break

            data = resp.json()
            if data.get("rt_cd") != "0" or not data.get("output2"):
                break

            items = data["output2"]
            all_items.extend(items)

            last_time = items[-1].get("stck_cntg_hour", "")
            if not last_time or last_time <= "090000":
                break

            reference_time = last_time  # 다음 페이지: 마지막 시각 기준으로 더 과거 조회

    return {"rt_cd": "0", "msg1": "", "output2": all_items}


# ── 현금 매수/매도 주문 ───────────────────────────────────────────────────────
# POST /trade/order
# KIS: POST /uapi/domestic-stock/v1/trading/order-cash
#      tr_id: VTTC0012U (매수 모의), VTTC0011U (매도 모의)
class OrderBody(BaseModel):
    code: str
    side: str        # "buy" | "sell"
    qty: int
    price: int       # 시장가는 0
    price_type: str  # "limit" | "market"


@router.post("/trade/order")
async def place_order(body: OrderBody):
    token = await get_access_token()
    tr_id = "VTTC0012U" if body.side == "buy" else "VTTC0011U"
    ord_dvsn = "01" if body.price_type == "market" else "00"  # 01=시장가, 00=지정가
    ord_unpr = "0" if body.price_type == "market" else str(body.price)

    payload = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": body.code,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(body.qty),
        "ORD_UNPR": ord_unpr,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
            headers=_base_headers(token, tr_id),
            json=payload,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ── 시장 지수 / 환율 개요 ─────────────────────────────────────────────────────
# GET /market/overview
# KIS:
#   KOSPI/KOSDAQ: GET /uapi/domestic-stock/v1/quotations/inquire-index-price
#                 tr_id: FHPUP02100000  FID_COND_MRKT_DIV_CODE=U
#                 FID_INPUT_ISCD: 0001(코스피) / 1001(코스닥)
#   달러환율:     GET /uapi/domestic-stock/v1/quotations/inquire-price
#                 tr_id: FHKST01010100  FID_COND_MRKT_DIV_CODE=X  FID_INPUT_ISCD=USD
@router.get("/market/overview")
async def get_market_overview():
    token = await get_real_access_token()

    async def fetch_index(iscd: str):
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{REAL_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": APP_KEY,
                    "appsecret": APP_SECRET,
                    "tr_id": "FHPUP02100000",
                    "Content-Type": "application/json",
                },
                params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": iscd},
            )

    async def fetch_fx():
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{REAL_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": APP_KEY,
                    "appsecret": APP_SECRET,
                    "tr_id": "FHKST01010100",
                    "Content-Type": "application/json",
                },
                params={"FID_COND_MRKT_DIV_CODE": "X", "FID_INPUT_ISCD": "USD"},
            )

    kospi_resp, kosdaq_resp, fx_resp = await asyncio.gather(
        fetch_index("0001"),
        fetch_index("1001"),
        fetch_fx(),
    )

    return {
        "kospi":  kospi_resp.json()  if kospi_resp.status_code  == 200 else None,
        "kosdaq": kosdaq_resp.json() if kosdaq_resp.status_code == 200 else None,
        "usd":    fx_resp.json()     if fx_resp.status_code     == 200 else None,
    }


# ── 실시간 거래량 순위 ────────────────────────────────────────────────────────
# GET /market/volume-rank
# KIS: GET /uapi/domestic-stock/v1/quotations/volume-rank  (실전 도메인)
#      tr_id: FHPST01710000
@router.get("/market/volume-rank")
async def get_volume_rank():
    token = await get_real_access_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{REAL_BASE_URL}/uapi/domestic-stock/v1/quotations/volume-rank",
            headers={
                "authorization": f"Bearer {token}",
                "appkey": APP_KEY,
                "appsecret": APP_SECRET,
                "tr_id": "FHPST01710000",
                "Content-Type": "application/json",
            },
            params={
                "FID_COND_MRKT_DIV_CODE":  "J",
                "FID_COND_SCR_DIV_CODE":   "20171",
                "FID_INPUT_ISCD":          "0000",   # 전체 종목
                "FID_DIV_CLS_CODE":        "0",
                "FID_BLNG_CLS_CODE":       "0",
                "FID_TRGT_CLS_CODE":       "111111111",
                "FID_TRGT_EXLS_CLS_CODE":  "000000",
                "FID_INPUT_PRICE_1":       "0",
                "FID_INPUT_PRICE_2":       "0",
                "FID_VOL_CNT":             "100000",
                "FID_INPUT_DATE_1":        "",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
