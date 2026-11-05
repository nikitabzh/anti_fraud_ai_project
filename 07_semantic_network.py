"""Лабораторная 11, вариант 27. Анализ семантической сети банковских транзакций.

Запуск: python 07_semantic_network.py
Метрики выводятся в консоль; рисунок 300 dpi сохраняется во временной папке ОС.
Зависимости: networkx, matplotlib, scipy (для PageRank).
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import networkx as nx

ROOT = Path(__file__).resolve().parent
TYPES = {'Transaction': 'Транзакция', 'Card': 'Профиль карты',
         'Device': 'Тип оборудования', 'Location': 'Регион',
         'Email': 'Почтовый домен', 'Product': 'Продукт'}
COLORS = dict(zip(TYPES, ['#4078b5', '#e5a13e', '#73a653', '#b47db4', '#ce665c', '#59a7ad']))

def load_rows(limit=500):
    if limit < 2:
        raise ValueError('Нужно не менее двух транзакций')
    query = '''SELECT f.transaction_id, f.amount, f.is_fraud,
      f.card_dim_id, f.device_dim_id, f.location_dim_id, f.email_dim_id, f.product_dim_id,
      c.card_network, c.card_type, d.device_type, d.os_family,
      l.addr_code, e.domain_name, p.product_code
      FROM fact_transactions f
      JOIN dim_card c ON f.card_dim_id=c.card_dim_id
      JOIN dim_device d ON f.device_dim_id=d.device_dim_id
      JOIN dim_location l ON f.location_dim_id=l.location_dim_id
      JOIN dim_email_domain e ON f.email_dim_id=e.email_dim_id
      JOIN dim_product p ON f.product_dim_id=p.product_dim_id
      ORDER BY f.transaction_id LIMIT ?'''
    with sqlite3.connect(f'file:{ROOT / "data/anti_fraud_dwh.db"}?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(query, (limit,))]
    if len(rows) < 2:
        raise ValueError('В хранилище недостаточно транзакций')
    return rows

def build_graph(rows):
    graph = nx.DiGraph()
    attributes = {}
    for r in rows:
        tx = f'tx_{r["transaction_id"]}'
        graph.add_node(tx, amount=r['amount'], is_fraud=r['is_fraud'])
        attributes[tx] = {'type': 'Transaction', 'name': tx}
        entities = [
            ('card', 'card_dim_id', 'Card', 'EXECUTED_WITH', f'{r["card_network"]}/{r["card_type"]}'),
            ('dev', 'device_dim_id', 'Device', 'INITIATED_FROM', f'{r["device_type"]}/{r["os_family"]}'),
            ('loc', 'location_dim_id', 'Location', 'OCCURRED_IN', str(r['addr_code'])),
            ('email', 'email_dim_id', 'Email', 'USES_EMAIL', str(r['domain_name'])),
            ('prod', 'product_dim_id', 'Product', 'OF_CATEGORY', str(r['product_code']))]
        for prefix, key, kind, relation, name in entities:
            node = f'{prefix}_{r[key]}'
            graph.add_node(node)
            attributes[node] = {'type': kind, 'name': name}
            graph.add_edge(tx, node, edge_type=relation, amount=r['amount'])
    nx.set_node_attributes(graph, attributes)
    return graph

def describe(graph, node):
    return f'{node} ({graph.nodes[node]["name"]})'

def analyze(graph):
    # Направление дуг хранит семантику. Связность и близость анализируем на U.
    u = graph.to_undirected()
    components = sorted(nx.connected_components(u), key=lambda c: (-len(c), min(c)))
    largest = u.subgraph(components[0])
    degree = dict(u.degree())
    leader = sorted(degree, key=lambda n: (-degree[n], n))[0]
    centralities = {'degree': nx.degree_centrality(u),
                    'betweenness': nx.betweenness_centrality(u),
                    'closeness': nx.closeness_centrality(u),
                    'pagerank': nx.pagerank(graph, alpha=0.85, tol=1e-10)}
    top = {name: [{'node': describe(graph, n), 'value': values[n]}
                 for n in sorted(values, key=lambda n: (-values[n], n))[:5]]
           for name, values in centralities.items()}
    communities = nx.community.louvain_communities(u, seed=27)
    communities = sorted(communities, key=lambda c: (-len(c), min(c)))
    community_data = []
    for i, group in enumerate(communities, 1):
        counts = Counter(graph.nodes[n]['type'] for n in group)
        hubs = sorted(group, key=lambda n: (-degree[n], n))[:3]
        community_data.append({'id': i, 'size': len(group), 'types': dict(counts),
                               'hubs': [describe(graph, n) for n in hubs]})
    txs = sorted(n for n in graph if graph.nodes[n]['type'] == 'Transaction')
    source = txs[0]
    distances = nx.single_source_shortest_path_length(u, source)
    target = next((n for n in txs[1:] if n in distances), source)
    path = nx.shortest_path(u, source, target)
    ego = nx.ego_graph(u, source, radius=2)
    # Считаем общую категорию оборудования, не уникальное физическое устройство.
    device_nodes = [n for n in graph if graph.nodes[n]['type'] == 'Device']
    device = sorted(device_nodes, key=lambda n: (-graph.in_degree(n), n))[0]
    related = sorted(graph.predecessors(device))
    fraud = [n for n in related if graph.nodes[n]['is_fraud'] == 1]
    return {'statistics': {'nodes': len(graph), 'edges': graph.number_of_edges(),
        'directed_density': nx.density(graph), 'weak_components': len(components),
        'strong_components': nx.number_strongly_connected_components(graph),
        'largest_component': len(largest), 'diameter_undirected': nx.diameter(largest),
        'mean_degree': sum(degree.values()) / len(graph), 'max_degree': degree[leader],
        'max_degree_node': describe(graph, leader), 'clustering': nx.average_clustering(u)},
        'node_types': dict(Counter(nx.get_node_attributes(graph, 'type').values())),
        'edge_types': dict(Counter(nx.get_edge_attributes(graph, 'edge_type').values())),
        'queries': {'shortest_path': path, 'ego_source': source,
            'ego_nodes': len(ego), 'ego_neighbors': len(ego)-1,
            'ego_preview': sorted(n for n in ego if n != source)[:10],
            'device': describe(graph, device), 'device_transactions': len(related),
            'device_fraud': len(fraud), 'fraud_preview': fraud[:10]},
        'top5': top, 'communities': community_data,
        'modularity': nx.community.modularity(u, communities)}

def visualize(graph, output):
    u = graph.to_undirected()
    # Несколько платежей и их контекст, затем соседние платежи до 40 узлов.
    txs = sorted(n for n in graph if graph.nodes[n]['type'] == 'Transaction')
    selected = set(txs[:5])
    for tx in txs[:5]: selected.update(graph.successors(tx))
    for node in sorted(selected):
        for neighbor in sorted(u.neighbors(node)):
            if len(selected) >= 40: break
            selected.add(neighbor)
        if len(selected) >= 40: break
    sub = u.subgraph(sorted(selected)).copy()
    positions = nx.spring_layout(sub, seed=27, k=0.65, iterations=150)
    important = sorted(sub, key=lambda n: (-sub.degree(n), n))[:10]
    fig, ax = plt.subplots(figsize=(10, 7.5))
    nx.draw_networkx_edges(sub, positions, ax=ax, alpha=0.35, edge_color='#707070')
    nx.draw_networkx_nodes(sub, positions, ax=ax,
        node_color=[COLORS[graph.nodes[n]['type']] for n in sub],
        node_size=[45*sub.degree(n) for n in sub], linewidths=0.5, edgecolors='white')
    nx.draw_networkx_labels(sub, positions, labels={n:n for n in important}, font_size=8, ax=ax,
        bbox={'facecolor':'white','alpha':0.8,'edgecolor':'none','pad':1})
    ax.legend(handles=[Patch(color=c, label=TYPES[t]) for t,c in COLORS.items()],
              loc='upper left', fontsize=8, frameon=False)
    ax.set_title(f'Семантическая сеть транзакций — фрагмент из {len(sub)} узлов', fontsize=12)
    ax.axis('off'); fig.tight_layout(); fig.savefig(output, dpi=300); plt.close(fig)
    return len(sub)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=500)
    args = parser.parse_args()
    graph = build_graph(load_rows(args.limit))
    result = analyze(graph)
    output = Path(tempfile.gettempdir())/'lab11_semantic_network.png'
    result['visualization_nodes'] = visualize(graph, output)
    result['image'] = str(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
