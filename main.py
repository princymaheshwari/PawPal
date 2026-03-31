import sys
sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, date
from tabulate import tabulate
from pawpal_system import (Owner, Pet, Task, RecurringTask, Preference,
                           Scheduler, TaskFilter)

# Plain-text labels for the CLI — emoji are double-width in terminals and
# break tabulate's column alignment, so we use bracketed text here instead.
CLI_PRIORITY = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
CLI_TYPE     = {
    "medication":  "Medication",
    "feeding":     "Feeding",
    "walk":        "Walk",
    "grooming":    "Grooming",
    "appointment": "Appointment",
    "other":       "Other",
}
CLI_STATUS   = {True: "Done", False: "Pending"}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def task_rows(tasks, scheduler=None):
    """Convert a list of Task objects to tabulate-ready rows."""
    ordered = scheduler.sort_by_time(tasks) if scheduler else tasks
    rows = []
    for t in ordered:
        rows.append([
            t.scheduled_time or "(flexible)",
            t.title,
            t.pet_name or "-",
            CLI_TYPE.get(t.task_type, t.task_type),
            CLI_PRIORITY.get(t.priority, t.priority),
            f"{t.duration_minutes} min",
            CLI_STATUS.get(t.is_completed, "-"),
        ])
    return rows

TASK_HEADERS = ["Time", "Task", "Pet", "Type", "Priority", "Duration", "Status"]

def print_table(title, rows, headers=TASK_HEADERS):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print('━' * 70)
    if rows:
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    else:
        print("  (no tasks)")

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
owner = Owner(name="Jordan", available_minutes=120)

mochi = Pet(name="Mochi", species="dog", age=3, breed="Shiba Inu")
bella = Pet(name="Bella", species="cat", age=5, breed="Tabby")

# Tasks added INTENTIONALLY OUT OF CHRONOLOGICAL ORDER
mochi.add_task(Task(
    title="Evening Walk",
    task_type="walk",
    duration_minutes=30,
    priority="medium",
    scheduled_time="18:00",
    pet_name="Mochi",
))
mochi.add_task(Task(
    title="Flea Medication",
    task_type="medication",
    duration_minutes=5,
    priority="high",
    scheduled_time="08:00",
    pet_name="Mochi",
    notes="Apply to back of neck",
))
mochi.add_recurring_task(RecurringTask(
    title="Breakfast",
    task_type="feeding",
    duration_minutes=10,
    priority="high",
    frequency="daily",
    scheduled_time="07:30",
    pet_name="Mochi",
))

bella.add_task(Task(
    title="Insulin Injection",
    task_type="medication",
    duration_minutes=5,
    priority="high",
    scheduled_time="09:00",
    pet_name="Bella",
    notes="0.5 units, left scruff",
))
bella.add_task(Task(
    title="Grooming Session",
    task_type="grooming",
    duration_minutes=20,
    priority="medium",
    scheduled_time="14:30",
    pet_name="Bella",
))
bella.add_task(Task(
    title="Playtime",
    task_type="other",
    duration_minutes=15,
    priority="low",
    pet_name="Bella",
))

mochi.tasks[1].mark_complete()   # Flea Medication — mark done for demo

owner.add_preference(Preference(
    category="time_of_day",
    task_type="walk",
    value="morning",
    description="Prefer walks in the morning",
))

owner.add_pet(mochi)
owner.add_pet(bella)

today     = datetime.now().strftime("%A")
today_date = date.today()
scheduler = Scheduler(owner)
all_tasks = owner.all_tasks_today(today)

# -----------------------------------------------------------------------
# DEMO 1 — All tasks sorted by time
# -----------------------------------------------------------------------
print_table("DEMO 1 — All tasks sorted by scheduled time",
            task_rows(all_tasks, scheduler))

# -----------------------------------------------------------------------
# DEMO 2 — Filter by pet
# -----------------------------------------------------------------------
print_table("DEMO 2 — Mochi's tasks only",
            task_rows(TaskFilter.by_pet(all_tasks, "Mochi"), scheduler))

print_table("DEMO 2 — Bella's tasks only",
            task_rows(TaskFilter.by_pet(all_tasks, "Bella"), scheduler))

# -----------------------------------------------------------------------
# DEMO 3 — Filter by completion status
# -----------------------------------------------------------------------
print_table("DEMO 3 — Completed tasks",
            task_rows(TaskFilter.by_status(all_tasks, completed=True), scheduler))

print_table("DEMO 3 — Pending tasks",
            task_rows(TaskFilter.by_status(all_tasks, completed=False), scheduler))

# -----------------------------------------------------------------------
# DEMO 4 — Filter by task type
# -----------------------------------------------------------------------
print_table("DEMO 4 — Medication tasks only",
            task_rows(TaskFilter.by_type(all_tasks, "medication"), scheduler))

print_table("DEMO 4 — Walk tasks only",
            task_rows(TaskFilter.by_type(all_tasks, "walk"), scheduler))

