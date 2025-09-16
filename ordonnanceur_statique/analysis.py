"""Analyse de faisabilité pour l'ordonnancement à priorité fixe."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .task import StaticTask

EPSILON = 1e-9
MAX_ITERATIONS = 1000


@dataclass
class ResponseTimeResult:
    """Résultat de l'analyse du temps de réponse pour une tâche."""

    task: StaticTask
    response_time: float
    deadline_met: bool
    iterations: int
    blocking_time: float
    priority_rank: int


@dataclass
class FeasibilityReport:
    """Synthèse des résultats de faisabilité."""

    feasible: bool
    policy: str
    preemptive: bool
    results: List[ResponseTimeResult]


def _order_tasks(tasks: Sequence[StaticTask], policy: str) -> List[StaticTask]:
    policy_upper = policy.upper()
    if policy_upper == "HPF":
        missing = [task.name for task in tasks if task.priority is None]
        if missing:
            missing_names = ", ".join(missing)
            raise ValueError(
                "HPF nécessite une priorité pour chaque tâche : "
                f"{missing_names}"
            )
        priorities = [task.priority for task in tasks if task.priority is not None]
        if len(set(priorities)) != len(priorities):
            raise ValueError("Les priorités HPF doivent être uniques")
        ordered = sorted(tasks, key=lambda task: (-task.priority, task.name))
    elif policy_upper == "RM":
        ordered = sorted(tasks, key=lambda task: (task.period, task.deadline, task.name))
    elif policy_upper == "DM":
        ordered = sorted(tasks, key=lambda task: (task.deadline, task.period, task.name))
    else:
        raise ValueError(
            "Politique inconnue. Valeurs attendues : HPF, RM ou DM"
        )
    return list(ordered)


def _compute_blocking_time(
    index: int, ordered: Sequence[StaticTask], preemptive: bool
) -> float:
    if preemptive:
        return 0.0
    lower_priority = ordered[index + 1 :]
    if not lower_priority:
        return 0.0
    return max(task.computation_time for task in lower_priority)


def _compute_response_time(
    task: StaticTask,
    higher_priority: Iterable[StaticTask],
    blocking: float,
) -> tuple[float, int]:
    higher_list = list(higher_priority)
    response = task.computation_time + blocking
    if not higher_list:
        return response, 0

    iterations = 0
    while iterations < MAX_ITERATIONS:
        interference = 0.0
        for hp_task in higher_list:
            ratio = response / hp_task.period
            interference += math.ceil(ratio - EPSILON) * hp_task.computation_time
        new_response = task.computation_time + blocking + interference
        iterations += 1

        if new_response - task.deadline > EPSILON:
            return new_response, iterations
        if abs(new_response - response) <= EPSILON:
            return new_response, iterations

        response = new_response

    raise RuntimeError(
        "Response time analysis did not converge within the iteration limit"
    )


def check_feasibility(
    tasks: Sequence[StaticTask], policy: str, *, preemptive: bool
) -> FeasibilityReport:
    """Analyse la faisabilité d'un ensemble de tâches."""

    ordered = _order_tasks(tasks, policy)
    results: List[ResponseTimeResult] = []
    feasible = True

    for idx, task in enumerate(ordered):
        blocking = _compute_blocking_time(idx, ordered, preemptive)
        response, iterations = _compute_response_time(task, ordered[:idx], blocking)
        deadline_met = response - task.deadline <= EPSILON
        if not deadline_met:
            feasible = False

        results.append(
            ResponseTimeResult(
                task=task,
                response_time=response,
                deadline_met=deadline_met,
                iterations=iterations,
                blocking_time=blocking,
                priority_rank=idx + 1,
            )
        )

    return FeasibilityReport(
        feasible=feasible,
        policy=policy.upper(),
        preemptive=preemptive,
        results=results,
    )


__all__ = [
    "FeasibilityReport",
    "ResponseTimeResult",
    "check_feasibility",
]