import pandas as pd
from market.db_market import market_engine, init_market_schema


def load_calendar(file_path: str):
    print(f"Loading calendar from {file_path}")

    df = pd.read_csv(file_path)

    # 컬럼 타입 변환
    df["base_date"] = pd.to_datetime(df["base_date"]).dt.date
    df["is_kr_business_day"] = df["is_kr_business_day"].astype(bool)
    df["is_us_business_day"] = df["is_us_business_day"].astype(bool)

    # 빈 문자열 → None
    df["kr_holiday_name"] = df["kr_holiday_name"].replace("", None)
    df["us_holiday_name"] = df["us_holiday_name"].replace("", None)

    df.to_sql("calendar", market_engine, schema="raw", if_exists="append", index=False)
    print(f"✓ Complete: {len(df):,} rows loaded")


if __name__ == "__main__":
    import sys

    load_calendar(sys.argv[1])
