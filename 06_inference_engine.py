"""Лабораторная 10. Прямой вывод; запуск из любой папки, без изменения DWH."""
import argparse
import csv
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPS = {'==': lambda a,b:a==b, '!=': lambda a,b:a!=b,
       '>': lambda a,b:a>b, '>=': lambda a,b:a>=b,
       '<': lambda a,b:a<b, '<=': lambda a,b:a<=b}

def check(value, condition):
    if value is None:
        return False
    if not isinstance(condition, dict):
        return value == condition
    return all(OPS[op](value, target) for op, target in condition.items())

def match_rules(facts, rules):
    return [r for r in rules if not facts.get('fired_' + r['id'])
            and all(check(facts.get(k), v) for k,v in r['if'].items())]

def resolve_conflicts(applicable):
    # Специфичность = число атомарных проверок; ID обеспечивает повторяемость.
    return sorted(applicable, key=lambda r: (-r['priority'],
        -sum(len(v) if isinstance(v, dict) else 1 for v in r['if'].values()), r['id']))[0]

def apply_rule(rule, facts):
    new = {'fired_' + rule['id']: True}
    if 'winning_rule' not in facts:
        new.update(decision=rule['then']['decision'], winning_rule=rule['id'])
    new['risk_score'] = max(facts.get('risk_score', 0), rule['then']['risk_score'])
    return {k:v for k,v in new.items() if k not in facts or facts[k] != v}

def infer(facts, rules, max_steps=100):
    memory, trace = dict(facts), []
    # Разметка не является входным фактом механизма вывода.
    memory.pop('is_fraud', None)
    for _ in range(max_steps):
        applicable = match_rules(memory, rules)
        if not applicable:
            break
        selected = resolve_conflicts(applicable)
        additions = apply_rule(selected, memory)
        if not additions:
            break
        trace.append({'id': selected['id'], 'description': selected['description'],
                      'conditions': {k: memory.get(k) for k in selected['if']},
                      'expected': selected['if'], 'added': additions,
                      'conflict_set': sorted(r['id'] for r in applicable)})
        memory.update(additions)
    else:
        raise RuntimeError('Превышен лимит шагов вывода')
    memory.setdefault('decision', 'Investigate_SOC')
    memory.setdefault('risk_score', 0)
    return memory, trace

def explain(trace):
    if not trace:
        return 'Правила не применимы. Investigate_SOC: требуется ручная проверка.'
    lines = []
    for step in trace:
        conditions = '; '.join(f'{k}={v!r}, условие {step["expected"][k]!r}'
                               for k,v in step['conditions'].items())
        lines.append(f'{step["id"]}: {step["description"]}. {conditions}. Добавлено: {step["added"]}')
    return '\n'.join(lines)

QUERY = '''SELECT f.transaction_id, f.amount, f.amt_bin,
 f.is_outlier AS is_amount_outlier, f.is_fraud, c.card_type,
 d.device_type, d.os_family, l.is_unknown_geo,
 t.is_night_flag AS is_night_tx, e.is_free_provider AS is_free_email
 FROM fact_transactions f
 JOIN dim_card c ON c.card_dim_id=f.card_dim_id
 JOIN dim_device d ON d.device_dim_id=f.device_dim_id
 JOIN dim_location l ON l.location_dim_id=f.location_dim_id
 JOIN dim_time t ON t.time_dim_id=f.time_dim_id
 JOIN dim_email_domain e ON e.email_dim_id=f.email_dim_id
 ORDER BY f.transaction_id LIMIT {limit}'''

def load_records(limit, postgres_dsn=None):
    if limit < 50:
        raise ValueError('Для оценки требуется не менее 50 записей')
    if postgres_dsn:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(postgres_dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(QUERY.format(limit=int(limit)))
                return [dict(r) for r in cursor.fetchall()], 'PostgreSQL'
    with sqlite3.connect(f'file:{ROOT / "data/anti_fraud_dwh.db"}?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(QUERY.format(limit=int(limit)))], 'SQLite'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--postgres', action='store_true', help='Использовать переменную POSTGRES_DSN')
    args = parser.parse_args()
    dsn = os.environ['POSTGRES_DSN'] if args.postgres else None
    rows, source = load_records(args.limit, dsn)
    if len(rows) < 50:
        raise ValueError('В хранилище недостаточно записей')
    rules = json.loads((ROOT / 'data/rules.json').read_text(encoding='utf-8'))
    results = []
    for row in rows:
        truth = int(row['is_fraud'])
        facts, trace = infer(row, rules)
        # Положительный класс: любая операция, направленная на проверку/блокировку.
        pred = int(facts['decision'] != 'Approve')
        results.append(dict(transaction_id=row['transaction_id'], actual=truth, predicted=pred,
            decision=facts['decision'], risk_score=facts['risk_score'], steps=len(trace),
            facts=row, trace=trace, explanation=explain(trace)))
    tp=sum(r['actual']==r['predicted']==1 for r in results)
    tn=sum(r['actual']==r['predicted']==0 for r in results)
    fp=sum(r['actual']==0 and r['predicted']==1 for r in results)
    fn=sum(r['actual']==1 and r['predicted']==0 for r in results)
    p=tp/(tp+fp) if tp+fp else 0
    rec=tp/(tp+fn) if tp+fn else 0
    metrics=dict(source=source,n=len(rows),correct=tp+tn,TP=tp,TN=tn,FP=fp,FN=fn,
        accuracy=(tp+tn)/len(rows),precision=p,recall=rec,f1=2*p*rec/(p+rec) if p+rec else 0,
        mean_steps=sum(r['steps'] for r in results)/len(rows),
        majority_accuracy=sum(r['actual']==0 for r in results)/len(rows))
    out=ROOT.parent/'10 лабораторная'/'результаты'
    out.mkdir(exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'traces.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        keys=['transaction_id','actual','predicted','decision','risk_score','steps']
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore'); writer.writeheader(); writer.writerows(results)
    print(json.dumps(metrics,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
