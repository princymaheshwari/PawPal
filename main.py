from pawpal_system import Owner, Pet, Task, RecurringTask, Preference, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", available_minutes=120)
owner.set_available_time(120)

mochi = Pet(name="Mochi", species="dog", age=3, breed="Shiba Inu")
bella = Pet(name="Bella", species="cat", age=5, breed="Tabby")

# --- Tasks for Mochi ---
mochi.add_task(Task(
    title="Morning Walk",
    task_type="walk",
    duration_minutes=30,
    priority="high",
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

# --- Tasks for Bella ---
bella.add_task(Task(
    title="Grooming Session",
    task_type="grooming",
    duration_minutes=20,
    priority="medium",
    pet_name="Bella",
))
bella.add_task(Task(
    title="Playtime / Enrichment",
    task_type="other",
    duration_minutes=15,
    priority="low",
    pet_name="Bella",
))
bella.add_recurring_task(RecurringTask(
    title="Insulin Injection",
    task_type="medication",
    duration_minutes=5,
    priority="high",
    frequency="daily",
    scheduled_time="09:00",
    pet_name="Bella",
    notes="0.5 units, left scruff",
))

# --- Owner preferences ---
owner.add_preference(Preference(
    category="time_of_day",
    task_type="walk",
    value="morning",
    description="Prefer walks in the morning",
))

# --- Add pets to owner ---
owner.add_pet(mochi)
owner.add_pet(bella)

# --- Generate schedule ---
from datetime import datetime
today = datetime.now().strftime("%A")  # e.g. "Monday"
scheduler = Scheduler(owner)
plan = scheduler.generate_plan(today)

# --- Print schedule ---
print(plan.summary())
