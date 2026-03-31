# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ goes beyond a simple task list. The scheduler contains several algorithmic features that make it behave like a real pet management tool.

### Core features

**Sorting by time**
All tasks in the generated plan are sorted chronologically by their `HH:MM` scheduled time. `Scheduler.sort_by_time()` uses a lambda key on the time string — because times are zero-padded fixed-width, plain string comparison produces correct chronological order without parsing. Tasks with no fixed time are pushed to the end using a `"99:99"` sentinel value.

**Filtering**
The `TaskFilter` class provides four static methods to slice any task list without touching the UI layer:
- `by_pet(tasks, pet_name)` — returns only tasks for a named pet
- `by_type(tasks, task_type)` — returns only tasks of a given type (e.g. `"medication"`)
- `by_status(tasks, completed)` — separates done tasks from pending ones
- `by_priority(tasks, priority)` — returns tasks at a specific priority level

**Recurring tasks**
`RecurringTask` templates generate a fresh `Task` instance each day they are active via `to_task()`, so the template itself is never marked complete. Supported frequencies:
- `"daily"` — fires every day
- `"weekly"` — fires on specified days of the week
- `"biweekly"` — fires every 14 days from a `start_date` using day-delta arithmetic
- `"every_n_days"` — fires every `interval_days` days from a `start_date`

When a recurring task is completed via `Pet.complete_task()`, a new instance is automatically added to the pet's task list with `next_due_date` set using Python's `timedelta`.

**Conflict detection**
`Scheduler.detect_conflicts()` scans all fixed-time tasks for wall-clock overlaps before the schedule is built. Two tasks conflict when their time windows overlap: `a_start < b_end AND b_start < a_end`. Conflicts are reported as human-readable warning strings stored on `DailyPlan.conflicts` and shown at the top of the schedule — the program never crashes, it warns instead.

---

### Additional algorithms

**Urgency scoring**
`Task.urgency_score(pet)` gives a task a `+2` boost to its sort score if the pet's `special_needs` list contains a keyword matching the task type (e.g. a pet with `"insulin injection"` in special needs causes its medication tasks to float above routine high-priority tasks). Keywords are defined in the `URGENCY_KEYWORDS` constant and cover medication, feeding, walking, grooming, and appointments.

**Task dependency ordering**
`Scheduler._enforce_dependencies()` reorders flexible tasks so that clinical sequencing is always respected: medication must come before feeding, feeding before walks, walks before grooming, grooming before appointments. This is implemented as a stable sort using the `TASK_ORDER` rank as the primary key — equivalent to a topological sort on a linear dependency graph.

**Smarter time-slot assignment**
`Scheduler._assign_times()` replaces the original hardcoded 8 AM start with a configurable `day_start` read from the `Owner` object, and inserts a `buffer_minutes` gap (default 5 minutes) between consecutive flexible tasks so the schedule never feels artificially packed. A `while changed` loop correctly handles adjacent fixed-task blocks, fixing a subtle single-pass bug in the original implementation.

**Overload warning**
`Scheduler.compute_overload_warning()` sums all requested task durations before fitting and compares the total to the owner's time budget. If over budget, it returns a message stating how many minutes over, what percentage, how much fixed tasks consume, and how many flexible minutes are competing for the remainder. The result is stored on `DailyPlan.overload_warning` and shown at the top of the schedule output.

---

---

## Testing PawPal+

### Running the tests

```bash
python -m pytest tests/test_pawpal.py -v
```

All 67 tests complete in under a second. The `-v` flag prints each test name so you can see exactly what passed.

### What the tests cover

The suite is organised into 8 sections, each targeting a distinct part of the system:

| Section | Tests | What is verified |
|---|---|---|
| **Schedule Generation** | 9 | Empty plans, budget fitting, fixed tasks always scheduled, overload warning, urgency boost ordering, clinical dependency order, reasoning recorded for every task |
| **Recurring Task Activation** | 14 | All 4 frequency modes (`daily`, `weekly`, `biweekly`, `every_n_days`), correct day-on / day-off behaviour, `days_of_week=None`, biweekly day 0/7/14 arithmetic, future `start_date` guard, `Pet.get_tasks_today` integration |
| **Conflict Detection** | 8 | True overlaps flagged, back-to-back tasks are NOT flagged, zero/single fixed task edge cases, partial overlaps, 3-way conflict pairs, conflicts surfaced on `DailyPlan` |
| **Task Completion & Recurrence** | 6 | Daily task creates next-day task, weekly task creates next-week task, one-off task spawns nothing, invalid ID returns `None`, next task inherits all properties |
| **Sorting & Time-Slot Assignment** | 8 | Chronological sort correctness, single flexible task placed at `day_start`, flexible task moved past fixed slot, two adjacent fixed slots handled by the while-changed loop, `buffer_minutes=0` back-to-back, exact buffer gap, custom `day_start` |
| **Urgency Scoring** | 6 | Keyword match returns `+2`, no match returns `0`, `None` pet, case-insensitivity, partial substring match (`"arthrit"` → `"arthritis"`), cross-type isolation |
| **Task Filters** | 6 | Filter by pet, type, completed status, pending status, high priority, low priority |
| **DailyPlan Utilities** | 7 | Time remaining, `all_done` states (incomplete / complete / empty), `get_reason` for known and unknown IDs, `completion_count` |

### Confidence Level

**4 / 5 stars**

The core scheduling pipeline — priority sorting, urgency boosting, dependency ordering, conflict detection, time-slot assignment, and recurring task date arithmetic — is fully tested with deterministic inputs (fixed reference date `2026-03-30`) so results never vary between runs. All 67 tests pass. One star is held back because the Streamlit UI layer (`app.py`) and session-state persistence are not covered by automated tests; those flows currently require manual verification in the browser.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
