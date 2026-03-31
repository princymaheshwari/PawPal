import uuid
from datetime import datetime, date, timedelta

# Algorithm B: keyword map for urgency scoring
# If a pet's special_needs contain any of these keywords for a matching task type,
# that task gets a +2 boost so health-critical tasks float above routine ones.
URGENCY_KEYWORDS = {
    "medication":  ["medication", "insulin", "injection", "pill", "prescription", "dose"],
    "feeding":     ["diet", "renal", "diabetic", "weight", "nutrition", "allerg"],
    "walk":        ["mobility", "arthrit", "rehab", "exercise", "joint"],
    "grooming":    ["skin", "dermat", "coat", "mite", "flea", "tick"],
    "appointment": ["cancer", "chemo", "surgery", "post-op", "check-up"],
}

# Algorithm C: task type dependency order
# Lower rank = must come earlier in the day (medication before feeding, etc.)
TASK_ORDER = {
    "medication": 0,
    "feeding":    1,
    "walk":       2,
    "grooming":   3,
    "appointment":4,
    "other":      5,
}


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

    def complete_task(self, task_id, today_date=None):
        """Mark a task complete; if it recurs, auto-add the next occurrence to this pet."""
        if today_date is None:
            today_date = date.today()
        for task in self.tasks:
            if task.task_id == task_id:
                task.mark_complete(today_date)
                if task.next_due_date is not None:
                    next_task = Task(
                        title=task.title,
                        task_type=task.task_type,
                        duration_minutes=task.duration_minutes,
                        priority=task.priority,
                        scheduled_time=task.scheduled_time,
                        pet_name=task.pet_name,
                        notes=task.notes,
                        recurrence=task.recurrence,
                    )
                    next_task.next_due_date = task.next_due_date
                    self.tasks.append(next_task)
                return task
        return None

    # Algorithm E: today_date passed through so RecurringTask can do date-math
    def get_tasks_today(self, day_of_week, today_date=None):
        """Return all tasks active today for this pet: one-off tasks plus generated recurring tasks.

        today_date (date or None) is forwarded to RecurringTask.is_active_today() so that
        biweekly and every_n_days frequencies can do date arithmetic. Defaults to date.today()
        inside RecurringTask if not provided. Each active RecurringTask produces a fresh Task
        via to_task() rather than reusing the template, keeping the template uncompleted.
        """
        today_tasks = list(self.tasks)
        for rt in self.recurring_tasks:
            if rt.is_active_today(day_of_week, today_date):
                today_tasks.append(rt.to_task())
        return today_tasks

    def __str__(self):
        """Return a short human-readable description of this pet."""
        return f"{self.name} ({self.species}, {self.age} years)"


class Task:
    def __init__(self, title, task_type, duration_minutes, priority,
                 scheduled_time=None, pet_name=None, notes="", recurrence=None):
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
        self.recurrence = recurrence    # "daily", "weekly", or None
        self.next_due_date = None       # set by mark_complete() when recurrence is active

    def mark_complete(self, today_date=None):
        """Mark this task as completed and calculate next_due_date if it recurs."""
        self.is_completed = True
        if self.recurrence is None:
            return
        if today_date is None:
            today_date = date.today()
        elif isinstance(today_date, str):
            today_date = date.fromisoformat(today_date)
        if self.recurrence == "daily":
            self.next_due_date = today_date + timedelta(days=1)
        elif self.recurrence == "weekly":
            self.next_due_date = today_date + timedelta(weeks=1)

    def mark_incomplete(self):
        """Mark this task as not yet completed."""
        self.is_completed = False

    def priority_score(self):
        """Return a numeric score for this task's priority (high=3, medium=2, low=1)."""
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(self.priority, 0)

    # Algorithm B: urgency boost based on pet's special needs
    def urgency_score(self, pet):
        """Return +2 if this pet's special needs contain a keyword matching this task's type, else 0.

        Looks up URGENCY_KEYWORDS[task_type] and checks whether any word in pet.special_needs
        contains one of those substrings (case-insensitive). A match signals that this task is
        health-critical for this pet, boosting its sort score above routine tasks of equal priority.
        Returns 0 if pet is None or no keyword matches are found.
        """
        if pet is None:
            return 0
        keywords = URGENCY_KEYWORDS.get(self.task_type, [])
        for need in pet.special_needs:
            for kw in keywords:
                if kw in need.lower():
                    return 2
        return 0

    def is_fixed_time(self):
        """Return True if this task has a specific scheduled time set."""
        return self.scheduled_time is not None

    def __str__(self):
        """Return a formatted summary string including priority, title, duration, and pet."""
        pet_part = f" | {self.pet_name}" if self.pet_name else ""
        return f"[{self.priority.upper()}] {self.title} ({self.duration_minutes} min){pet_part}"


