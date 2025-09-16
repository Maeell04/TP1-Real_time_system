"""Data structures for EDF scheduling tasks and jobs.

Ce module contient les classes de base utilisées par le simulateur EDF.
On y trouve la représentation d'une tâche périodique ainsi que les jobs
générés pour la simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

EPSILON = 1e-9


@dataclass
class Task:
    """Représentation d'une tâche périodique.

    Attributes
    ----------
    name:
        Nom de la tâche, utilisé pour les traces.
    computation_time:
        Durée d'exécution (C).
    period:
        Période de répétition (T).
    deadline:
        Échéance relative (D). Si ``None``, on considère ``deadline = period``.
    offset:
        Date de première libération de la tâche.
    """

    name: str
    computation_time: float
    period: float
    deadline: float | None = None
    offset: float = 0.0

    def __post_init__(self) -> None:
        try:
            self.computation_time = float(self.computation_time)
            self.period = float(self.period)
            self.offset = float(self.offset)
        except (TypeError, ValueError) as exc:  # pragma: no cover - validation
            raise TypeError(
                f"Numeric values are required for task '{self.name}'."
            ) from exc

        if self.deadline is None:
            self.deadline = self.period
        else:
            try:
                self.deadline = float(self.deadline)
            except (TypeError, ValueError) as exc:  # pragma: no cover - validation
                raise TypeError(
                    f"Numeric values are required for task '{self.name}'."
                ) from exc

        if self.computation_time <= 0:
            raise ValueError(
                f"Computation time must be positive for task '{self.name}'."
            )
        if self.period <= 0:
            raise ValueError(
                f"Period must be positive for task '{self.name}'."
            )
        if self.deadline <= 0:
            raise ValueError(
                f"Deadline must be positive for task '{self.name}'."
            )
        if self.offset < 0:
            raise ValueError(
                f"Offset cannot be negative for task '{self.name}'."
            )

    @property
    def utilization(self) -> float:
        """Retourne l'utilisation ``C/T`` de la tâche."""

        return self.computation_time / self.period

    def generate_jobs(
        self, horizon: float, *, include_job_at_horizon: bool = True
    ) -> List["Job"]:
        """Génère les jobs libérés avant une certaine date.

        Parameters
        ----------
        horizon:
            Date limite (incluse si ``include_job_at_horizon`` est ``True``).
        include_job_at_horizon:
            Inclure ou non les jobs libérés exactement à ``horizon``.
        """

        try:
            horizon = float(horizon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - validation
            raise TypeError("Horizon must be a numeric value") from exc

        if horizon < 0:
            raise ValueError("Horizon must be non negative")

        limit = horizon
        if include_job_at_horizon:
            limit += EPSILON

        jobs: List[Job] = []
        instance = 1
        while True:
            release = self.offset + (instance - 1) * self.period
            if release > limit + EPSILON:
                break

            jobs.append(
                Job(
                    task=self,
                    release_time=release,
                    instance=instance,
                    absolute_deadline=release + self.deadline,
                    remaining_time=self.computation_time,
                )
            )
            instance += 1

        return jobs


@dataclass
class Job:
    """Instance d'exécution d'une tâche."""

    task: Task
    release_time: float
    instance: int
    absolute_deadline: float
    remaining_time: float
    started_at: float | None = None
    completed_at: float | None = None

    @property
    def deadline_missed(self) -> bool:
        """Indique si le job a dépassé son échéance."""

        if self.completed_at is None:
            return False
        return self.completed_at - self.absolute_deadline > EPSILON


__all__ = ["Task", "Job", "EPSILON"]