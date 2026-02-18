from __future__ import annotations
from typing import Dict
import pandas as pd
import os
import math


class OnlineZScore:
    """EWMA 기반 온라인 Z-Score 계산"""
    
    def __init__(self, alpha: float = 0.1, eps: float = 1e-9):
        self.alpha = alpha
        self.eps = eps
        self.m = None
        self.v = None

    def update(self, x: float) -> float:
        if x is None or not math.isfinite(float(x)):
            return 0.0
        if self.m is None:
            self.m, self.v = float(x), 0.0
            return 0.0
        diff = float(x) - self.m
        self.m = (1 - self.alpha) * self.m + self.alpha * float(x)
        self.v = (1 - self.alpha) * self.v + self.alpha * (diff * diff)
        s = math.sqrt(max(self.v, self.eps))
        return diff / (s + self.eps)


def map_key_to_tf(key: str) -> str:
    """파일명에서 타임프레임 추출"""
    key = key.lower().replace(".csv", "").strip()
    if key.endswith(" 1"):
        return "1m"
    if key.endswith(" 3"):
        return "3m"
    if key.endswith(" 5"):
        return "5m"
    if key.endswith(" 15"):
        return "15m"
    if key.endswith(" 30"):
        return "30m"
    if key.endswith(" 60"):
        return "60m"
    if key.endswith(" 240"):
        return "240m"
    if key.endswith(" d"):
        return "1d"
    if key.endswith(" w"):
        return "1w"
    return None


def load_csv_folder(folder_path: str) -> Dict[str, pd.DataFrame]:
    """폴더에서 모든 CSV 파일 로딩"""
    csv_dataframes: Dict[str, pd.DataFrame] = {}
    
    for file_name in os.listdir(folder_path):
        if not file_name.lower().endswith(".csv"):
            continue
        full_path = os.path.join(folder_path, file_name)
        try:
            df = pd.read_csv(full_path)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.set_index("Date")
            csv_dataframes[file_name] = df
        except Exception as e:
            print(f"Error loading {file_name}: {e}")
    
    return csv_dataframes


# Technical Analysis 함수들
def ta_ema(df: pd.DataFrame, n: int, col: str = "close") -> pd.Series:
    """Exponential Moving Average"""
    return df[col].ewm(span=n, adjust=False).mean()


def ta_sma(df: pd.DataFrame, n: int, col: str = "close") -> pd.Series:
    """Simple Moving Average"""
    return df[col].rolling(window=n).mean()


def ta_rsi(df: pd.DataFrame, n: int = 14, col: str = "close") -> pd.Series:
    """Relative Strength Index"""
    delta = df[col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def ta_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, col: str = "close") -> pd.DataFrame:
    """MACD"""
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    
    return pd.DataFrame({
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist
    }, index=df.index)


def ta_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range"""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.rolling(window=period).mean()


def ta_bollinger(df: pd.DataFrame, n: int = 20, std: float = 2.0, col: str = "close") -> pd.DataFrame:
    """Bollinger Bands"""
    sma = df[col].rolling(window=n).mean()
    std_dev = df[col].rolling(window=n).std()
    
    return pd.DataFrame({
        "bb_upper": sma + std * std_dev,
        "bb_middle": sma,
        "bb_lower": sma - std * std_dev
    }, index=df.index)
