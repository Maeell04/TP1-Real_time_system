"""Interface en ligne de commande pour l'analyse à priorités fixes des tâches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    import sys

    PACKAGE_ROOT = Path(__file__).resolve().parent
    sys.path.insert(0, str(PACKAGE_ROOT.parent))

from ordonnanceur_edf.task import Task
from ordonnanceur_statique.hpf import assign_priorities, check_feasibility

DEFAULT_TASKS = [
    {"name": "T1", "computation_time": 1, "period": 4, "deadline": 4},
    {"name": "T2", "computation_time": 1, "period": 5, "deadline": 5},
    {"name": "T3", "computation_time": 2, "period": 10, "deadline": 10},
]


def format_time(value: float) -> str:
    """Formate une valeur temporelle pour l'affichage."""

    rounded = round(value)
    if abs(value - rounded) < 1e-9:
        return str(int(rounded))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def load_tasks(path: Path) -> list[Task]:
    """Charge une liste de tâches depuis un fichier JSON."""

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if isinstance(raw, dict):
        if "tasks" not in raw:
            raise ValueError("Le fichier JSON doit contenir une clé 'tasks'.")
        raw_tasks = raw["tasks"]
    elif isinstance(raw, list):
        raw_tasks = raw
    else:
        raise ValueError("Structure JSON invalide pour décrire des tâches.")

    tasks = [Task(**item) for item in raw_tasks]
    return tasks


def build_default_tasks() -> list[Task]:
    """Construit un jeu de tâches par défaut pour l'analyse."""

    return [Task(**data) for data in DEFAULT_TASKS]


def describe_tasks(tasks: Sequence[Task], policy: str, unit: str) -> None:
    """Affiche un résumé des tâches et de leurs priorités."""

    if not tasks:
        print("Aucune tâche fournie.")
        return

    print("Tâches analysées :")
    total_utilization = 0.0
    for task in tasks:
        total_utilization += task.utilization
        deadline = format_time(task.deadline)
        print(
            f"  - {task.name:<8} : C={format_time(task.computation_time)} {unit}, "
            f"T={format_time(task.period)} {unit}, D={deadline} {unit}, "
            f"U={task.utilization:.3f}"
        )

    ordered = assign_priorities(tasks, policy)
    priority_chain = " > ".join(task.name for task in ordered)
    print(f"Utilisation totale : {total_utilization:.3f}")
    print(f"Priorités {policy.upper()} (du plus élevé au plus faible) : {priority_chain}")
    

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Analyse les arguments de la ligne de commande."""

    parser = argparse.ArgumentParser(
        description=(
            "Vérifie la faisabilité d'un ensemble de tâches à priorités fixes "
            "(HPF/RM/DM)."
        ),
    )
    parser.add_argument(
        "--tasks",
        type=Path,
        help="Fichier JSON décrivant les tâches (sinon un exemple est utilisé).",
    )
    parser.add_argument(
        "--time-unit",
        default="s",
        help="Unité de temps affichée (par défaut : secondes).",
    )
    parser.add_argument(
        "--policy",
        choices=["HPF", "RM", "DM"],
        default="HPF",
        help=(
            "Politique d'assignation des priorités : HPF (alias RM), RM ou DM."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée du script d'analyse à priorités fixes."""

    args = parse_args(argv)

    if args.tasks is not None:
        tasks = load_tasks(args.tasks)
    else:
        tasks = build_default_tasks()

    policy_label = args.policy.upper()
    describe_tasks(tasks, args.policy, args.time_unit)

    try:
        feasible = check_feasibility(list(tasks), policy=args.policy)
    except (ValueError, RuntimeError) as exc:
        print(f"Erreur lors de l'analyse : {exc}")
        raise SystemExit(1) from exc

    if feasible:
        print(f"\nRésultat : l'ensemble de tâches est faisable avec la politique {policy_label}.")
    else:
        print(f"\nRésultat : l'ensemble de tâches n'est pas faisable avec la politique {policy_label}.")


if __name__ == "__main__":
    main()