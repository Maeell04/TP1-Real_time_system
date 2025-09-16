"""Interface terminale pour l'analyse de faisabilité HPF/RM/DM."""

from __future__ import annotations

from typing import List

from .analysis import FeasibilityReport, check_feasibility
from .task import StaticTask


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _prompt_int(prompt: str, *, min_value: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw:
            print("Une valeur est obligatoire.")
            continue
        try:
            value = int(raw)
        except ValueError:
            print("Veuillez saisir un entier valide.")
            continue
        if min_value is not None and value < min_value:
            print(f"La valeur doit être supérieure ou égale à {min_value}.")
            continue
        return value


def _prompt_float(
    prompt: str,
    *,
    min_value: float | None = None,
    allow_empty: bool = False,
    strictly_positive: bool = False,
) -> float | None:
    while True:
        raw = input(prompt).strip()
        if not raw:
            if allow_empty:
                return None
            print("Une valeur est obligatoire.")
            continue
        normalized = raw.replace(",", ".")
        try:
            value = float(normalized)
        except ValueError:
            print("Veuillez saisir un nombre valide.")
            continue
        if strictly_positive and value <= 0:
            print("La valeur doit être strictement positive.")
            continue
        if min_value is not None and value < min_value:
            print(f"La valeur doit être supérieure ou égale à {min_value}.")
            continue
        return value


def _prompt_optional_int(prompt: str, *, min_value: int | None = None) -> int | None:
    while True:
        raw = input(prompt).strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            print("Veuillez saisir un entier valide.")
            continue
        if min_value is not None and value < min_value:
            print(f"La valeur doit être supérieure ou égale à {min_value}.")
            continue
        return value


def _prompt_non_empty(prompt: str) -> str:
    while True:
        raw = input(prompt).strip()
        if not raw:
            print("Ce champ est obligatoire.")
            continue
        return raw


def _prompt_policy() -> str:
    while True:
        raw = input("Politique (HPF / RM / DM) : ").strip().upper()
        if raw in {"HPF", "RM", "DM"}:
            return raw
        print("Veuillez choisir parmi HPF, RM ou DM.")


def _prompt_preemption() -> bool:
    while True:
        raw = input("Mode préemptif ? (o/n) : ").strip().lower()
        if raw in {"o", "oui", "y", "yes"}:
            return True
        if raw in {"n", "non", "no"}:
            return False
        print("Réponse invalide. Saisissez 'o' pour oui ou 'n' pour non.")


def _collect_tasks() -> List[StaticTask]:
    tasks: List[StaticTask] = []
    task_count = _prompt_int("Combien de tâches souhaitez-vous définir ? ", min_value=1)

    for index in range(task_count):
        print(f"\nTâche #{index + 1}")
        while True:
            name = _prompt_non_empty("  Nom : ")
            computation = _prompt_float(
                "  Durée d'exécution (C) : ", strictly_positive=True
            )
            period = _prompt_float("  Période (T) : ", strictly_positive=True)
            deadline = _prompt_float(
                "  Échéance (D) [laisser vide pour D=T] : ",
                allow_empty=True,
                strictly_positive=True,
            )
            priority = _prompt_optional_int(
                "  Priorité (entier, laisser vide si inconnu) : ", min_value=1
            )

            try:
                task = StaticTask(
                    name=name,
                    computation_time=computation,
                    period=period,
                    deadline=deadline,
                    priority=priority,
                )
            except (TypeError, ValueError) as exc:
                print(f"  Erreur : {exc}")
                print("  Recommencez la saisie de cette tâche.")
                continue

            tasks.append(task)
            break

    return tasks


def _ensure_priorities(tasks: List[StaticTask]) -> None:
    used_values: set[int] = set()
    for task in tasks:
        if task.priority is not None:
            if task.priority in used_values:
                print(
                    f"La priorité {task.priority} est déjà utilisée, elle va être redéfinie"
                )
                task.priority = None
            else:
                used_values.add(task.priority)

    for task in tasks:
        while task.priority is None:
            value = _prompt_int(
                f"Priorité pour {task.name} (entier, plus petit = plus prioritaire) : ",
                min_value=1,
            )
            if value in used_values:
                print("Cette priorité est déjà utilisée. Choisissez une autre valeur.")
                continue
            task.priority = value
            used_values.add(value)


def _print_report(report: FeasibilityReport) -> None:
    header_mode = "préemptif" if report.preemptive else "non préemptif"
    print("\n=== Résultats de l'analyse ===")
    print(f"Politique : {report.policy} | Mode : {header_mode}")

    if not report.results:
        print("Aucune tâche à analyser.")
        return

    print("\nPriorité | Tâche       | R (temps de réponse) | D (échéance) | Blocage | Statut")
    print("-" * 79)
    for result in report.results:
        response = _format_number(result.response_time)
        deadline = _format_number(result.task.deadline)
        blocking = _format_number(result.blocking_time)
        status = "OK" if result.deadline_met else "DÉPASSÉE"
        priority_label = (
            f"{result.task.priority}" if report.policy == "HPF" else str(result.priority_rank)
        )
        print(
            f"{priority_label:^9}| {result.task.name:<11}| {response:^21}| "
            f"{deadline:^11}| {blocking:^8}| {status:>9}"
        )

    print("\nFaisabilité globale : ", "OUI" if report.feasible else "NON")


def main() -> None:
    print("=== Analyse de faisabilité à priorité fixe ===")
    tasks = _collect_tasks()
    policy = _prompt_policy()

    if policy == "HPF":
        _ensure_priorities(tasks)

    preemptive = _prompt_preemption()
    input("\nAppuyez sur Entrée pour lancer l'analyse...")

    try:
        report = check_feasibility(tasks, policy, preemptive=preemptive)
    except ValueError as exc:
        print(f"\nErreur lors de l'analyse : {exc}")
        return
    except RuntimeError as exc:
        print(f"\nErreur lors du calcul du temps de réponse : {exc}")
        return

    _print_report(report)


if __name__ == "__main__":
    main()