import uuid
from datetime import datetime


class Pet:
    def __init__(self, name, species, age, breed="", special_needs=None):
        """Create a pet with basic info and empty task lists."""
        self.name = name
        self.species = species
        self.age = age
        self.breed = breed
        self.special_needs = special_needs if special_needs is not None else []
        self.tasks = []
        self.recurring_tasks = []

    def add_special_need(self, need):
        """Append a special care need (e.g. 'insulin injection') to this pet's list."""
        self.special_needs.append(need)

    def remove_special_need(self, need):
        """Remove a special need from the list if it exists."""
        if need in self.special_needs:
            self.special_needs.remove(need)

    def has_special_needs(self):
        """Return True if this pet has any special care needs recorded."""
        return len(self.special_needs) > 0

    def add_task(self, task):
        """Add a one-off Task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id):
        """Remove the task with the given task_id from this pet's task list."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def add_recurring_task(self, recurring_task):
        """Add a RecurringTask template to this pet's recurring task list."""
        self.recurring_tasks.append(recurring_task)

    def remove_recurring_task(self, title):
        """Remove a recurring task template by its title."""
        self.recurring_tasks = [rt for rt in self.recurring_tasks if rt.title != title]

    def get_tasks_today(self, day_of_week):
        """Return one-off tasks plus any recurring tasks active today."""
        today_tasks = list(self.tasks)
        for rt in self.recurring_tasks:
            if rt.is_active_today(day_of_week):
                today_tasks.append(rt.to_task())
        return today_tasks

    def __str__(self):
        """Return a short human-readable description of this pet."""
        return f"{self.name} ({self.species}, {self.age} years)"


class Task:
    def __init__(self, title, task_type, duration_minutes, priority,
                 scheduled_time=None, pet_name=None, notes=""):
        """Create a task with a unique ID and set completion status to False."""
        self.task_id = str(uuid.uuid4())
        self.title = title
        self.task_type = task_type
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.scheduled_time = scheduled_time
        self.is_completed = False
        self.pet_name = pet_name
        self.notes = notes

    def mark_complete(self):
        """Mark this task as completed."""
        self.is_completed = True

    def mark_incomplete(self):
        """Mark this task as not yet completed."""
        self.is_completed = False

    def priority_score(self):
        """Return a numeric score for this task's priority (high=3, medium=2, low=1)."""
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(self.priority, 0)

    def is_fixed_time(self):
        """Return True if this task has a specific scheduled time set."""
        return self.scheduled_time is not None

    def __str__(self):
        """Return a formatted summary string including priority, title, duration, and pet."""
        pet_part = f" | {self.pet_name}" if self.pet_name else ""
        return f"[{self.priority.upper()}] {self.title} ({self.duration_minutes} min){pet_part}"


class RecurringTask:
    def __init__(self, title, task_type, duration_minutes, priority,
                 frequency="daily", scheduled_time=None, days_of_week=None,
                 pet_name=None, notes=""):
        """Create a recurring task template that generates a fresh Task each active day."""
        self.title = title
        self.task_type = task_type
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.scheduled_time = scheduled_time
        self.frequency = frequency
        self.days_of_week = days_of_week
        self.pet_name = pet_name
        self.notes = notes

    def is_active_today(self, day_of_week):
        """Return True if this recurring task should appear on the given day of the week."""
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            if self.days_of_week is None:
                return True
            return day_of_week in self.days_of_week
        return False

    def to_task(self):
        """Create and return a new Task instance from this template's attributes."""
        return Task(
            title=self.title,
            task_type=self.task_type,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            scheduled_time=self.scheduled_time,
            pet_name=self.pet_name,
            notes=self.notes,
        )

    def __str__(self):
        """Return a short description showing the frequency and title of this template."""
        time_part = f" at {self.scheduled_time}" if self.scheduled_time else ""
        return f"{self.frequency.capitalize()}{time_part} - {self.title}"


