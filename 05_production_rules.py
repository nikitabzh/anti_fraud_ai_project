import json
import os

print(
    ">>> [ЛАБА 11 / ПРОДУКЦИИ] Инициализация базы продукционных правил..."
)

# 1. Формирование базы правил (16 правил)
rules_data = [
    {
        "id": "R001",
        "group": "Limits",
        "priority": 2,
        "if": {
            "amt_bin": "Small",
            "is_trusted_device": True,
            "tx_velocity_1h": 1,
        },
        "then": {"decision": "Approve", "risk_score": 0},
        "description": "Обычная микро-покупка с доверенного устройства",
    },
    {
        "id": "R002",
        "group": "Limits",
        "priority": 3,
        "if": {
            "is_amount_outlier": 1,
            "is_trusted_device": True,
            "is_night_tx": 0,
        },
        "then": {"decision": "Challenge_2FA", "risk_score": 45},
        "description": "Крупная дневная покупка с доверенного устройства",
    },
    {
        "id": "R003",
        "group": "Limits",
        "priority": 5,
        "if": {"amt_bin": "Extreme", "is_trusted_device": False},
        "then": {"decision": "Decline_Block", "risk_score": 90},
        "description": (
            "Экстремально крупная сумма с нового неизвестного устройства"
        ),
    },
    {
        "id": "R004",
        "group": "Limits",
        "priority": 4,
        "if": {"amt_bin": "Large", "card_type": "credit", "is_night_tx": 1},
        "then": {"decision": "Challenge_2FA", "risk_score": 60},
        "description": "Крупный ночной расход кредитного лимита",
    },
    {
        "id": "R005",
        "group": "Devices",
        "priority": 2,
        "if": {"device_type": "offline_pos", "is_amount_outlier": 0},
        "then": {"decision": "Approve", "risk_score": 0},
        "description": "Офлайн-оплата на кассе в пределах обычного чека",
    },
    {
        "id": "R006",
        "group": "Devices",
        "priority": 4,
        "if": {
            "is_trusted_device": False,
            "device_type": {"!=": "offline_pos"},
            "is_night_tx": 1,
        },
        "then": {"decision": "Challenge_2FA", "risk_score": 55},
        "description": "Ночной онлайн-платеж с нового устройства",
    },
    {
        "id": "R007",
        "group": "Devices",
        "priority": 5,
        "if": {"device_fraud_history": {">=": 2}},
        "then": {"decision": "Decline_Block", "risk_score": 95},
        "description": (
            "Вход с устройства, замеченного в атаках (Данные Графа Знаний)"
        ),
    },
    {
        "id": "R008",
        "group": "Devices",
        "priority": 4,
        "if": {"os_family": "Other", "is_amount_outlier": 1},
        "then": {"decision": "Challenge_2FA", "risk_score": 65},
        "description": "Крупная покупка с подозрительной нестандартной ОС",
    },
    {
        "id": "R009",
        "group": "Identity",
        "priority": 3,
        "if": {
            "is_unknown_geo": 1,
            "is_free_email": 1,
            "amt_bin": {"!=": "Small"},
        },
        "then": {"decision": "Challenge_2FA", "risk_score": 50},
        "description": (
            "Неизвестный регион биллинга в сочетании с бесплатной почтой"
        ),
    },
    {
        "id": "R010",
        "group": "Identity",
        "priority": 5,
        "if": {"is_risky_email": 1, "is_amount_outlier": 1},
        "then": {"decision": "Decline_Block", "risk_score": 85},
        "description": "Анонимная почта при транзакции с аномальной суммой",
    },
    {
        "id": "R011",
        "group": "Identity",
        "priority": 2,
        "if": {
            "is_unknown_geo": 1,
            "is_trusted_device": True,
            "amt_bin": "Small",
        },
        "then": {"decision": "Approve", "risk_score": 15},
        "description": "Мелкая доверенная покупка в поездке (новый регион)",
    },
    {
        "id": "R012",
        "group": "Identity",
        "priority": 3,
        "if": {"is_risky_email": 1, "amt_bin": "Small"},
        "then": {"decision": "Challenge_2FA", "risk_score": 40},
        "description": "Анонимный почтовый сервис даже при малой сумме",
    },
    {
        "id": "R013",
        "group": "Velocity",
        "priority": 5,
        "if": {"tx_velocity_1h": {">=": 5}},
        "then": {"decision": "Decline_Block", "risk_score": 90},
        "description": "Аномальный всплеск частоты (5 и более оплат за час)",
    },
    {
        "id": "R014",
        "group": "Velocity",
        "priority": 3,
        "if": {"tx_velocity_1h": {">=": 3, "<": 5}},
        "then": {"decision": "Challenge_2FA", "risk_score": 50},
        "description": "Повышенная частота транзакций (3-4 покупки в час)",
    },
    {
        "id": "R015",
        "group": "Velocity",
        "priority": 5,
        "if": {
            "is_night_tx": 1,
            "tx_velocity_1h": {">=": 2},
            "is_trusted_device": False,
        },
        "then": {"decision": "Decline_Block", "risk_score": 88},
        "description": "Серия ночных списаний с нового оборудования",
    },
    {
        "id": "R016",
        "group": "Default",
        "priority": 1,
        "if": {
            "is_trusted_device": True,
            "is_amount_outlier": 0,
            "tx_velocity_1h": 1,
        },
        "then": {"decision": "Approve", "risk_score": 0},
        "description": "Базовое доверенное поведение пользователя",
    },
]

