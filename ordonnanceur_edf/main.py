"""Simulateur EDF (Earliest Deadline First).

Ce script offre une interface en ligne de commande permettant de charger un
ensemble de tâches et d'en simuler l'exécution selon l'algorithme EDF. Le
résultat est affiché sous forme textuelle (trace temporelle et éventuels
retards d'échéance).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence
import heapq
import itertools

from task import EPSILON, Job, Task


@dataclass
class TimelineEntry:
    """Représente une portion de temps occupée par un job ou l'inactivité."""

    task: str
    job: int | None
    start: float
    end: float
    deadline: float | None
    completed: bool

    @property
    def duration(self) -> float:
        return self.end - self.start


def compute_default_horizon(tasks: Sequence[Task]) -> float:
    """Calcule un horizon de simulation par défaut."""

    if not tasks:
        return 0.0

    periods = [task.period for task in tasks]
    max_period = max(periods)

    int_periods: List[int] = []
    for value in periods:
        rounded = round(value)
        if abs(value - rounded) < EPSILON:
            int_periods.append(int(rounded))
        else:
            int_periods = []
            break

    if int_periods:
        hyperperiod = int_periods[0]
        for period in int_periods[1:]:
            hyperperiod = math.lcm(hyperperiod, period)
            if hyperperiod > 500:
                break
        if hyperperiod <= 500:
            return float(hyperperiod)

    return float(max_period * max(3, len(tasks)))


def merge_timeline(entries: Iterable[TimelineEntry]) -> List[TimelineEntry]:
    """Fusionne les segments contigus représentant le même job."""

    merged: List[TimelineEntry] = []
    for entry in entries:
        if entry.duration <= EPSILON:
            continue

        if merged:
            last = merged[-1]
            if (
                entry.task == last.task
                and entry.job == last.job
                and entry.deadline == last.deadline
                and abs(entry.start - last.end) <= EPSILON
            ):
                last.end = entry.end
                last.completed = entry.completed
                continue

        merged.append(entry)

    return merged


def simulate_edf(tasks: Sequence[Task], horizon: float) -> dict[str, object]:
    """Simule l'exécution EDF pour l'ensemble de tâches fourni."""

    if horizon < 0:
        raise ValueError("Horizon must be non negative")

    future_jobs: list[tuple[float, int, Job]] = []
    ready_jobs: list[tuple[float, float, int, Job]] = []
    release_counter = itertools.count()
    ready_counter = itertools.count()

    for task in tasks:
        for job in task.generate_jobs(horizon, include_job_at_horizon=False):
            heapq.heappush(
                future_jobs, (job.release_time, next(release_counter), job)
            )

    now = 0.0
    timeline: List[TimelineEntry] = []
    missed_deadlines: List[Job] = []
    unfinished_jobs: List[Job] = []

    while (future_jobs or ready_jobs) and now < horizon:
        while future_jobs and future_jobs[0][0] <= now:
            _, _, job = heapq.heappop(future_jobs)
            heapq.heappush(
                ready_jobs,
                (job.absolute_deadline, job.release_time, next(ready_counter), job),
            )

        if ready_jobs:
            _, _, _, job = heapq.heappop(ready_jobs)

            if job.remaining_time <= EPSILON:
                continue

            if job.started_at is None:
                job.started_at = now

            next_release_time = future_jobs[0][0] if future_jobs else float("inf")
            planned_finish = now + job.remaining_time
            next_event = min(planned_finish, next_release_time, horizon)
            execution_time = max(0.0, next_event - now)

            if execution_time <= EPSILON:
                execution_time = min(job.remaining_time, horizon - now)
                if execution_time <= EPSILON:
                    break

            segment_end = now + execution_time
            segment = TimelineEntry(
                task=job.task.name,
                job=job.instance,
                start=now,
                end=min(segment_end, horizon),
                deadline=job.absolute_deadline,
                completed=False,
            )
            timeline.append(segment)

            job.remaining_time -= execution_time
            now = segment.end

            if job.remaining_time <= EPSILON:
                job.completed_at = now
                segment.completed = True
                if job.deadline_missed:
                    missed_deadlines.append(job)
            else:
                if now < horizon:
                    heapq.heappush(
                        ready_jobs,
                        (
                            job.absolute_deadline,
                            job.release_time,
                            next(ready_counter),
                            job,
                        ),
                    )
                else:
                    unfinished_jobs.append(job)
        else:
            if not future_jobs:
                if now < horizon:
                    timeline.append(
                        TimelineEntry(
                            task="IDLE",
                            job=None,
                            start=now,
                            end=horizon,
                            deadline=None,
                            completed=True,
                        )
                    )
                    now = horizon
                break

            next_time = min(future_jobs[0][0], horizon)
            if next_time > now + EPSILON:
                timeline.append(
                    TimelineEntry(
                        task="IDLE",
                        job=None,
                        start=now,
                        end=next_time,
                        deadline=None,
                        completed=True,
                    )
                )
            now = next_time

    for _, _, _, job in ready_jobs:
        if job.remaining_time > EPSILON and job not in unfinished_jobs:
            unfinished_jobs.append(job)

    timeline = merge_timeline(timeline)

    return {
        "timeline": timeline,
        "missed_deadlines": missed_deadlines,
        "unfinished_jobs": unfinished_jobs,
        "simulation_end": min(now, horizon),
    }


