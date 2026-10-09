-- DDL Схема «Звезда» для антифрод-хранилища
DROP TABLE IF EXISTS fact_transactions CASCADE;
DROP TABLE IF EXISTS dim_card CASCADE;
DROP TABLE IF EXISTS dim_device CASCADE;
DROP TABLE IF EXISTS dim_location CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;
DROP TABLE IF EXISTS dim_email_domain CASCADE;
DROP TABLE IF EXISTS dim_product CASCADE;

CREATE TABLE dim_card (
    card_dim_id       BIGSERIAL PRIMARY KEY,
    card1_code        INTEGER NOT NULL,
    card_network      VARCHAR(20) NOT NULL,
    card_type         VARCHAR(20) NOT NULL
);

CREATE TABLE dim_device (
    device_dim_id     BIGSERIAL PRIMARY KEY,
    device_type       VARCHAR(20) NOT NULL,
    os_family         VARCHAR(50) NOT NULL,
    device_info_raw   VARCHAR(100)
);

CREATE TABLE dim_location (
    location_dim_id   BIGSERIAL PRIMARY KEY,
    addr_code         INTEGER NOT NULL,
    is_unknown_geo    SMALLINT NOT NULL
);

CREATE TABLE dim_time (
    time_dim_id       BIGSERIAL PRIMARY KEY,
    hour_of_day       SMALLINT NOT NULL,
    day_of_week       SMALLINT NOT NULL,
    is_night_flag     SMALLINT NOT NULL
);

CREATE TABLE dim_email_domain (
    email_dim_id      BIGSERIAL PRIMARY KEY,
    domain_name       VARCHAR(100) NOT NULL,
    is_free_provider  SMALLINT NOT NULL
);

CREATE TABLE dim_product (
    product_dim_id    BIGSERIAL PRIMARY KEY,
    product_code      VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE fact_transactions (
    fact_tx_id        BIGSERIAL PRIMARY KEY,
    transaction_id    BIGINT NOT NULL UNIQUE,
    card_dim_id       BIGINT NOT NULL REFERENCES dim_card(card_dim_id),
    device_dim_id     BIGINT NOT NULL REFERENCES dim_device(device_dim_id),
    location_dim_id   BIGINT NOT NULL REFERENCES dim_location(location_dim_id),
    time_dim_id       BIGINT NOT NULL REFERENCES dim_time(time_dim_id),
    email_dim_id      BIGINT NOT NULL REFERENCES dim_email_domain(email_dim_id),
    product_dim_id    BIGINT NOT NULL REFERENCES dim_product(product_dim_id),
    amount            NUMERIC(10, 2) NOT NULL,
    amount_log        REAL NOT NULL,
    is_fraud          SMALLINT NOT NULL,
    is_outlier        SMALLINT NOT NULL,
    amt_bin           VARCHAR(20) NOT NULL,
    tx_count          INTEGER DEFAULT 1
);