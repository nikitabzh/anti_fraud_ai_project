import os
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

print(">>> [ЛАБА 8] Инициализация графа знаний (Knowledge Graph)...")

os.makedirs("plots", exist_ok=True)

# 1. Загрузка данных
df = pd.read_csv("data/data_cleaned.csv")
# Берем срез первых 2500 транзакций
sample_df = df.head(2500).copy()

# Создаем направленный граф
G = nx.DiGraph()

print(">>> Построение узлов и рёбер графа знаний...")
for _, row in sample_df.iterrows():
    tx_id = f"tx_{row['TransactionID']}"
    card_id = f"card_{row['card1']}"
    dev_id = f"dev_{row['os_family']}_{row['DeviceType']}"
    loc_id = f"loc_{row['addr1']}"
    email_id = f"email_{row['P_emaildomain']}"
    prod_id = f"prod_{row['ProductCD']}"

    # Создаем узлы с атрибутами
    G.add_node(
        tx_id,
        label="Transaction",
        amount=row["TransactionAmt"],
        is_fraud=row["isFraud"],
        is_night=row["is_night_tx"],
    )
    G.add_node(
        card_id,
        label="Card",
        network=row["card4"],
        card_type=row["card6"],
    )
    G.add_node(
        dev_id,
        label="Device",
        os=row["os_family"],
        dtype=row["DeviceType"],
    )
    G.add_node(loc_id, label="Location")
    G.add_node(email_id, label="EmailDomain")
    G.add_node(prod_id, label="Product")

    # Создаем типизированные рёбра
    G.add_edge(
        tx_id,
        card_id,
        rel="EXECUTED_WITH",
        amount=row["TransactionAmt"],
    )
    G.add_edge(tx_id, dev_id, rel="INITIATED_FROM")
    G.add_edge(tx_id, loc_id, rel="OCCURRED_IN")
    G.add_edge(tx_id, email_id, rel="USES_EMAIL")
    G.add_edge(tx_id, prod_id, rel="OF_CATEGORY")

print(
    f"Граф успешно построен: {G.number_of_nodes()} узлов,"
    f" {G.number_of_edges()} рёбер.\n"
)

# Преобразуем во ненаправленный граф для поиска связности и путей
undirected_G = G.to_undirected()

# =====================================================================
# ВЫПОЛНЕНИЕ 4 ОБЯЗАТЕЛЬНЫХ ТЕСТОВЫХ ЗАПРОСОВ
# =====================================================================

print("=" * 60)
print("ТЕСТОВЫЙ ЗАПРОС 1: Локальный контекст транзакции tx_3000005")
print("=" * 60)
target_tx = "tx_3000005"
if target_tx in G:
    attrs = G.nodes[target_tx]
    print(
        f"Узел: {target_tx} (Сумма: ${attrs.get('amount')}, Фрод:"
        f" {attrs.get('is_fraud')}):"
    )
    for neighbor in G.successors(target_tx):
        edge_data = G.get_edge_data(target_tx, neighbor)
        rel_type = edge_data.get("rel", "CONNECTED_TO")
        n_label = G.nodes[neighbor].get("label", "Entity")
        print(f"  -> [{rel_type}] -> {n_label}: {neighbor}")

print("\n" + "=" * 60)
print("ТЕСТОВЫЙ ЗАПРОС 2: Кратчайший путь между сущностями")
print("=" * 60)
# Динамически выбираем вторую карту, которая точно есть в графе
source_node = "tx_3000005"
existing_cards = [
    n
    for n, d in G.nodes(data=True)
    if d.get("label") == "Card" and n not in G.successors(source_node)
]

if existing_cards:
    target_card = existing_cards[10]  # гарантированно существующий узел
    try:
        path = nx.shortest_path(
            undirected_G, source=source_node, target=target_card
        )
        print(f"Кратчайший путь между {source_node} и {target_card}:")
        print(" -> ".join(path))
    except nx.NetworkXNoPath:
        print(f"Путь между {source_node} и {target_card} не найден.")
else:
    print("Не найдено подходящих узлов карт.")

print("\n" + "=" * 60)
print("ТЕСТОВЫЙ ЗАПРОС 3: Топ-10 узлов-хабов по степени связности (Degree)")
print("=" * 60)
degrees = sorted(undirected_G.degree, key=lambda x: x[1], reverse=True)[:10]
for idx, (node, deg) in enumerate(degrees, 1):
    label = G.nodes[node].get("label", "Entity")
    print(f"{idx:2d}. {node:30s} [{label:12s}] : {deg} связей")

