"""Analyse de faisabilité pour un ordonnanceur à priorités fixes.

Ce module implémente la méthode d'analyse du temps de réponse pour vérifier
la faisabilité d'un ensemble de tâches lorsque les priorités sont fixées selon
différentes politiques « Highest Priority First » (HPF/RM) ou « Deadline
Monotonic » (DM).
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from ordonnanceur_edf.task import EPSILON, Task


def assign_priorities(tasks: Sequence[Task], policy: str) -> list[Task]:
    """Retourne les tâches triées par ordre de priorité selon une politique donnée.
    Parameters
    ----------
    tasks:
        Tâches à ordonnancer.
    policy:
        Politique d'ordonnancement souhaitée. ``"RM"`` (Rate Monotonic) classe les
        tâches par période croissante. ``"DM"`` (Deadline Monotonic) les classe par
        échéance relative croissante. ``"HPF"`` est accepté comme alias de ``"RM"``.

    Returns
    -------
    list[Task]
        Nouvelle liste ordonnée de la plus haute à la plus basse priorité.

    Raises
    ------
    ValueError
        Si la politique n'est pas reconnue.
    """

    try:
        normalized = policy.upper()
    except AttributeError as exc:  # pragma: no cover - validation
        raise TypeError("Policy must be provided as a string.") from exc

    if normalized == "HPF":
        normalized = "RM"

    if normalized == "RM":
        key = lambda task: (task.period, task.deadline, task.name)
    elif normalized == "DM":
        key = lambda task: (task.deadline, task.period, task.name)
    else:  # pragma: no cover - validation
        raise ValueError(
            f"Unknown priority assignment policy: {policy}. Expected 'HPF', 'RM' or 'DM'."
        )

    return sorted(tasks, key=key)

def _compute_response_time(task: Task,higher_priority_tasks: Iterable[Task],blocking: float = 0.0,) -> float | None:
    """Calcule le pire temps de réponse pour ``task``.

    Parameters
    ----------
    task:
        Tâche analysée.
    higher_priority_tasks:
        Tâches de priorité strictement supérieure à ``task``.

    blocking:
        Durée de blocage potentielle due aux tâches de priorité plus faible.

    Returns
    -------
    float | None
        Temps de réponse convergé si la tâche est faisable, ``None`` sinon.
    """

    if task.offset > EPSILON:
        raise ValueError(
            "Response-time analysis with HPF requires synchronous releases (offset=0)."
        )

    response = task.computation_time + blocking
    higher = list(higher_priority_tasks)

    for _ in range(1000):
        interference = 0.0
        for hp_task in higher:
            interference += math.ceil(response / hp_task.period) * hp_task.computation_time

        next_response = task.computation_time + blocking + interference
        if next_response > task.deadline + EPSILON:
            return None

        if abs(next_response - response) <= EPSILON:
            return next_response

        response = next_response

    raise RuntimeError("Response-time analysis did not converge")


def check_feasibility(tasks: Sequence[Task], policy: str = "HPF", preemptive: bool = True) -> bool:
    """Vérifie la faisabilité d'un ensemble de tâches à priorités fixes.

    Parameters
    ----------
    tasks:
        Liste de tâches périodiques.

    policy:
        Politique utilisée pour l'assignation des priorités.

    preemptive:
        ``True`` pour un modèle préemptif, ``False`` pour un modèle non préemptif.

    Returns
    -------
    bool
        ``True`` si toutes les tâches respectent leurs échéances, ``False`` sinon.
    """

    ordered_tasks = assign_priorities(tasks, policy)

    for index, task in enumerate(ordered_tasks):
        higher = ordered_tasks[:index]
        if preemptive:
            blocking = 0.0
        else:
            lower = ordered_tasks[index + 1 :]
            blocking = max((lp_task.computation_time for lp_task in lower), default=0.0)

        response = _compute_response_time(task, higher, blocking=blocking)
        if response is None:
            return False

    return True


__all__ = ["assign_priorities", "check_feasibility"]