# Сохранение в файл rules.json
os.makedirs("data", exist_ok=True)
with open("data/rules.json", "w", encoding="utf-8") as f:
    json.dump(rules_data, f, ensure_ascii=False, indent=2)
print(">>> База правил успешно сохранена в data/rules.json (16 правил)\n")


# 2. Механизм логического вывода (Inference Engine)
def check_condition(fact_val, condition):
    if isinstance(condition, dict):
        for op, target in condition.items():
            if op == "!=" and fact_val == target:
                return False
            if op == ">=" and not (fact_val >= target):
                return False
            if op == "<" and not (fact_val < target):
                return False
            if op == "<=" and not (fact_val <= target):
                return False
            if op == ">" and not (fact_val > target):
                return False
        return True
    return fact_val == condition


def evaluate_transaction(facts, rules):
    conflict_set = []

    for rule in rules:
        matched = True
        for key, cond in rule["if"].items():
            fact_val = facts.get(key)
            if fact_val is None or not check_condition(fact_val, cond):
                matched = False
                break
        if matched:
            conflict_set.append(rule)

    if not conflict_set:
        return {"decision": "Approve", "risk_score": 0, "rules_triggered": []}

    # Разрешение конфликтов: сортировка по приоритету (убывание) и числу условий (специфичность)
    conflict_set.sort(key=lambda r: (r["priority"], len(r["if"])), reverse=True)

    winning_rule = conflict_set[0]
    max_risk = max(r["then"]["risk_score"] for r in conflict_set)
    triggered_ids = [r["id"] for r in conflict_set]

    return {
        "decision": winning_rule["then"]["decision"],
        "risk_score": max_risk,
        "winning_rule": winning_rule["id"],
        "conflict_set": triggered_ids,
        "explanation": winning_rule["description"],
    }


# 3. Тестирование 5 контрольных примеров
test_cases = [
    {
        "name": "Тест 1: Стандартная мелкая дневная покупка",
        "facts": {
            "amt_bin": "Small",
            "is_trusted_device": True,
            "tx_velocity_1h": 1,
            "is_night_tx": 0,
            "is_amount_outlier": 0,
        },
    },
    {
        "name": "Тест 2: Крупная дневная покупка с доверенного ноутбука",
        "facts": {
            "amt_bin": "Large",
            "is_trusted_device": True,
            "is_amount_outlier": 1,
            "is_night_tx": 0,
            "tx_velocity_1h": 1,
        },
    },
    {
        "name": "Тест 3: Экстремальный ночной платеж с анонимной почты",
        "facts": {
            "amt_bin": "Extreme",
            "is_trusted_device": False,
            "is_amount_outlier": 1,
            "is_risky_email": 1,
            "is_night_tx": 1,
            "device_type": "mobile",
        },
    },
    {
        "name": "Тест 4: Атака с устройства, замеченного в ботнет-ферме",
        "facts": {
            "device_fraud_history": 8,
            "amt_bin": "Medium",
            "is_trusted_device": False,
        },
    },
    {
        "name": "Тест 5: Всплеск ночной активности (серия транзакций)",
        "facts": {
            "is_night_tx": 1,
            "tx_velocity_1h": 3,
            "is_trusted_device": False,
            "device_type": "mobile",
        },
    },
]

print("=" * 70)
print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ БАЗЫ ПРОДУКЦИОННЫХ ПРАВИЛ")
print("=" * 70)

for idx, tc in enumerate(test_cases, 1):
    res = evaluate_transaction(tc["facts"], rules_data)
    print(f"\n{tc['name']}:")
    print(f"  Входные факты: {tc['facts']}")
    print(f"  Сработавшие правила (Conflict Set): {res['conflict_set']}")
    print(
        f"  Итоговое решение: [{res['decision']}] | Балл риска:"
        f" {res['risk_score']}"
    )
    print(
        f"  Победившее правило: {res.get('winning_rule')} ->"
        f" {res.get('explanation')}"
    )

print("\n" + "=" * 70)
print(">>> [ЛАБА 11] Все тесты завершены успешно!")