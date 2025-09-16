"""Analyse de faisabilité pour un ordonnanceur à priorités fixes.

Ce module implémente la méthode d'analyse du temps de réponse pour vérifier
la faisabilité d'un ensemble de tâches lorsque les priorités sont fixées selon
une politique « Highest Priority First » (HPF). Les priorités sont ici
attribuées sur la période des tâches : plus la période est courte, plus la
priorité est élevée (ordonnancement de type Rate Monotonic).
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from ordonnanceur_edf.task import EPSILON, Task


def _order_by_priority(tasks: Sequence[Task]) -> list[Task]:
    """Retourne les tâches triées de la plus haute à la plus basse priorité."""

    return sorted(tasks, key=lambda task: (task.period, task.deadline, task.name))


def _compute_response_time(task: Task, higher_priority_tasks: Iterable[Task]) -> float | None:
    """Calcule le pire temps de réponse pour ``task``.

    Parameters
    ----------
    task:
        Tâche analysée.
    higher_priority_tasks:
        Tâches de priorité strictement supérieure à ``task``.

    Returns
    -------
    float | None
        Temps de réponse convergé si la tâche est faisable, ``None`` sinon.
    """

    if task.offset > EPSILON:
        raise ValueError(
            "Response-time analysis with HPF requires synchronous releases (offset=0)."
        )

    response = task.computation_time
    higher = list(higher_priority_tasks)

    for _ in range(1000):
        interference = 0.0
        for hp_task in higher:
            interference += math.ceil(response / hp_task.period) * hp_task.computation_time

        next_response = task.computation_time + interference
        if next_response > task.deadline + EPSILON:
            return None

        if abs(next_response - response) <= EPSILON:
            return next_response

        response = next_response

    raise RuntimeError("Response-time analysis did not converge")


def check_feasibility(tasks: list[Task]) -> bool:
    """Vérifie la faisabilité d'un ensemble de tâches HPF via l'analyse du temps.

    Parameters
    ----------
    tasks:
        Liste de tâches périodiques.

    Returns
    -------
    bool
        ``True`` si toutes les tâches respectent leurs échéances, ``False`` sinon.
    """

    ordered_tasks = _order_by_priority(tasks)

    for index, task in enumerate(ordered_tasks):
        higher = ordered_tasks[:index]
        response = _compute_response_time(task, higher)
        if response is None:
            return False

    return True


__all__ = ["check_feasibility"]