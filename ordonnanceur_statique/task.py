"""Modèles de tâches pour l'ordonnancement à priorité fixe."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StaticTask:
    """Tâche périodique utilisée pour l'analyse de faisabilité HPF/RM/DM."""

    name: str
    computation_time: float
    period: float
    deadline: float | None = None
    priority: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Task name must be a non-empty string")
        self.name = self.name.strip()

        try:
            self.computation_time = float(self.computation_time)
            self.period = float(self.period)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"Numeric values are required for task '{self.name}'."
            ) from exc

        if self.deadline is None:
            self.deadline = self.period
        else:
            try:
                self.deadline = float(self.deadline)
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    f"Numeric values are required for task '{self.name}'."
                ) from exc

        if self.priority is not None:
            try:
                self.priority = int(self.priority)
            except (TypeError, ValueError) as exc:
                raise TypeError("Priority must be an integer value") from exc

        if self.computation_time <= 0:
            raise ValueError(
                f"Computation time must be positive for task '{self.name}'."
            )
        if self.period <= 0:
            raise ValueError(f"Period must be positive for task '{self.name}'.")
        if self.deadline <= 0:
            raise ValueError(
                f"Deadline must be positive for task '{self.name}'."
            )

    @property
    def utilization(self) -> float:
        """Retourne l'utilisation ``C/T`` de la tâche."""

        return self.computation_time / self.period


__all__ = ["StaticTask"]