def format_time(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def format_job(job: Job) -> str:
    release = format_time(job.release_time)
    deadline = format_time(job.absolute_deadline)
    return f"{job.task.name}#{job.instance} (release={release}, deadline={deadline})"


def load_tasks(path: Path) -> List[Task]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if isinstance(raw, dict):
        if "tasks" not in raw:
            raise ValueError("JSON file must contain a 'tasks' list")
        raw_tasks = raw["tasks"]
    elif isinstance(raw, list):
        raw_tasks = raw
    else:
        raise ValueError("Invalid JSON structure for tasks")

    tasks = [Task(**item) for item in raw_tasks]
    return tasks


def describe_tasks(tasks: Sequence[Task], unit: str) -> None:
    print("Tâches simulées :")
    total_utilization = 0.0
    for task in tasks:
        total_utilization += task.utilization
        deadline = format_time(task.deadline)
        print(
            f"  - {task.name:<8} : C={format_time(task.computation_time)} {unit}, "
            f"T={format_time(task.period)} {unit}, D={deadline} {unit}, "
            f"U={task.utilization:.3f}"
        )
    print(f"Utilisation totale : {total_utilization:.3f}")


def print_timeline(result: dict[str, object], unit: str) -> None:
    timeline: List[TimelineEntry] = result["timeline"]  # type: ignore[assignment]
    missed: List[Job] = result["missed_deadlines"]  # type: ignore[assignment]
    unfinished: List[Job] = result["unfinished_jobs"]  # type: ignore[assignment]
    end_time = result["simulation_end"]  # type: ignore[assignment]

    print("\nTrace EDF :")
    if not timeline:
        print("  (aucun job exécuté dans l'horizon de simulation)")
    else:
        for entry in timeline:
            start = format_time(entry.start)
            end = format_time(entry.end)
            if entry.task == "IDLE":
                print(f"  [{start}, {end}] : processeur inactif")
                continue

            deadline = format_time(entry.deadline) if entry.deadline is not None else "-"
            if entry.completed:
                status = "terminé"
            elif entry.end >= end_time - EPSILON:
                status = "en cours à l'horizon"
            else:
                status = "préempté"
            print(
                f"  [{start}, {end}] : {entry.task}#{entry.job} (deadline={deadline}) -> {status}"
            )

    if missed:
        print("\nÉchéances dépassées :")
        for job in missed:
            done = format_time(job.completed_at) if job.completed_at is not None else "?"
            print(f"  - {format_job(job)} terminé à {done}")
    else:
        print("\nAucun dépassement d'échéance détecté.")

    if unfinished:
        print("Jobs non terminés avant la fin de la simulation :")
        for job in unfinished:
            remaining = format_time(job.remaining_time)
            print(f"  - {format_job(job)} (reste {remaining} {unit})")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulation d'un ordonnanceur EDF")
    parser.add_argument(
        "--tasks",
        type=Path,
        help="Fichier JSON décrivant les tâches (sinon un exemple est utilisé)",
    )
    parser.add_argument(
        "--horizon",
        type=float,
        help="Durée de simulation (par défaut : calcul automatique)",
    )
    parser.add_argument(
        "--time-unit",
        default="s",
        help="Unité de temps affichée (par défaut : secondes)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if args.tasks:
        tasks = load_tasks(args.tasks)
    else:
        tasks = [
            Task("Thread1", computation_time=2, period=7, deadline=7),
            Task("Thread2", computation_time=3, period=11, deadline=11),
            Task("Thread3", computation_time=5, period=13, deadline=13),
        ]

    horizon = args.horizon if args.horizon is not None else compute_default_horizon(tasks)

    print(f"Horizon de simulation : {format_time(horizon)} {args.time_unit}")
    describe_tasks(tasks, args.time_unit)

    result = simulate_edf(tasks, horizon)

    print_timeline(result, args.time_unit)


if __name__ == "__main__":
    main()