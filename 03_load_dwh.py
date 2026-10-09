import sqlite3
import numpy as np
import pandas as pd

print(">>> [ЛАБА 6] Запуск миграции и загрузки в реляционное DWH...")

conn = sqlite3.connect("data/anti_fraud_dwh.db")
cursor = conn.cursor()

df = pd.read_csv("data/data_cleaned.csv")
print(f"Считано строк для загрузки: {len(df)}")

# 1. Создание схемы таблиц
cursor.executescript(
    """
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS dim_card;
DROP TABLE IF EXISTS dim_device;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_email_domain;
DROP TABLE IF EXISTS dim_product;

CREATE TABLE dim_card (
    card_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    card1_code INTEGER,
    card_network TEXT,
    card_type TEXT
);

CREATE TABLE dim_device (
    device_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_type TEXT,
    os_family TEXT,
    device_info_raw TEXT
);

CREATE TABLE dim_location (
    location_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    addr_code INTEGER,
    is_unknown_geo INTEGER
);

CREATE TABLE dim_time (
    time_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour_of_day INTEGER,
    day_of_week INTEGER,
    is_night_flag INTEGER
);

CREATE TABLE dim_email_domain (
    email_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_name TEXT,
    is_free_provider INTEGER
);

CREATE TABLE dim_product (
    product_dim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT
);

CREATE TABLE fact_transactions (
    fact_tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER,
    card_dim_id INTEGER,
    device_dim_id INTEGER,
    location_dim_id INTEGER,
    time_dim_id INTEGER,
    email_dim_id INTEGER,
    product_dim_id INTEGER,
    amount REAL,
    amount_log REAL,
    is_fraud INTEGER,
    is_outlier INTEGER,
    amt_bin TEXT,
    tx_count INTEGER DEFAULT 1
);
"""
)

# 2. Наполнение измерений
print(">>> Наполнение 6 измерений...")
dim_card = (
    df[["card1", "card4", "card6"]]
    .drop_duplicates()
    .rename(
        columns={
            "card1": "card1_code",
            "card4": "card_network",
            "card6": "card_type",
        }
    )
)
dim_card.to_sql("dim_card", conn, if_exists="append", index=False)

dim_device = (
    df[["DeviceType", "os_family", "DeviceInfo"]]
    .drop_duplicates()
    .rename(
        columns={"DeviceType": "device_type", "DeviceInfo": "device_info_raw"}
    )
)
dim_device.to_sql("dim_device", conn, if_exists="append", index=False)

dim_loc = (
    df[["addr1", "addr_missing"]]
    .drop_duplicates()
    .rename(columns={"addr1": "addr_code", "addr_missing": "is_unknown_geo"})
)
dim_loc.to_sql("dim_location", conn, if_exists="append", index=False)

dim_time = (
    df[["tx_hour", "tx_day_of_week", "is_night_tx"]]
    .drop_duplicates()
    .rename(
        columns={
            "tx_hour": "hour_of_day",
            "tx_day_of_week": "day_of_week",
            "is_night_tx": "is_night_flag",
        }
    )
)
dim_time.to_sql("dim_time", conn, if_exists="append", index=False)

dim_email = (
    df[["P_emaildomain", "is_free_email"]]
    .drop_duplicates()
    .rename(
        columns={
            "P_emaildomain": "domain_name",
            "is_free_email": "is_free_provider",
        }
    )
)
dim_email.to_sql("dim_email_domain", conn, if_exists="append", index=False)

dim_prod = (
    df[["ProductCD"]]
    .drop_duplicates()
    .rename(columns={"ProductCD": "product_code"})
)
dim_prod.to_sql("dim_product", conn, if_exists="append", index=False)

# 3. Разрешение ключей (строгий merge)
print(">>> Связывание суррогатных ключей...")
map_card = pd.read_sql(
    "SELECT card_dim_id, card1_code, card_network, card_type FROM dim_card",
    conn,
)
map_device = pd.read_sql(
    "SELECT device_dim_id, device_type, os_family, device_info_raw FROM"
    " dim_device",
    conn,
)
map_loc = pd.read_sql(
    "SELECT location_dim_id, addr_code, is_unknown_geo FROM dim_location", conn
)
map_time = pd.read_sql(
    "SELECT time_dim_id, hour_of_day, day_of_week, is_night_flag FROM"
    " dim_time",
    conn,
)
map_email = pd.read_sql(
    "SELECT email_dim_id, domain_name, is_free_provider FROM dim_email_domain",
    conn,
)
map_prod = pd.read_sql(
    "SELECT product_dim_id, product_code FROM dim_product", conn
)

df_fact = df.merge(
    map_card,
    left_on=["card1", "card4", "card6"],
    right_on=["card1_code", "card_network", "card_type"],
)
df_fact = df_fact.merge(
    map_device,
    left_on=["DeviceType", "os_family", "DeviceInfo"],
    right_on=["device_type", "os_family", "device_info_raw"],
)
df_fact = df_fact.merge(
    map_loc,
    left_on=["addr1", "addr_missing"],
    right_on=["addr_code", "is_unknown_geo"],
)
df_fact = df_fact.merge(
    map_time,
    left_on=["tx_hour", "tx_day_of_week", "is_night_tx"],
    right_on=["hour_of_day", "day_of_week", "is_night_flag"],
)
df_fact = df_fact.merge(
    map_email,
    left_on=["P_emaildomain", "is_free_email"],
    right_on=["domain_name", "is_free_provider"],
)
df_fact = df_fact.merge(
    map_prod, left_on="ProductCD", right_on="product_code"
)

# 4. Загрузка фактов
fact_table = pd.DataFrame(
    {
        "transaction_id": df_fact["TransactionID"],
        "card_dim_id": df_fact["card_dim_id"],
        "device_dim_id": df_fact["device_dim_id"],
        "location_dim_id": df_fact["location_dim_id"],
        "time_dim_id": df_fact["time_dim_id"],
        "email_dim_id": df_fact["email_dim_id"],
        "product_dim_id": df_fact["product_dim_id"],
        "amount": df_fact["TransactionAmt"],
        "amount_log": df_fact["amt_log"],
        "is_fraud": df_fact["isFraud"],
        "is_outlier": df_fact["is_amount_outlier"],
        "amt_bin": df_fact["amt_bin"].astype(str),
        "tx_count": 1,
    }
)

print(f">>> Загрузка {len(fact_table)} строк в fact_transactions...")
fact_table.to_sql("fact_transactions", conn, if_exists="append", index=False)
conn.commit()

# 5. Аудит
query_audit = """
SELECT 
    COUNT(*) AS total_rows, 
    ROUND(AVG(amount), 2) AS avg_amount,
    SUM(is_fraud) AS total_fraud,
    ROUND(SUM(is_fraud) * 100.0 / COUNT(*), 2) AS fraud_pct
FROM fact_transactions;
"""
res = pd.read_sql(query_audit, conn)
print("\n--- РЕЗУЛЬТАТ АУДИТА ЗАГРУЗКИ ---")
print(res)

conn.close()
print("\n>>> [ЛАБА 6] Успешно завершено! База data/anti_fraud_dwh.db готова.")