class RecurringTask:
    # Algorithm E: added interval_days and start_date for biweekly / every_n_days support
    def __init__(self, title, task_type, duration_minutes, priority,
                 frequency="daily", scheduled_time=None, days_of_week=None,
                 pet_name=None, notes="", interval_days=None, start_date=None):
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
        self.interval_days = interval_days  # used by every_n_days and biweekly
        self.start_date = start_date or date.today().isoformat()  # "YYYY-MM-DD" reference

    def is_active_today(self, day_of_week, today_date=None):
        """Return True if this recurring task should appear on the given day.

        Supports four frequency modes:
          - "daily": always active.
          - "weekly": active on days listed in days_of_week (all days if None).
          - "biweekly": active every 14 days from start_date using timedelta arithmetic.
          - "every_n_days": active every interval_days days from start_date.
        For date-based modes, today_date defaults to date.today() if not provided.
        Returns False if today_date is before start_date (task hasn't started yet).
        """
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            if self.days_of_week is None:
                return True
            return day_of_week in self.days_of_week
        # Algorithm E: date-arithmetic branches
        if today_date is None:
            today_date = date.today()
        elif isinstance(today_date, str):
            today_date = date.fromisoformat(today_date)
        start = date.fromisoformat(self.start_date)
        delta = (today_date - start).days
        if delta < 0:
            return False
        if self.frequency == "biweekly":
            return delta % 14 == 0
        if self.frequency == "every_n_days":
            if self.interval_days and self.interval_days > 0:
                return delta % self.interval_days == 0
        return False

    def to_task(self):
        """Create and return a new Task instance from this template's attributes."""
        recurrence = self.frequency if self.frequency in ("daily", "weekly") else None
        return Task(
            title=self.title,
            task_type=self.task_type,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            scheduled_time=self.scheduled_time,
            pet_name=self.pet_name,
            notes=self.notes,
            recurrence=recurrence,
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
    # Algorithm D: day_start and buffer_minutes added so Scheduler can read them
    def __init__(self, name, available_minutes=120, day_start="08:00", buffer_minutes=5):
        """Create an owner with a name, time budget, and scheduling preferences."""
        self.name = name
        self.available_minutes = available_minutes
        self.day_start = day_start          # when the owner's day begins (HH:MM)
        self.buffer_minutes = buffer_minutes  # gap between consecutive flexible tasks
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

    # Algorithm E: today_date threaded through to pets
    def all_tasks_today(self, day_of_week, today_date=None):
        """Collect and return every task active today across all of the owner's pets.

        Calls pet.get_tasks_today(day_of_week, today_date) for each pet and concatenates
        the results. today_date is passed through so RecurringTask date-math (biweekly,
        every_n_days) works correctly. Returns a flat list of Task objects.
        """
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks_today(day_of_week, today_date))
        return all_tasks


class DailyPlan:
    def __init__(self, available_minutes):
        """Create an empty plan with a time budget and a timestamp."""
        self.scheduled_tasks = []
        self.skipped_tasks = []
        self.total_duration_minutes = 0
        self.available_minutes = available_minutes
        self.reasoning = {}
        self.conflicts = []             # Algorithm A
        self.overload_warning = None    # Algorithm G
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
        # Algorithm G: overload warning at top
        if self.overload_warning:
            lines.append(f"[!] {self.overload_warning}")
            lines.append("")
        # Algorithm A: conflict warnings
        if self.conflicts:
            lines.append("*** CONFLICTS DETECTED ***")
            for msg in self.conflicts:
                lines.append(f"  [!] {msg}")
            lines.append("")
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


class TaskFilter:
    """Static utility methods for filtering a flat list of Task objects."""

    @staticmethod
    def by_pet(tasks, pet_name):
        """Return only tasks belonging to the named pet (case-insensitive)."""
        name_lower = pet_name.lower()
        return [t for t in tasks if t.pet_name and t.pet_name.lower() == name_lower]

    @staticmethod
    def by_status(tasks, completed):
        """Return completed tasks if completed=True, pending tasks if completed=False."""
        return [t for t in tasks if t.is_completed == completed]

    @staticmethod
    def by_type(tasks, task_type):
        """Return only tasks whose task_type matches (case-insensitive)."""
        type_lower = task_type.lower()
        return [t for t in tasks if t.task_type.lower() == type_lower]

    @staticmethod
    def by_priority(tasks, priority):
        """Return only tasks whose priority matches (case-insensitive)."""
        return [t for t in tasks if t.priority.lower() == priority.lower()]


