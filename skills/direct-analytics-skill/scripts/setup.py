#!/usr/bin/env python3
"""
Мастер настройки проекта direct-analytics-skill.
Управление конфигами для нескольких кабинетов Яндекс.Директ + Метрика.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(os.environ.get("DIRECT_ANALYTICS_DATA_DIR", str(Path.home() / ".direct_analytics"))).expanduser()


def get_projects() -> dict:
    """Возвращает словарь {name: config_path} всех проектов."""
    projects = {}
    if BASE_DIR.exists():
        for p in BASE_DIR.iterdir():
            cfg = p / "config.json"
            if p.is_dir() and cfg.exists():
                projects[p.name] = cfg
    return projects


def load_config(project: str) -> dict:
    cfg_path = BASE_DIR / project / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Проект '{project}' не найден. Запустите: python scripts/setup.py")
    with open(cfg_path) as f:
        return json.load(f)


def get_default_project() -> str | None:
    default_file = BASE_DIR / ".default"
    if default_file.exists():
        name = default_file.read_text().strip()
        if (BASE_DIR / name / "config.json").exists():
            return name
    # Если нет дефолта — берём единственный проект, если он один
    projects = get_projects()
    if len(projects) == 1:
        return list(projects.keys())[0]
    return None


def resolve_project(project_arg: str | None) -> str:
    if project_arg:
        return project_arg
    default = get_default_project()
    if default:
        return default
    projects = get_projects()
    if not projects:
        print("❌ Нет настроенных проектов. Запустите: python scripts/setup.py")
        sys.exit(1)
    print("Доступные проекты:")
    for name in projects:
        print(f"  - {name}")
    print("Укажите проект: python scripts/collect.py --project NAME")
    sys.exit(1)


def prompt(label: str, default: str = "", secret: bool = False) -> str:
    """Интерактивный prompt с дефолтным значением."""
    import getpass
    if default:
        label = f"{label} [{default}]"
    label += ": "
    if secret:
        value = getpass.getpass(label)
    else:
        value = input(label).strip()
    return value if value else default


def create_project(name: str | None = None) -> str:
    """Интерактивный wizard создания нового проекта."""
    print("\n=== Настройка нового проекта ===\n")

    if not name:
        name = prompt("Название проекта (латиница, без пробелов)").replace(" ", "_")
    if not name:
        print("❌ Название обязательно")
        sys.exit(1)

    project_dir = BASE_DIR / name
    project_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = project_dir / "config.json"
    existing = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            existing = json.load(f)
        print(f"⚠️  Проект '{name}' уже существует. Значения в [] — текущие.\n")

    print("Получить токены: https://yandex.ru/dev/direct/doc/dg/concepts/auth-token.html\n")

    config = {
        "project_name": name,
        "DIRECT_TOKEN":  prompt("OAuth-токен Яндекс.Директ", existing.get("DIRECT_TOKEN", ""), secret=True),
        "DIRECT_LOGIN":  prompt("Логин клиентского кабинета Директа", existing.get("DIRECT_LOGIN", "")),
        "METRIKA_TOKEN": prompt("OAuth-токен Яндекс.Метрики", existing.get("METRIKA_TOKEN", ""), secret=True),
        "METRIKA_COUNTER": prompt("ID счётчика Метрики", existing.get("METRIKA_COUNTER", "")),
        "METRIKA_GOAL_IDS": prompt(
            "ID целей для конверсий (через запятую; Enter = все)",
            existing.get("METRIKA_GOAL_IDS", ""),
        ),
        "CURRENCY": prompt("Валюта кабинета", existing.get("CURRENCY", "RUB")),
        "REPORT_TIMEZONE": prompt(
            "Timezone отчётов (IANA)", existing.get("REPORT_TIMEZONE", "Europe/Moscow")
        ),
        "UTM_SOURCE": prompt(
            "UTM source для Директа", existing.get("UTM_SOURCE", "yandex")
        ),
        "UTM_MEDIUM": prompt(
            "UTM medium для Директа", existing.get("UTM_MEDIUM", "cpc")
        ),
        "UTM_CAMPAIGN_MAPPING": prompt(
            "Как utm_campaign сопоставляется с Директом (campaign_id/campaign_name)",
            existing.get("UTM_CAMPAIGN_MAPPING", "campaign_id"),
        ),
        "ATTRIBUTION_MODE": "parallel",
        "ALLOW_LEGACY_CAMPAIGN_NAME_MATCH": existing.get("ALLOW_LEGACY_CAMPAIGN_NAME_MATCH", False),
        "GUARDRAILS": existing.get("GUARDRAILS", {}),
        "MONITOR_METRICS": existing.get(
            "MONITOR_METRICS", ["Cost", "Clicks", "MetrikaRevenue", "MetrikaTransactions"]
        ),
        "COHORT_RULES": existing.get("COHORT_RULES", {}),
    }

    with open(cfg_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Проект '{name}' сохранён: {cfg_path}")

    # Предложить сделать дефолтным
    if not get_default_project():
        make_default = input("Сделать проект дефолтным? [Y/n]: ").strip().lower()
        if make_default != "n":
            (BASE_DIR / ".default").write_text(name)
            print(f"✅ '{name}' — проект по умолчанию")

    return name


def list_projects():
    projects = get_projects()
    default = get_default_project()
    if not projects:
        print("Нет настроенных проектов. Запустите: python scripts/setup.py")
        return
    print("\nПроекты:")
    for name, cfg_path in projects.items():
        marker = " (default)" if name == default else ""
        print(f"  • {name}{marker}")
    print()


def show_project(name: str):
    try:
        cfg = load_config(name)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    # Маскируем токены
    display = {k: ("***" if "TOKEN" in k else v) for k, v in cfg.items()}
    print(f"\nПроект: {name}")
    for k, v in display.items():
        print(f"  {k}: {v}")
    print()


def set_default(name: str):
    if not (BASE_DIR / name / "config.json").exists():
        print(f"❌ Проект '{name}' не найден")
        return
    (BASE_DIR / ".default").write_text(name)
    print(f"✅ Проект по умолчанию: {name}")


def main():
    parser = argparse.ArgumentParser(description="Управление проектами direct-analytics-skill")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--new", action="store_true", help="Создать новый проект")
    group.add_argument("--list", action="store_true", help="Список проектов")
    group.add_argument("--show", metavar="NAME", help="Показать конфиг проекта")
    group.add_argument("--set-default", metavar="NAME", help="Установить проект по умолчанию")
    group.add_argument("--edit", metavar="NAME", help="Редактировать существующий проект")
    args = parser.parse_args()

    if args.list:
        list_projects()
    elif args.show:
        show_project(args.show)
    elif args.set_default:
        set_default(args.set_default)
    elif args.edit:
        create_project(args.edit)
    elif args.new:
        create_project()
    else:
        # Без аргументов — wizard для нового проекта
        projects = get_projects()
        if projects:
            print("Существующие проекты:")
            for name in projects:
                print(f"  • {name}")
            action = input("\n[N] новый проект / [E] редактировать: ").strip().lower()
            if action == "e":
                name = input("Имя проекта: ").strip()
                create_project(name)
                return
        create_project()


if __name__ == "__main__":
    main()
