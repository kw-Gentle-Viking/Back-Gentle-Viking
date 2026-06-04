# app/kis_websocket.py
import json
import asyncio
import websockets
import requests
from typing import Callable
from collections import defaultdict

from app.kis_config import kis_approval_url, kis_ws_url


class KISWebSocket:
    """KIS 실시간 시세 웹소켓"""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.ws_url = kis_ws_url()
        self.approval_url = kis_approval_url()
        self.approval_key = None
        self.ws = None
        self.prices: dict[str, dict] = {}  # ticker -> {price, volume, ...}
        self.callbacks: list[Callable] = []
        self._running = False

    def _get_approval_key(self) -> str:
        """웹소켓 접속키 발급"""
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }
        resp = requests.post(self.approval_url, json=body)
        resp.raise_for_status()
        return resp.json()["approval_key"]

    def _build_subscribe_msg(self, ticker: str) -> str:
        """종목 구독 메시지 생성"""
        return json.dumps({
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1",  # 1: 등록, 2: 해제
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0",  # 실시간 체결가
                    "tr_key": ticker,
                }
            }
        })

    def _parse_price_data(self, data: str) -> dict:
        """실시간 체결 데이터 파싱"""
        fields = data.split("|")
        if len(fields) < 4:
            return None

        # 3번째 필드가 데이터
        raw = fields[3].split("^")
        if len(raw) < 20:
            return None

        return {
            "ticker": raw[0],       # 종목코드
            "price": int(raw[2]),    # 현재가
            "change": float(raw[4]), # 등락률
            "volume": int(raw[12]),  # 누적거래량
            "high": int(raw[8]),     # 고가
            "low": int(raw[9]),      # 저가
            "time": raw[1],          # 체결시간
        }

    def on_price(self, callback: Callable):
        """가격 업데이트 콜백 등록"""
        self.callbacks.append(callback)

    async def connect(self, tickers: list[str]):
        """웹소켓 연결 + 종목 구독"""
        self.approval_key = self._get_approval_key()
        print(f"웹소켓 접속키 발급 완료")

        self._running = True

        async with websockets.connect(self.ws_url, ping_interval=30) as ws:
            self.ws = ws
            print(f"웹소켓 연결 완료")

            # 종목 구독
            for ticker in tickers:
                await ws.send(self._build_subscribe_msg(ticker))
                print(f"{ticker} 구독 등록")
                await asyncio.sleep(0.5)

            # 실시간 수신 루프
            while self._running:
                try:
                    data = await asyncio.wait_for(ws.recv(), timeout=60)

                    if data[0] == "0" or data[0] == "1":
                        parsed = self._parse_price_data(data)
                        if parsed:
                            self.prices[parsed["ticker"]] = parsed

                            for cb in self.callbacks:
                                await cb(parsed)

                except asyncio.TimeoutError:
                    print("웹소켓 대기 중...")
                    continue
                except websockets.ConnectionClosed:
                    print("웹소켓 연결 끊김 → 재연결 시도")
                    break

    async def disconnect(self):
        """웹소켓 종료"""
        self._running = False
        if self.ws:
            await self.ws.close()
            print("웹소켓 종료")

    def get_price(self, ticker: str) -> dict:
        """최신 시세 조회 (캐시)"""
        return self.prices.get(ticker, None)