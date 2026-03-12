"""
CSV 데이터를 market-db에 적재하는 스크립트

사용법:
    python -m market.load_market_data --file data.csv --table price_min_01
    python -m market.load_market_data --folder ./data --table price_min_01
"""

import argparse
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from market.db_market import market_engine, init_market_schema


def load_csv_to_db(
    file_path: str, table_name: str, schema: str = "raw", chunk_size: int = 50000
):
    """
    CSV 파일을 DB에 적재

    Args:
        file_path: CSV 파일 경로
        table_name: 테이블명 (price_daily, price_min_01, price_min_05, price_min_15)
        schema: 스키마명
        chunk_size: 한 번에 처리할 행 수
    """
    print(f"Loading {file_path} → {schema}.{table_name}")

    # CSV 읽기
    df = pd.read_csv(file_path)
    print(f"  Total rows: {len(df):,}")

    # 컬럼 매핑 (CSV → DB)
    column_mapping = {
        "trade_date": "trade_date",
        "trade_time": "trade_time",
        "open_price": "open_price",
        "high_price": "high_price",
        "low_price": "low_price",
        "close_price": "close_price",
        "volume": "volume",
        "turnover": "turnover",
        "bid_size_total": "bid_size_total",
        "ask_size_total": "ask_size_total",
    }

    # 일봉이 아닌 경우: trade_date + trade_time → trade_datetime
    if table_name != "price_daily":
        if "trade_date" in df.columns and "trade_time" in df.columns:
            if "ticker" in df.columns:
                df["ticker"] = df["ticker"].astype(str).str.zfill(6)
            df["trade_datetime"] = pd.to_datetime(
                df["trade_date"].astype(str) + " " + df["trade_time"].astype(str)
            )
            df = df.drop(columns=["trade_date", "trade_time"])
    else:
        # 일봉: trade_date만 유지
        if "ticker" in df.columns:
            df["ticker"] = df["ticker"].astype(str).str.zfill(6)
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    # 청크 단위로 적재
    total_chunks = (len(df) // chunk_size) + 1
    for i, start in enumerate(range(0, len(df), chunk_size)):
        chunk = df.iloc[start : start + chunk_size]
        chunk.to_sql(
            table_name,
            market_engine,
            schema=schema,
            if_exists="append",
            index=False,
            method="multi",
        )
        print(f"  Chunk {i+1}/{total_chunks} loaded ({len(chunk):,} rows)")

    print(f"  ✓ Complete: {len(df):,} rows loaded")


def load_folder_to_db(
    folder_path: str, table_name: str, schema: str = "raw", pattern: str = "*.csv"
):
    """폴더 내 모든 CSV 파일 적재"""
    folder = Path(folder_path)
    files = sorted(folder.glob(pattern))

    print(f"Found {len(files)} files in {folder_path}")

    for file_path in files:
        load_csv_to_db(str(file_path), table_name, schema)


def main():
    parser = argparse.ArgumentParser(description="Load CSV data to market-db")
    parser.add_argument("--file", type=str, help="CSV file path")
    parser.add_argument("--folder", type=str, help="Folder containing CSV files")
    parser.add_argument(
        "--table",
        type=str,
        required=True,
        choices=["price_daily", "price_min_01", "price_min_05", "price_min_15"],
        help="Target table name",
    )
    parser.add_argument("--schema", type=str, default="raw", help="Schema name")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Chunk size")

    args = parser.parse_args()

    # 스키마 생성
    init_market_schema()

    if args.file:
        load_csv_to_db(args.file, args.table, args.schema, args.chunk_size)
    elif args.folder:
        load_folder_to_db(args.folder, args.table, args.schema)
    else:
        print("Error: --file or --folder required")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
