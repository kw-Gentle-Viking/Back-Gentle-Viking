from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import  datetime

class BacktestRequest(BaseModel) :
    symbol : str 
    startegty : str =""
    start_date: str 
    end_date : str 

    # 초기자본
    initial_capital : float = 10000.0 
    
    # 최대 로스 컷 
    max_drawdown: float = 0.08

class TradeRecord(BaseModel):
    ts: datetime
    symbol: str
    side: str
    qty: float
    price: float
    fee: float
    is_maker: bool

class BacktestResponse(BaseModel):
    # 성과 지표
    '''
    총 수익률 log return? 
    위험 대비 수익 
    연환산 변동성
    최대낙폭 (고점 대비 최대 손실)
    수익/최대 낙폭 비율 
    '''
    cumulative : float
    shrape : float 
    volatility : float 
    max_drawdown: float
    calmar : float


    # 메타 정보
    symbol: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    
    # 상세 데이터 (선택)
    equity_curve: Optional[List[Dict[str, Any]]] = None
    trades: Optional[List[TradeRecord]] = None

class BacktestListResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int