# -----------------------------------------------------------------------
# DEMO 5 — Filter by priority
# -----------------------------------------------------------------------
print_table("DEMO 5 — High priority tasks only",
            task_rows(TaskFilter.by_priority(all_tasks, "high"), scheduler))

print_table("DEMO 5 — Low priority tasks only",
            task_rows(TaskFilter.by_priority(all_tasks, "low"), scheduler))

# -----------------------------------------------------------------------
# DEMO 6 — Full generated schedule
# -----------------------------------------------------------------------
plan = scheduler.generate_plan(today, today_date)

print(f"\n{'━' * 70}")
print("  DEMO 6 — Generated daily schedule")
print('━' * 70)
print(f"  Budget: {plan.available_minutes} min  |  "
      f"Scheduled: {plan.total_duration_minutes} min  |  "
      f"Remaining: {plan.time_remaining()} min")

if plan.overload_warning:
    print(f"\n  [!] OVERLOAD: {plan.overload_warning}")

if plan.conflicts:
    print(f"\n  [!] {len(plan.conflicts)} conflict(s) detected:")
    for msg in plan.conflicts:
        print(f"      - {msg}")

if plan.scheduled_tasks:
    sched_rows = []
    for t in plan.scheduled_tasks:
        reason = plan.get_reason(t.task_id)
        urgent = "[!] " if "special need" in reason.lower() else ""
        sched_rows.append([
            t.scheduled_time or "--:--",
            urgent + t.title,
            t.pet_name or "-",
            CLI_TYPE.get(t.task_type, t.task_type),
            CLI_PRIORITY.get(t.priority, t.priority),
            f"{t.duration_minutes} min",
            reason,
        ])
    print()
    print(tabulate(sched_rows,
                   headers=["Time", "Task", "Pet", "Type", "Priority", "Duration", "Reason"],
                   tablefmt="rounded_outline"))

if plan.skipped_tasks:
    skipped_rows = []
    for t in plan.skipped_tasks:
        skipped_rows.append([
            t.title,
            t.pet_name or "-",
            CLI_PRIORITY.get(t.priority, t.priority),
            f"{t.duration_minutes} min",
            plan.get_reason(t.task_id),
        ])
    print()
    print("  Skipped tasks:")
    print(tabulate(skipped_rows,
                   headers=["Task", "Pet", "Priority", "Duration", "Reason"],
                   tablefmt="rounded_outline"))

# -----------------------------------------------------------------------
# DEMO 7 — Recurring task auto-scheduling
# -----------------------------------------------------------------------
print(f"\n{'━' * 70}")
print("  DEMO 7 — Recurring task auto-scheduling (timedelta)")
print('━' * 70)

daily_feed = Task(
    title="Lunch Feeding",
    task_type="feeding",
    duration_minutes=10,
    priority="high",
    scheduled_time="12:00",
    pet_name="Bella",
    recurrence="daily",
)
bella.add_task(daily_feed)

print(f"  Before: Bella has {len(bella.tasks)} task(s)")
bella.complete_task(daily_feed.task_id, today_date)
print(f"  After:  Bella has {len(bella.tasks)} task(s)  (next occurrence auto-added)")

spawn_rows = []
for t in bella.tasks:
    spawn_rows.append([
        t.title,
        CLI_STATUS.get(t.is_completed, "-"),
        str(t.recurrence or "-"),
        str(t.next_due_date or "-"),
    ])
print()
print(tabulate(spawn_rows,
               headers=["Task", "Status", "Recurrence", "Next Due"],
               tablefmt="rounded_outline"))

# -----------------------------------------------------------------------
# DEMO 8 — Conflict detection
# -----------------------------------------------------------------------
print(f"\n{'━' * 70}")
print("  DEMO 8 — Conflict detection (overlapping fixed-time tasks)")
print('━' * 70)

conflict_owner = Owner(name="Jordan", available_minutes=120)
conflict_pet   = Pet(name="Mochi", species="dog", age=3)

conflict_pet.add_task(Task(
    title="Morning Walk",
    task_type="walk",
    duration_minutes=30,
    priority="high",
    scheduled_time="09:00",
    pet_name="Mochi",
))
conflict_pet.add_task(Task(
    title="Grooming Session",
    task_type="grooming",
    duration_minutes=20,
    priority="medium",
    scheduled_time="09:15",     # overlaps 09:00–09:30
    pet_name="Mochi",
))
conflict_pet.add_task(Task(
    title="Feeding",
    task_type="feeding",
    duration_minutes=10,
    priority="high",
    scheduled_time="10:00",     # clean, no overlap
    pet_name="Mochi",
))

conflict_owner.add_pet(conflict_pet)
conflict_plan = Scheduler(conflict_owner).generate_plan(today)

if conflict_plan.conflicts:
    print(f"\n  [!] {len(conflict_plan.conflicts)} conflict(s) found:")
    for msg in conflict_plan.conflicts:
        print(f"      - {msg}")
else:
    print("  No conflicts detected.")
print()
