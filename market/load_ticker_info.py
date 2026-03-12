import pandas as pd
import sys
from pathlib import Path
from market.db_market import market_engine


def load_ticker_info(file_path: str):
    print(f"Loading ticker_info from {file_path}")

    df = pd.read_csv(file_path)
    df = df.rename(columns={"sector": "sector_name"})
    df["listing_date"] = pd.to_datetime(df["listing_date"]).dt.date

    df.to_sql(
        "ticker_info", market_engine, schema="raw", if_exists="append", index=False
    )
    print(f"✓ Complete: {len(df):,} rows loaded")


if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        load_ticker_info(file_path)
