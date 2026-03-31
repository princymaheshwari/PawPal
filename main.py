from datetime import datetime
from pawpal_system import Owner, Pet, Task, RecurringTask, Preference, Scheduler, TaskFilter

# --- Setup ---
owner = Owner(name="Jordan", available_minutes=120)

mochi = Pet(name="Mochi", species="dog", age=3, breed="Shiba Inu")
bella = Pet(name="Bella", species="cat", age=5, breed="Tabby")

# --- Tasks added INTENTIONALLY OUT OF CHRONOLOGICAL ORDER ---
# Mochi's tasks
mochi.add_task(Task(
    title="Evening Walk",
    task_type="walk",
    duration_minutes=30,
    priority="medium",
    scheduled_time="18:00",      # <-- late in the day
    pet_name="Mochi",
))
mochi.add_task(Task(
    title="Flea Medication",
    task_type="medication",
    duration_minutes=5,
    priority="high",
    scheduled_time="08:00",      # <-- early
    pet_name="Mochi",
    notes="Apply to back of neck",
))
mochi.add_recurring_task(RecurringTask(
    title="Breakfast",
    task_type="feeding",
    duration_minutes=10,
    priority="high",
    frequency="daily",
    scheduled_time="07:30",      # <-- earliest of all
    pet_name="Mochi",
))

# Bella's tasks
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
    scheduled_time="14:30",      # <-- afternoon
    pet_name="Bella",
))
bella.add_task(Task(
    title="Playtime",
    task_type="other",
    duration_minutes=15,
    priority="low",
    pet_name="Bella",            # no fixed time -- flexible
))

# Mark one task complete to demonstrate status filtering
mochi.tasks[1].mark_complete()  # Flea Medication is done

# --- Preferences ---
owner.add_preference(Preference(
    category="time_of_day",
    task_type="walk",
    value="morning",
    description="Prefer walks in the morning",
))

owner.add_pet(mochi)
owner.add_pet(bella)

# --- Collect all tasks for today ---
today = datetime.now().strftime("%A")
scheduler = Scheduler(owner)
all_tasks = owner.all_tasks_today(today)

# -----------------------------------------------------------------------
# DEMO 1: Sort by time using Scheduler.sort_by_time()
# "HH:MM" strings compare correctly as plain strings because digits are
# fixed-width zero-padded. The lambda key returns "99:99" for None so
# timeless tasks always land at the end.
# -----------------------------------------------------------------------
print("=" * 55)
print("DEMO 1: All tasks sorted by scheduled time")
print("=" * 55)
sorted_tasks = scheduler.sort_by_time(all_tasks)
for t in sorted_tasks:
    time_label = t.scheduled_time if t.scheduled_time else "(flexible)"
    print(f"  {time_label}  {t}")

# -----------------------------------------------------------------------
# DEMO 2: Filter by pet name
# -----------------------------------------------------------------------
print()
print("=" * 55)
print("DEMO 2: Filter -- Mochi's tasks only")
print("=" * 55)
mochi_tasks = TaskFilter.by_pet(all_tasks, "Mochi")
for t in scheduler.sort_by_time(mochi_tasks):
    print(f"  {t}")

print()
print("=" * 55)
print("DEMO 2: Filter -- Bella's tasks only")
print("=" * 55)
bella_tasks = TaskFilter.by_pet(all_tasks, "Bella")
for t in scheduler.sort_by_time(bella_tasks):
    print(f"  {t}")

# -----------------------------------------------------------------------
# DEMO 3: Filter by completion status
# -----------------------------------------------------------------------
print()
print("=" * 55)
print("DEMO 3: Filter -- Completed tasks")
print("=" * 55)
done = TaskFilter.by_status(all_tasks, completed=True)
print(f"  {len(done)} completed task(s):")
for t in done:
    print(f"  [x] {t}")

print()
print("=" * 55)
print("DEMO 3: Filter -- Pending tasks")
print("=" * 55)
pending = TaskFilter.by_status(all_tasks, completed=False)
print(f"  {len(pending)} pending task(s):")
for t in scheduler.sort_by_time(pending):
    print(f"  [ ] {t}")

# -----------------------------------------------------------------------
# DEMO 4: Filter by task type
# -----------------------------------------------------------------------
print()
print("=" * 55)
print("DEMO 4: Filter -- Medication tasks only")
print("=" * 55)
meds = TaskFilter.by_type(all_tasks, "medication")
for t in scheduler.sort_by_time(meds):
    print(f"  {t}")

print()
print("=" * 55)
print("DEMO 4: Filter -- Walk tasks only")
print("=" * 55)
walks = TaskFilter.by_type(all_tasks, "walk")
for t in scheduler.sort_by_time(walks):
    print(f"  {t}")

# -----------------------------------------------------------------------
# DEMO 5: Filter by priority
# -----------------------------------------------------------------------
print()
print("=" * 55)
print("DEMO 5: Filter -- High priority tasks only")
print("=" * 55)
high_priority = TaskFilter.by_priority(all_tasks, "high")
for t in scheduler.sort_by_time(high_priority):
    print(f"  {t}")

print()
print("=" * 55)
print("DEMO 5: Filter -- Low priority tasks only")
print("=" * 55)
low_priority = TaskFilter.by_priority(all_tasks, "low")
for t in scheduler.sort_by_time(low_priority):
    print(f"  {t}")

# -----------------------------------------------------------------------
# DEMO 6: Full generated schedule (as before)
# -----------------------------------------------------------------------
print()
print("=" * 55)
print("DEMO 6: Generated daily schedule")
print("=" * 55)
plan = scheduler.generate_plan(today)
print(plan.summary())
