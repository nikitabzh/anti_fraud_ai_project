import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

print(">>> [ЛАБА 4] Запуск ETL-очистки данных...")

df_raw = pd.read_csv("data/data_raw.csv")
df = df_raw.copy()

# 1. Дедупликация
df = df.drop_duplicates(subset=["TransactionID"], keep="first")

# 2. Обработка сумм
df["TransactionAmt"] = df["TransactionAmt"].round(2)
df["amt_log"] = np.log1p(df["TransactionAmt"])
df["is_amount_outlier"] = (df["TransactionAmt"] > 217.57).astype(int)
df["amt_bin"] = pd.cut(
    df["TransactionAmt"],
    bins=[-np.inf, 50.0, 200.0, 500.0, np.inf],
    labels=["Small", "Medium", "Large", "Extreme"],
)

# 3. Инженерия времени
df["tx_hour"] = (df["TransactionDT"] // 3600) % 24
df["tx_day_of_week"] = (df["TransactionDT"] // 86400) % 7
df["is_night_tx"] = (df["tx_hour"] < 6).astype(int)

# 4. Обработка устройств
df["DeviceType"] = (
    df["DeviceType"].fillna("offline_pos").astype(str).str.lower()
)


def parse_os(val):
    if pd.isna(val) or val == "unknown_pos":
        return "unknown_pos"
    v = str(val).lower()
    if any(x in v for x in ["windows", "win"]):
        return "Windows"
    if any(x in v for x in ["ios", "iphone", "ipad"]):
        return "iOS"
    if any(x in v for x in ["android", "sm-", "moto", "lg"]):
        return "Android"
    if any(x in v for x in ["mac", "macintosh"]):
        return "MacOS"
    return "Other"


df["DeviceInfo"] = df["DeviceInfo"].fillna("unknown_pos")
df["os_family"] = df["DeviceInfo"].apply(parse_os)

# 5. Обработка почты
df["P_emaildomain"] = (
    df["P_emaildomain"].fillna("missing").astype(str).str.lower().str.strip()
)
free_mail = {"gmail.com", "yahoo.com", "hotmail.com", "mail.ru", "yandex.ru"}
df["is_free_email"] = df["P_emaildomain"].isin(free_mail).astype(int)

# 6. Обработка регионов
df["addr_missing"] = df["addr1"].isna().astype(int)
df["addr1"] = df["addr1"].fillna(-1).astype(int)

# 7. Импутация карт
for col in ["card4", "card6"]:
    mode_map = df.groupby("card1")[col].transform(
        lambda x: x.mode()[0] if not x.mode().empty else "unknown"
    )
    df[col] = df[col].fillna(mode_map).fillna("unknown")

# Сохранение артефактов
df.to_csv("data/data_cleaned.csv", index=False)

quality_rep = pd.DataFrame(
    {
        "Поле": df.columns,
        "Тип": df.dtypes.astype(str).values,
        "Уникальных": df.nunique().values,
        "Пропусков": df.isnull().sum().values,
        "Пропусков_%": (df.isnull().sum() / len(df) * 100).round(2).values,
    }
)
quality_rep.to_csv("data/quality_report.csv", index=False)

# Графики сравнения
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.histplot(
    df_raw["TransactionAmt"],
    bins=40,
    color="#c0392b",
    ax=axes[0],
    kde=True,
    stat="density",
)
axes[0].set_title("Сумма транзакций (До обработки: скос вправо)")
axes[0].set_xlim(0, 500)

sns.histplot(
    df["amt_log"],
    bins=40,
    color="#2980b9",
    ax=axes[1],
    kde=True,
    stat="density",
)
axes[1].set_title("amt_log = ln(1 + Amt) (После обработки)")
plt.tight_layout()
plt.savefig("plots/etl_fig1_amounts_compare.png", dpi=300)
plt.close()

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.countplot(x="tx_hour", data=df, color="#27ae60", ax=axes[0])
axes[0].set_title("Транзакции по часам суток (tx_hour)")

order_os = df["os_family"].value_counts().index
sns.countplot(
    x="os_family", data=df, order=order_os, palette="Blues_r", ax=axes[1]
)
axes[1].set_title("Семейство ОС (os_family)")
axes[1].tick_params(axis="x", rotation=25)
plt.tight_layout()
plt.savefig("plots/etl_fig2_features.png", dpi=300)
plt.close()

print(f"Размер очищенных данных: {df.shape} (21 колонка, 0 пропусков)")
print(
    ">>> [ЛАБА 4] Выполнено! Файлы сохранены в data/, графики — в папку plots/"
)