class Preference:
    def __init__(self, category, task_type, value, description=""):
        """Create a scheduling preference for a specific task type."""
        self.category = category
        self.task_type = task_type
        self.value = value
        self.description = description if description else f"{task_type} preference: {value}"

    def matches_task_type(self, task_type):
        """Return True if this preference applies to the given task type."""
        return self.task_type == task_type

    def __str__(self):
        """Return the human-readable description of this preference."""
        return self.description


class Owner:
    def __init__(self, name, available_minutes=120):
        """Create an owner with a name, a time budget, and empty pet and preference lists."""
        self.name = name
        self.available_minutes = available_minutes
        self.pets = []
        self.preferences = []

    def add_pet(self, pet):
        """Add a Pet to this owner's list of pets."""
        self.pets.append(pet)

    def remove_pet(self, pet_name):
        """Remove the pet with the given name from the owner's list."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_pet(self, pet_name):
        """Return the Pet with the given name, or None if not found."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet
        return None

    def add_preference(self, preference):
        """Add a scheduling Preference to this owner's list."""
        self.preferences.append(preference)

    def remove_preference(self, task_type):
        """Remove all preferences that apply to the given task type."""
        self.preferences = [p for p in self.preferences if p.task_type != task_type]

    def set_available_time(self, minutes):
        """Update how many minutes the owner has available today."""
        self.available_minutes = minutes

    def get_preferences_for(self, task_type):
        """Return all preferences that match the given task type."""
        return [p for p in self.preferences if p.matches_task_type(task_type)]

    def all_tasks_today(self, day_of_week):
        """Collect and return all tasks for today across every pet."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks_today(day_of_week))
        return all_tasks


class DailyPlan:
    def __init__(self, available_minutes):
        """Create an empty plan with a time budget and a timestamp."""
        self.scheduled_tasks = []
        self.skipped_tasks = []
        self.total_duration_minutes = 0
        self.available_minutes = available_minutes
        self.reasoning = {}
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def add_scheduled_task(self, task, reason):
        """Add a task to the scheduled list, store its reason, and update total duration."""
        self.scheduled_tasks.append(task)
        self.reasoning[task.task_id] = reason
        self.total_duration_minutes += task.duration_minutes

    def add_skipped_task(self, task, reason):
        """Add a task to the skipped list and record why it was excluded."""
        self.skipped_tasks.append(task)
        self.reasoning[task.task_id] = reason

    def get_reason(self, task_id):
        """Return the explanation string for the given task ID."""
        return self.reasoning.get(task_id, "No reason recorded.")

    def time_remaining(self):
        """Return the number of minutes left in today's budget after scheduled tasks."""
        return self.available_minutes - self.total_duration_minutes

    def completion_count(self):
        """Return the number of scheduled tasks that have been marked complete."""
        return sum(1 for t in self.scheduled_tasks if t.is_completed)

    def all_done(self):
        """Return True if every scheduled task has been marked complete."""
        return len(self.scheduled_tasks) > 0 and all(
            t.is_completed for t in self.scheduled_tasks
        )

    def summary(self):
        """Return a formatted multi-line string of the full plan for terminal display."""
        lines = [
            f"Daily Plan - Generated {self.generated_at}",
            f"Budget: {self.available_minutes} min | Used: {self.total_duration_minutes} min | Remaining: {self.time_remaining()} min",
            "",
        ]
        if self.scheduled_tasks:
            lines.append("Scheduled:")
            for task in self.scheduled_tasks:
                status = "[x]" if task.is_completed else "[ ]"
                time_label = f"[{task.scheduled_time}]" if task.scheduled_time else "[--:--]"
                lines.append(f"  {status} {time_label} {task}")
                lines.append(f"           -> {self.get_reason(task.task_id)}")
        if self.skipped_tasks:
            lines.append("")
            lines.append("Skipped:")
            for task in self.skipped_tasks:
                lines.append(f"  [!] {task}")
                lines.append(f"           -> {self.get_reason(task.task_id)}")
        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner):
        """Create a Scheduler tied to the given Owner."""
        self.owner = owner

    def generate_plan(self, day_of_week):
        """Main entry point: builds and returns a DailyPlan for the given day."""
        plan = DailyPlan(self.owner.available_minutes)
        tasks = self._collect_tasks(day_of_week)
        fixed, flexible = self._separate_fixed(tasks)
        flexible = self._sort_flexible(flexible)
        flexible = self._apply_preferences(flexible)
        scheduled, skipped = self._fit_tasks(fixed, flexible, self.owner.available_minutes)
        scheduled = self._assign_times(scheduled)
        for task in scheduled:
            plan.add_scheduled_task(task, self._build_reasoning(task, included=True))
        for task in skipped:
            plan.add_skipped_task(task, self._build_reasoning(task, included=False))
        return plan

    def _collect_tasks(self, day_of_week):
        """Retrieve all tasks for today from the owner's pets."""
        return self.owner.all_tasks_today(day_of_week)

    def _separate_fixed(self, tasks):
        """Split the task list into fixed-time tasks and flexible tasks."""
        fixed = [t for t in tasks if t.is_fixed_time()]
        flexible = [t for t in tasks if not t.is_fixed_time()]
        return fixed, flexible

    def _sort_flexible(self, tasks):
        """Sort flexible tasks by priority descending, then duration ascending as tiebreaker."""
        return sorted(tasks, key=lambda t: (-t.priority_score(), t.duration_minutes))

    def _apply_preferences(self, tasks):
        """Pin a suggested time onto flexible tasks that match a time_of_day preference."""
        time_map = {"morning": "08:00", "afternoon": "12:00", "evening": "18:00"}
        for task in tasks:
            prefs = self.owner.get_preferences_for(task.task_type)
            for pref in prefs:
                if pref.category == "time_of_day" and pref.value in time_map:
                    task.scheduled_time = time_map[pref.value]
        return tasks

    def _fit_tasks(self, fixed, flexible, budget):
        """Always include fixed tasks; greedily fill remaining time with flexible tasks."""
        scheduled = list(fixed)
        remaining = budget - sum(t.duration_minutes for t in fixed)
        skipped = []
        for task in flexible:
            if task.duration_minutes <= remaining:
                scheduled.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(task)
        return scheduled, skipped

    def _build_reasoning(self, task, included):
        """Return a short string explaining why a task was included or skipped."""
        if included:
            reason = f"Included: {task.priority} priority"
            if task.is_fixed_time():
                reason += f", fixed at {task.scheduled_time}"
            prefs = self.owner.get_preferences_for(task.task_type)
            if prefs:
                reason += f", preference: {prefs[0].description}"
            return reason
        return f"Skipped: not enough time remaining (needs {task.duration_minutes} min)"

    def _assign_times(self, tasks):
        """Assign sequential start times to tasks that don't already have one."""
        fixed = sorted(
            [t for t in tasks if t.is_fixed_time()],
            key=lambda t: t.scheduled_time,
        )
        flexible = [t for t in tasks if not t.is_fixed_time()]

        # Track occupied slots as (start_min, end_min) from midnight
        occupied = []
        for t in fixed:
            h, m = map(int, t.scheduled_time.split(":"))
            start = h * 60 + m
            occupied.append((start, start + t.duration_minutes))

        # Place flexible tasks starting at 8:00 AM, skipping occupied slots
        cursor = 8 * 60
        for task in flexible:
            for occ_start, occ_end in sorted(occupied):
                if cursor < occ_end and cursor + task.duration_minutes > occ_start:
                    cursor = occ_end
            h, m = divmod(cursor, 60)
            task.scheduled_time = f"{h:02d}:{m:02d}"
            occupied.append((cursor, cursor + task.duration_minutes))
            occupied.sort()
            cursor += task.duration_minutes

        return sorted(tasks, key=lambda t: t.scheduled_time)
