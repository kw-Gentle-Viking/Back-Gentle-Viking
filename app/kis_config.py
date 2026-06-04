import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")


def kis_is_mock() -> bool:
    return os.getenv("KIS_MOCK", "true").lower() in {"1", "true", "yes", "y"}


def kis_real_trading_enabled() -> bool:
    return os.getenv("KIS_REAL_TRADING_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def kis_ws_url() -> str:
    if kis_is_mock():
        return "ws://ops.koreainvestment.com:21000"
    return "ws://ops.koreainvestment.com:31000"


def kis_approval_url() -> str:
    if kis_is_mock():
        return "https://openapivts.koreainvestment.com:29443/oauth2/Approval"
    return "https://openapi.koreainvestment.com:9443/oauth2/Approval"
