import os
from typing import Optional, Tuple, List, Dict, Any
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# 환경변수에서 DB URL 로딩
MARKET_DB_URL = os.getenv(
    "MARKET_DB_URL", "postgresql://trader:traderpass@localhost:5433/market_data"
)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = os.getenv("CLICKHOUSE_PORT", "8123")

# SQLAlchemy 엔진 (market-db)
market_engine = create_engine(MARKET_DB_URL, pool_pre_ping=True)


async def get_market_data(
    symbol: str, start_date: str, end_date: str, timeframe: str = "1m"
) -> pd.DataFrame:
    """market-db에서 OHLCV 데이터 조회"""

    table_name = f"ohlcv_{timeframe}"

    query = text(
        f"""
        SELECT time, open, high, low, close, volume
        FROM {table_name}
        WHERE symbol = :symbol
          AND time >= :start_date
          AND time <= :end_date
        ORDER BY time
    """
    )

    try:
        df = pd.read_sql(
            query,
            market_engine,
            params={"symbol": symbol, "start_date": start_date, "end_date": end_date},
        )

        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time")

        return df
    except Exception as e:
        print(f"Error loading market data: {e}")
        return pd.DataFrame()


async def save_to_clickhouse(result) -> bool:
    """백테스트 결과를 ClickHouse에 저장"""
    try:
        import httpx

        url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}"

        query = f"""
            INSERT INTO backtest_results (
                id, strategy_name, symbol, start_date, end_date,
                initial_capital, final_equity, cumulative_return,
                sharpe_ratio, max_drawdown, calmar, volatility,
                total_trades, created_at
            ) VALUES (
                generateUUIDv4(),
                '{result.strategy}',
                '{result.symbol}',
                '{result.start_date}',
                '{result.end_date}',
                {result.initial_capital},
                {result.final_equity},
                {result.cumulative},
                {result.sharpe},
                {result.max_drawdown},
                {result.calmar},
                {result.volatility},
                {result.total_trades},
                now()
            )
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=query)
            return response.status_code == 200

    except Exception as e:
        print(f"Error saving to ClickHouse: {e}")
        return False


async def get_from_clickhouse(
    symbol: Optional[str], strategy: Optional[str], limit: int, offset: int
) -> Tuple[List[Dict[str, Any]], int]:
    """ClickHouse에서 백테스트 기록 조회"""
    try:
        import httpx

        url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}"

        where_clauses = []
        if symbol:
            where_clauses.append(f"symbol = '{symbol}'")
        if strategy:
            where_clauses.append(f"strategy_name = '{strategy}'")

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 결과 조회
        query = f"""
            SELECT *
            FROM backtest_results
            {where_sql}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
            FORMAT JSON
        """

        # 총 개수 조회
        count_query = f"""
            SELECT count() as total
            FROM backtest_results
            {where_sql}
            FORMAT JSON
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=query)
            count_response = await client.post(url, data=count_query)

            if response.status_code == 200:
                data = response.json()
                count_data = count_response.json()

                results = data.get("data", [])
                total = count_data.get("data", [{}])[0].get("total", 0)

                return results, total

        return [], 0

    except Exception as e:
        print(f"Error reading from ClickHouse: {e}")
        return [], 0


async def init_clickhouse_table():
    """ClickHouse 테이블 초기화"""
    try:
        import httpx

        url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}"

        create_table = """
            CREATE TABLE IF NOT EXISTS backtest_results (
                id UUID,
                strategy_name String,
                symbol String,
                start_date String,
                end_date String,
                initial_capital Float64,
                final_equity Float64,
                cumulative_return Float64,
                sharpe_ratio Float64,
                max_drawdown Float64,
                calmar Float64,
                volatility Float64,
                total_trades UInt32,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (strategy_name, symbol, created_at)
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=create_table)
            return response.status_code == 200

    except Exception as e:
        print(f"Error creating ClickHouse table: {e}")
        return False