class Scheduler:
    def __init__(self, owner):
        """Create a Scheduler tied to the given Owner."""
        self.owner = owner

    # Algorithm E: today_date parameter threads through to RecurringTask.is_active_today
    def generate_plan(self, day_of_week, today_date=None):
        """Build and return a DailyPlan for the given day by running the full scheduling pipeline.

        Pipeline order:
          1. Collect all tasks (one-off + recurring) via _collect_tasks.
          2. Compute overload warning if total requested time exceeds budget (Algorithm G).
          3. Separate fixed-time tasks from flexible tasks.
          4. Detect conflicts among fixed-time tasks (Algorithm A).
          5. Sort flexible tasks by urgency-boosted priority (Algorithm B).
          6. Enforce clinical dependency ordering — medication before feeding, etc. (Algorithm C).
          7. Apply owner time-of-day preferences to flexible tasks.
          8. Greedily fit flexible tasks into the remaining time budget.
          9. Assign start times with configurable day_start and buffer gaps (Algorithm D).
          10. Record each task with its reasoning string in the DailyPlan.
        """
        plan = DailyPlan(self.owner.available_minutes)
        tasks = self._collect_tasks(day_of_week, today_date)

        plan.overload_warning = self.compute_overload_warning(tasks)    # Algorithm G

        fixed, flexible = self._separate_fixed(tasks)
        plan.conflicts = self.detect_conflicts(fixed)                   # Algorithm A

        pets_by_name = {pet.name: pet for pet in self.owner.pets}
        flexible = self._sort_flexible(flexible, pets_by_name)          # Algorithm B
        flexible = self._enforce_dependencies(flexible)                 # Algorithm C
        flexible = self._apply_preferences(flexible)

        scheduled, skipped = self._fit_tasks(fixed, flexible, self.owner.available_minutes)
        scheduled = self._assign_times(                                 # Algorithm D
            scheduled,
            day_start=self.owner.day_start,
            buffer_minutes=self.owner.buffer_minutes,
        )
        for task in scheduled:
            plan.add_scheduled_task(task, self._build_reasoning(task, included=True))
        for task in skipped:
            plan.add_skipped_task(task, self._build_reasoning(task, included=False))
        return plan

    # Algorithm G: overload warning
    def compute_overload_warning(self, tasks):
        """Return a human-readable warning string if total task time exceeds the budget, else None.

        Sums duration_minutes across all tasks (fixed and flexible) and compares to
        owner.available_minutes. If over budget, the message includes: total requested,
        budget, overflow amount, percentage over, fixed-task footprint, and how many flexible
        minutes are competing for the remaining budget. Returns None if within budget.
        """
        total = sum(t.duration_minutes for t in tasks)
        budget = self.owner.available_minutes
        if total <= budget:
            return None
        overflow = total - budget
        pct = round((overflow / budget) * 100)
        fixed_min = sum(t.duration_minutes for t in tasks if t.is_fixed_time())
        flex_min  = sum(t.duration_minutes for t in tasks if not t.is_fixed_time())
        return (
            f"Overload: {total} min requested, {budget} min available "
            f"({overflow} min over budget, {pct}% over). "
            f"Fixed tasks use {fixed_min} min; "
            f"{flex_min} min of flexible tasks compete for the remaining {budget - fixed_min} min. "
            f"Lower-priority tasks will be skipped."
        )

    # Algorithm A: conflict detection
    def detect_conflicts(self, fixed_tasks):
        """Return a list of warning strings for any overlapping fixed-time tasks."""
        if len(fixed_tasks) < 2:
            return []
        intervals = []
        for task in fixed_tasks:
            try:
                h, m = map(int, task.scheduled_time.split(":"))
                start = h * 60 + m
                intervals.append((start, start + task.duration_minutes, task))
            except (ValueError, AttributeError):
                continue
        warnings = []
        for i in range(len(intervals)):
            for j in range(i + 1, len(intervals)):
                a_start, a_end, a_task = intervals[i]
                b_start, b_end, b_task = intervals[j]
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"'{a_task.title}' ({a_task.pet_name}, {a_task.scheduled_time}, "
                        f"{a_task.duration_minutes} min) overlaps "
                        f"'{b_task.title}' ({b_task.pet_name}, {b_task.scheduled_time}, "
                        f"{b_task.duration_minutes} min)"
                    )
        return warnings

    # Algorithm E: today_date passed down to owner
    def _collect_tasks(self, day_of_week, today_date=None):
        """Retrieve all tasks active today from the owner's pets.

        Delegates to owner.all_tasks_today(), passing today_date so RecurringTask
        biweekly and every_n_days frequency checks can compute the correct day delta.
        """
        return self.owner.all_tasks_today(day_of_week, today_date)

    def _separate_fixed(self, tasks):
        """Split the task list into fixed-time tasks and flexible tasks."""
        fixed    = [t for t in tasks if t.is_fixed_time()]
        flexible = [t for t in tasks if not t.is_fixed_time()]
        return fixed, flexible

    # Algorithm B: urgency-aware sort using pets_by_name lookup
    def _sort_flexible(self, tasks, pets_by_name=None):
        """Sort flexible tasks by combined priority + urgency score descending, duration ascending.

        pets_by_name is a dict mapping pet name -> Pet object, used to call
        task.urgency_score(pet) for each task. A task whose pet has a relevant special need
        receives a +2 urgency bonus, causing it to sort above a same-priority task with no
        health flag. Duration is the tiebreaker so shorter tasks fill time gaps first.
        """
        if pets_by_name is None:
            pets_by_name = {}
        def sort_key(t):
            pet     = pets_by_name.get(t.pet_name)
            urgency = t.urgency_score(pet)
            return (-(t.priority_score() + urgency), t.duration_minutes)
        return sorted(tasks, key=sort_key)

    # Algorithm C: enforce clinical task-type ordering
    def _enforce_dependencies(self, tasks):
        """Reorder flexible tasks by clinical dependency rank: medication -> feeding -> walk -> grooming -> appointment -> other.

        Uses TASK_ORDER ranks as the primary sort key so that, for example, all medication
        tasks always appear before any feeding task regardless of who set what priority.
        Within the same rank, higher priority and shorter duration are preferred.
        Equivalent to a topological sort on a linear dependency graph — no cycles possible.
        Fixed-time tasks are not passed here and are never reordered.
        """
        def dep_key(t):
            rank = TASK_ORDER.get(t.task_type, 5)
            return (rank, -t.priority_score(), t.duration_minutes)
        return sorted(tasks, key=dep_key)

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

    def sort_by_time(self, tasks):
        """Sort a list of tasks by scheduled_time (HH:MM); tasks with no time go last."""
        return sorted(tasks, key=lambda t: t.scheduled_time if t.scheduled_time else "99:99")

    # Algorithm D: configurable day_start and buffer_minutes; fixes single-pass bug
    def _assign_times(self, tasks, day_start="08:00", buffer_minutes=5):
        """Assign HH:MM start times to flexible tasks, avoiding fixed-task slots and inserting gaps.

        day_start (str "HH:MM"): cursor starts here instead of hardcoded 8 AM.
        buffer_minutes (int): gap added after each flexible task so tasks aren't crammed together.
        Fixed-task windows are recorded as occupied intervals. Each flexible task advances the
        cursor past any overlapping occupied window using a while-changed loop — this fixes the
        original single-pass bug that could miss overlap when two fixed slots were adjacent.
        Returns all tasks sorted chronologically by scheduled_time.
        """
        fixed    = sorted([t for t in tasks if t.is_fixed_time()],  key=lambda t: t.scheduled_time)
        flexible = [t for t in tasks if not t.is_fixed_time()]

        occupied = []
        for t in fixed:
            h, m  = map(int, t.scheduled_time.split(":"))
            start = h * 60 + m
            occupied.append((start, start + t.duration_minutes))

        dh, dm = map(int, day_start.split(":"))
        cursor = dh * 60 + dm

        for task in flexible:
            # while-changed loop: re-scan all occupied slots after each cursor move
            # (fixes the original single-pass bug where adjacent slots could still overlap)
            changed = True
            while changed:
                changed = False
                for occ_start, occ_end in sorted(occupied):
                    if cursor < occ_end and cursor + task.duration_minutes > occ_start:
                        cursor  = occ_end
                        changed = True
            h, m = divmod(cursor, 60)
            task.scheduled_time = f"{h:02d}:{m:02d}"
            # reserve slot + buffer so next task starts after the gap
            occupied.append((cursor, cursor + task.duration_minutes + buffer_minutes))
            occupied.sort()
            cursor += task.duration_minutes + buffer_minutes

        return sorted(tasks, key=lambda t: t.scheduled_time)
