import os
import matplotlib.pyplot as plt
import missingno as msno
import numpy as np
import pandas as pd
import seaborn as sns

os.makedirs("data", exist_ok=True)
os.makedirs("plots", exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.size"] = 10

print(">>> [ЛАБА 2] Запуск разведочного анализа данных (EDA)...")
np.random.seed(42)
N = 100000

df = pd.DataFrame(
    {
        "TransactionID": np.arange(3000000, 3000000 + N),
        "isFraud": np.random.choice([0, 1], size=N, p=[0.96594, 0.03406]),
        "TransactionAmt": np.round(
            np.random.exponential(scale=70, size=N) + 5, 2
        ),
        "ProductCD": np.random.choice(
            ["W", "C", "R", "H", "S"],
            size=N,
            p=[0.7398, 0.1160, 0.0640, 0.0560, 0.0242],
        ),
        "card1": np.random.randint(1000, 18396, size=N),
        "card4": np.random.choice(
            ["visa", "mastercard", "discover", "american express", None],
            size=N,
            p=[0.6514, 0.3150, 0.0220, 0.0100, 0.0016],
        ),
        "card6": np.random.choice(
            ["debit", "credit", None], size=N, p=[0.7439, 0.2543, 0.0018]
        ),
        "addr1": np.random.choice(
            list(np.random.randint(100, 540, size=300)) + [np.nan],
            size=N,
            p=[0.88335 / 300] * 300 + [0.11665],
        ),
        "P_emaildomain": np.random.choice(
            ["gmail.com", "yahoo.com", "hotmail.com", "mail.ru", None],
            size=N,
            p=[0.4362, 0.2350, 0.1200, 0.0499, 0.1589],
        ),
        "DeviceType": np.random.choice(
            ["desktop", "mobile", None], size=N, p=[0.1454, 0.0958, 0.7588]
        ),
        "DeviceInfo": np.random.choice(
            ["Windows", "iOS Device", "MacOS", "SM-G960N", None],
            size=N,
            p=[0.0811, 0.0750, 0.0500, 0.0324, 0.7615],
        ),
        "TransactionDT": np.sort(np.random.randint(86400, 86400 * 30, size=N)),
    }
)

df.to_csv("data/data_raw.csv", index=False)
print(f"Сырой датасет сохранен в data/data_raw.csv: {df.shape}")

# Расчет выбросов IQR
Q1 = df["TransactionAmt"].quantile(0.25)
Q3 = df["TransactionAmt"].quantile(0.75)
IQR = Q3 - Q1
upper_bound = Q3 + 1.5 * IQR
outliers = (df["TransactionAmt"] > upper_bound).sum()
print(f"Порог выбросов IQR: {upper_bound:.2f} USD (выбросов: {outliers})")

# Построение графиков
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.histplot(
    df["TransactionAmt"],
    bins=50,
    kde=False,
    color="#2b5c8f",
    log_scale=True,
    ax=axes[0],
)
axes[0].set_title("Распределение суммы транзакций (log-scale)")

sns.boxplot(
    data=df,
    x="isFraud",
    y="TransactionAmt",
    palette=["#4a90e2", "#d9534f"],
    showfliers=False,
    ax=axes[1],
)
axes[1].set_title("Сумма транзакции по статусу isFraud")
plt.tight_layout()
plt.savefig("plots/eda_fig1_amounts.png", dpi=300)
plt.close()

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
df["card4"].value_counts().plot(kind="bar", color="#5cb85c", ax=axes[0])
axes[0].set_title("Популярность платежных систем")
df["ProductCD"].value_counts().plot(kind="pie", autopct="%1.1f%%", ax=axes[1])
axes[1].set_title("Категории продуктов")
plt.tight_layout()
plt.savefig("plots/eda_fig2_categories.png", dpi=300)
plt.close()

plt.figure(figsize=(10, 4))
msno.matrix(df, sparkline=False, figsize=(10, 4), fontsize=9)
plt.savefig("plots/eda_fig3_missing_matrix.png", dpi=300)
plt.close()

print(">>> [ЛАБА 2] Выполнено! Все графики сохранены в папку plots/")