print("\n" + "=" * 60)
print("ТЕСТОВЫЙ ЗАПРОС 4: Антифрод-детекция (Device Sharing при мошенничестве)")
print("=" * 60)
devices = [n for n, d in G.nodes(data=True) if d.get("label") == "Device"]
found_clusters = False
for dev in devices:
    if "offline_pos" in dev:
        continue
    # Все транзакции, совершенные с этого устройства
    txs = [t for t in G.predecessors(dev) if G.nodes[t].get("is_fraud") == 1]
    cards = set()
    total_amt = 0.0
    for t in txs:
        total_amt += G.nodes[t].get("amount", 0.0)
        for target in G.successors(t):
            if G.nodes[target].get("label") == "Card":
                cards.add(target)
    if len(cards) > 1:
        found_clusters = True
        print(f"КЛАСТЕР МОШЕННИЧЕСКОЙ ФЕРМЫ НА УСТРОЙСТВЕ: {dev}")
        print(f"  Скомпрометировано карт: {len(cards)} шт.")
        print(
            f"  Совершено атак: {len(txs)} шт. на общую сумму: ${total_amt:.2f}"
        )

if not found_clusters:
    # Если в первых 2500 строк не попалось таких устройств, ищем по общим транзакциям
    print("Подозрительные устройства с несколькими картами:")
    for dev in devices:
        if "offline_pos" in dev:
            continue
        all_txs = list(G.predecessors(dev))
        cards = {
            target
            for t in all_txs
            for target in G.successors(t)
            if G.nodes[target].get("label") == "Card"
        }
        if len(cards) > 2:
            print(
                f"Устройство {dev} связано с {len(cards)} различными картами"
                f" (Всего операций: {len(all_txs)})"
            )

# =====================================================================
# ВИЗУАЛИЗАЦИЯ ПОДГРАФА (ШАГ 7)
# =====================================================================
print("\n>>> Генерация визуализации подграфа (20-25 узлов)...")

# Динамически находим самое активное онлайн-устройство для центра подграфа
online_devs = [
    n
    for n, d in G.nodes(data=True)
    if d.get("label") == "Device" and "offline_pos" not in n
]
focus_dev = (
    max(online_devs, key=lambda d: G.in_degree(d))
    if online_devs
    else list(devices)[0]
)

sub_nodes = {focus_dev}
connected_txs = list(G.predecessors(focus_dev))[:6]
sub_nodes.update(connected_txs)

for t in connected_txs:
    for neighbor in G.successors(t):
        sub_nodes.add(neighbor)

sub_G = G.subgraph(list(sub_nodes)[:24])

# Цветовая схема узлов
color_map = []
for node in sub_G.nodes():
    label = sub_G.nodes[node].get("label")
    if label == "Transaction":
        if sub_G.nodes[node].get("is_fraud") == 1:
            color_map.append("#e74c3c")  # Красный - фрод
        else:
            color_map.append("#2ecc71")  # Зеленый - легитимная
    elif label == "Card":
        color_map.append("#3498db")  # Синий
    elif label == "Device":
        color_map.append("#e67e22")  # Оранжевый
    elif label == "Location":
        color_map.append("#9b59b6")  # Фиолетовый
    else:
        color_map.append("#f1c40f")  # Желтый

plt.figure(figsize=(11, 7))
pos = nx.spring_layout(sub_G, seed=42, k=0.5)
nx.draw_networkx_nodes(
    sub_G,
    pos,
    node_color=color_map,
    node_size=650,
    alpha=0.9,
    edgecolors="#2c3e50",
)
nx.draw_networkx_edges(
    sub_G, pos, arrowstyle="->", arrowsize=12, edge_color="#7f8c8d", alpha=0.6
)

labels = {
    n: n.split("_")[0] + "_" + n.split("_")[1][:5] for n in sub_G.nodes()
}
nx.draw_networkx_labels(sub_G, pos, labels=labels, font_size=8)

plt.title(
    f"Фрагмент графа знаний вокруг устройства {focus_dev}\n(Красный: Фрод,"
    " Зеленый: Легитимно, Синий: Карты, Оранжевый: Устройства)",
    fontsize=10,
)
plt.axis("off")
plt.tight_layout()
plt.savefig("plots/graph_fig1_subgraph.png", dpi=300)
plt.close()

print(
    ">>> [ЛАБА 8] Успешно завершено! Визуализация сохранена в"
    " plots/graph_fig1_subgraph.png"
)