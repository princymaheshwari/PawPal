from datetime import date, timedelta
import pytest
from pawpal_system import (
    Pet, Task, RecurringTask, Owner, Preference, Scheduler, TaskFilter, DailyPlan,
)

# Fixed reference date for deterministic tests (Monday, 2026-03-30)
TODAY = date(2026, 3, 30)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_task(title="Task", task_type="other", duration=30, priority="medium",
              scheduled_time=None, pet_name="Rex", recurrence=None):
    return Task(
        title=title,
        task_type=task_type,
        duration_minutes=duration,
        priority=priority,
        scheduled_time=scheduled_time,
        pet_name=pet_name,
        recurrence=recurrence,
    )


def make_owner(available_minutes=120, day_start="08:00", buffer_minutes=5):
    return Owner("Alex", available_minutes=available_minutes,
                 day_start=day_start, buffer_minutes=buffer_minutes)


# ══════════════════════════════════════════════════════════════════════════════
# ORIGINAL TESTS (preserved)
# ══════════════════════════════════════════════════════════════════════════════

def test_mark_complete_changes_status():
    """mark_complete() should set is_completed to True."""
    task = Task(
        title="Morning Walk",
        task_type="walk",
        duration_minutes=30,
        priority="high",
    )
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a pet should increase its task list by one."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0

    task = Task(
        title="Evening Walk",
        task_type="walk",
        duration_minutes=20,
        priority="medium",
        pet_name="Mochi",
    )
    pet.add_task(task)
    assert len(pet.tasks) == 1


# ══════════════════════════════════════════════════════════════════════════════
# 1. SCHEDULE GENERATION  —  Scheduler.generate_plan()
# ══════════════════════════════════════════════════════════════════════════════

class TestScheduleGeneration:

    def test_empty_tasks_returns_empty_plan(self):
        """Zero tasks → empty plan with no crash."""
        owner = make_owner()
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert plan.scheduled_tasks == []
        assert plan.skipped_tasks == []
        assert plan.total_duration_minutes == 0

    def test_tasks_within_budget_all_scheduled(self):
        """When total duration fits the budget, all tasks are scheduled."""
        owner = make_owner(available_minutes=120)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Walk", duration=30, pet_name="Rex"))
        pet.add_task(make_task("Feed", task_type="feeding", duration=20, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert len(plan.scheduled_tasks) == 2
        assert plan.skipped_tasks == []

    def test_low_priority_task_skipped_when_over_budget(self):
        """Low-priority task is skipped when the budget can only fit one task."""
        owner = make_owner(available_minutes=30)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("High Task", priority="high", duration=30, pet_name="Rex"))
        pet.add_task(make_task("Low Task", priority="low", duration=30, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        scheduled = [t.title for t in plan.scheduled_tasks]
        skipped = [t.title for t in plan.skipped_tasks]
        assert "High Task" in scheduled
        assert "Low Task" in skipped

    def test_fixed_tasks_always_included_even_over_budget(self):
        """Fixed-time tasks are scheduled even when total time exceeds the budget."""
        owner = make_owner(available_minutes=10)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Fixed Appointment", task_type="appointment",
                               duration=60, scheduled_time="09:00", pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert any(t.title == "Fixed Appointment" for t in plan.scheduled_tasks)

    def test_overload_warning_set_when_over_budget(self):
        """overload_warning is not None when tasks exceed available minutes."""
        owner = make_owner(available_minutes=30)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Task A", duration=20, pet_name="Rex"))
        pet.add_task(make_task("Task B", duration=20, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert plan.overload_warning is not None

    def test_no_overload_warning_within_budget(self):
        """overload_warning is None when all tasks fit within the budget."""
        owner = make_owner(available_minutes=120)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Walk", duration=30, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert plan.overload_warning is None

    def test_urgency_boost_promotes_health_critical_task(self):
        """A pet with a matching special need causes its task to be prioritised over
        a same-priority task belonging to a pet with no special needs."""
        owner = make_owner(available_minutes=30)
        rex = Pet("Rex", "dog", 3, special_needs=["insulin injection"])
        rex.add_task(make_task("Rex Meds", task_type="medication",
                               priority="medium", duration=30, pet_name="Rex"))
        luna = Pet("Luna", "cat", 2)
        luna.add_task(make_task("Luna Groom", task_type="grooming",
                                priority="medium", duration=30, pet_name="Luna"))
        owner.add_pet(rex)
        owner.add_pet(luna)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        scheduled = [t.title for t in plan.scheduled_tasks]
        assert "Rex Meds" in scheduled
        assert "Luna Groom" not in scheduled

    def test_dependency_order_medication_before_feeding(self):
        """Medication tasks must appear before feeding tasks even when feeding has
        higher priority, because clinical dependency ordering overrides priority."""
        owner = make_owner(available_minutes=120)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Breakfast", task_type="feeding",
                               priority="high", duration=10, pet_name="Rex"))
        pet.add_task(make_task("Morning Meds", task_type="medication",
                               priority="medium", duration=10, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        titles = [t.title for t in plan.scheduled_tasks]
        assert titles.index("Morning Meds") < titles.index("Breakfast")

    def test_reasoning_recorded_for_every_task(self):
        """Every scheduled and skipped task must have a reasoning entry."""
        owner = make_owner(available_minutes=30)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Walk", priority="high", duration=30, pet_name="Rex"))
        pet.add_task(make_task("Bath", priority="low", duration=30, pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        all_tasks = plan.scheduled_tasks + plan.skipped_tasks
        for task in all_tasks:
            assert plan.get_reason(task.task_id) != "No reason recorded."


# ══════════════════════════════════════════════════════════════════════════════
# 2. RECURRING TASK ACTIVATION  —  RecurringTask.is_active_today()
# ══════════════════════════════════════════════════════════════════════════════

class TestRecurringTaskActivation:

    def _rt(self, frequency="daily", days_of_week=None, interval_days=None,
            start_date=None):
        return RecurringTask(
            title="Test Task", task_type="other",
            duration_minutes=15, priority="medium",
            frequency=frequency, days_of_week=days_of_week,
            interval_days=interval_days,
            start_date=start_date or TODAY.isoformat(),
        )

    # ── daily ──────────────────────────────────────────────────────────────────

    def test_daily_always_active(self):
        rt = self._rt("daily")
        for day in range(7):
            assert rt.is_active_today(day, TODAY) is True

    # ── weekly ─────────────────────────────────────────────────────────────────

    def test_weekly_active_on_matching_day(self):
        rt = self._rt("weekly", days_of_week=[0, 2, 4])  # Mon, Wed, Fri
        assert rt.is_active_today(0, TODAY) is True
        assert rt.is_active_today(2, TODAY) is True

    def test_weekly_inactive_on_non_matching_day(self):
        rt = self._rt("weekly", days_of_week=[0, 2, 4])
        assert rt.is_active_today(1, TODAY) is False   # Tuesday
        assert rt.is_active_today(5, TODAY) is False   # Saturday

    def test_weekly_no_days_of_week_active_every_day(self):
        """weekly with days_of_week=None must be active every day."""
        rt = self._rt("weekly", days_of_week=None)
        for day in range(7):
            assert rt.is_active_today(day, TODAY) is True

    # ── biweekly ───────────────────────────────────────────────────────────────

    def test_biweekly_active_on_start_date(self):
        """Day 0 → 0 % 14 == 0, must be active."""
        rt = self._rt("biweekly", start_date=TODAY.isoformat())
        assert rt.is_active_today(0, TODAY) is True

    def test_biweekly_inactive_7_days_after_start(self):
        """Day 7 → 7 % 14 != 0, must NOT be active."""
        rt = self._rt("biweekly", start_date=TODAY.isoformat())
        assert rt.is_active_today(0, TODAY + timedelta(days=7)) is False

    def test_biweekly_active_14_days_after_start(self):
        """Day 14 → 14 % 14 == 0, must be active."""
        rt = self._rt("biweekly", start_date=TODAY.isoformat())
        assert rt.is_active_today(0, TODAY + timedelta(days=14)) is True

    def test_biweekly_inactive_on_odd_multiples(self):
        """Days 7, 21, 35 must not fire for a biweekly task."""
        rt = self._rt("biweekly", start_date=TODAY.isoformat())
        for offset in [7, 21, 35]:
            assert rt.is_active_today(0, TODAY + timedelta(days=offset)) is False

    # ── every_n_days ───────────────────────────────────────────────────────────

    def test_every_n_days_active_on_start_date(self):
        rt = self._rt("every_n_days", interval_days=5, start_date=TODAY.isoformat())
        assert rt.is_active_today(0, TODAY) is True

    def test_every_n_days_inactive_between_intervals(self):
        rt = self._rt("every_n_days", interval_days=5, start_date=TODAY.isoformat())
        for offset in [1, 2, 3, 4]:
            assert rt.is_active_today(0, TODAY + timedelta(days=offset)) is False

    def test_every_n_days_active_at_interval_multiples(self):
        rt = self._rt("every_n_days", interval_days=5, start_date=TODAY.isoformat())
        assert rt.is_active_today(0, TODAY + timedelta(days=5)) is True
        assert rt.is_active_today(0, TODAY + timedelta(days=10)) is True

    def test_every_n_days_interval_1_behaves_like_daily(self):
        """interval_days=1 means every day, same as daily."""
        rt = self._rt("every_n_days", interval_days=1, start_date=TODAY.isoformat())
        for offset in range(7):
            assert rt.is_active_today(0, TODAY + timedelta(days=offset)) is True

    # ── start_date guard ───────────────────────────────────────────────────────

    def test_recurring_before_start_date_not_active(self):
        """A task with a future start_date must not appear before it begins."""
        future = TODAY + timedelta(days=5)
        rt = self._rt("biweekly", start_date=future.isoformat())
        assert rt.is_active_today(0, TODAY) is False

    # ── Pet.get_tasks_today integration ────────────────────────────────────────

    def test_get_tasks_today_includes_active_recurring(self):
        pet = Pet("Rex", "dog", 3)
        rt = RecurringTask("Daily Feed", "feeding", 20, "medium",
                           frequency="daily", pet_name="Rex",
                           start_date=TODAY.isoformat())
        pet.add_recurring_task(rt)
        tasks = pet.get_tasks_today(0, TODAY)
        assert any(t.title == "Daily Feed" for t in tasks)

    def test_get_tasks_today_excludes_inactive_recurring(self):
        """A weekly task set for Tuesday only must not appear on Monday."""
        pet = Pet("Rex", "dog", 3)
        rt = RecurringTask("Tue Walk", "walk", 30, "medium",
                           frequency="weekly", days_of_week=[1],  # Tuesday
                           pet_name="Rex", start_date=TODAY.isoformat())
        pet.add_recurring_task(rt)
        tasks = pet.get_tasks_today(0, TODAY)   # Monday
        assert not any(t.title == "Tue Walk" for t in tasks)


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONFLICT DETECTION  —  Scheduler.detect_conflicts()
# ══════════════════════════════════════════════════════════════════════════════

class TestConflictDetection:

    def _scheduler(self):
        return Scheduler(make_owner())

    def test_overlapping_fixed_tasks_flagged(self):
        """09:00–09:30 and 09:15–09:45 overlap → one conflict warning."""
        s = self._scheduler()
        t1 = make_task("Walk", duration=30, scheduled_time="09:00")
        t2 = make_task("Meds", task_type="medication", duration=30, scheduled_time="09:15")
        conflicts = s.detect_conflicts([t1, t2])
        assert len(conflicts) == 1
        assert "Walk" in conflicts[0]
        assert "Meds" in conflicts[0]

    def test_back_to_back_not_a_conflict(self):
        """09:00–09:30 immediately followed by 09:30–10:00 is NOT an overlap."""
        s = self._scheduler()
        t1 = make_task("Walk", duration=30, scheduled_time="09:00")
        t2 = make_task("Feed", task_type="feeding", duration=30, scheduled_time="09:30")
        assert s.detect_conflicts([t1, t2]) == []

    def test_no_fixed_tasks_returns_empty_list(self):
        """Empty input → no conflicts, no crash."""
        assert self._scheduler().detect_conflicts([]) == []

    def test_single_fixed_task_no_conflict(self):
        """A single fixed task cannot conflict with anything."""
        s = self._scheduler()
        t = make_task("Walk", duration=30, scheduled_time="09:00")
        assert s.detect_conflicts([t]) == []

    def test_partial_overlap_detected(self):
        """Task B starts before Task A ends — partial overlap must be caught."""
        s = self._scheduler()
        t1 = make_task("Appointment", task_type="appointment",
                       duration=60, scheduled_time="10:00")
        t2 = make_task("Groom", task_type="grooming",
                       duration=30, scheduled_time="10:45")
        assert len(s.detect_conflicts([t1, t2])) == 1

    def test_non_overlapping_tasks_no_conflict(self):
        """Two well-separated fixed tasks produce no conflicts."""
        s = self._scheduler()
        t1 = make_task("Morning Walk", duration=30, scheduled_time="08:00")
        t2 = make_task("Evening Walk", duration=30, scheduled_time="18:00")
        assert s.detect_conflicts([t1, t2]) == []

    def test_multiple_overlapping_pairs_all_reported(self):
        """Three mutually overlapping tasks must report all three conflict pairs."""
        s = self._scheduler()
        t1 = make_task("A", duration=60, scheduled_time="09:00")
        t2 = make_task("B", duration=60, scheduled_time="09:15")
        t3 = make_task("C", duration=60, scheduled_time="09:30")
        assert len(s.detect_conflicts([t1, t2, t3])) == 3

    def test_generate_plan_populates_conflicts_in_daily_plan(self):
        """generate_plan must surface conflict warnings in DailyPlan.conflicts."""
        owner = make_owner(available_minutes=300)
        pet = Pet("Rex", "dog", 3)
        pet.add_task(make_task("Walk", duration=30, scheduled_time="09:00", pet_name="Rex"))
        pet.add_task(make_task("Meds", task_type="medication",
                               duration=30, scheduled_time="09:15", pet_name="Rex"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan(0, TODAY)
        assert len(plan.conflicts) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. TASK COMPLETION & NEXT-OCCURRENCE  —  Pet.complete_task()
# ══════════════════════════════════════════════════════════════════════════════

class TestTaskCompletion:

    def test_complete_daily_task_creates_next_day_task(self):
        """Completing a daily recurring task auto-adds a task due tomorrow."""
        pet = Pet("Rex", "dog", 3)
        task = make_task("Daily Walk", task_type="walk",
                         recurrence="daily", pet_name="Rex")
        pet.add_task(task)

        initial_count = len(pet.tasks)
        pet.complete_task(task.task_id, today_date=TODAY)

        assert task.is_completed is True
        assert len(pet.tasks) == initial_count + 1
        assert pet.tasks[-1].next_due_date == TODAY + timedelta(days=1)

    def test_complete_weekly_task_creates_next_week_task(self):
        """Completing a weekly recurring task adds a task due in 7 days."""
        pet = Pet("Rex", "dog", 3)
        task = make_task("Weekly Groom", task_type="grooming",
                         recurrence="weekly", pet_name="Rex")
        pet.add_task(task)

        pet.complete_task(task.task_id, today_date=TODAY)

        assert task.is_completed is True
        assert pet.tasks[-1].next_due_date == TODAY + timedelta(weeks=1)

    def test_complete_one_off_task_no_new_task_created(self):
        """Completing a non-recurring task must NOT spawn a new task."""
        pet = Pet("Rex", "dog", 3)
        task = make_task("One-off Bath", recurrence=None, pet_name="Rex")
        pet.add_task(task)

        initial_count = len(pet.tasks)
        pet.complete_task(task.task_id, today_date=TODAY)

        assert task.is_completed is True
        assert len(pet.tasks) == initial_count

    def test_complete_invalid_task_id_returns_none(self):
        """complete_task with a nonexistent ID must return None without crashing."""
        pet = Pet("Rex", "dog", 3)
        result = pet.complete_task("nonexistent-id", today_date=TODAY)
        assert result is None

    def test_next_task_inherits_all_properties(self):
        """The auto-generated next task inherits title, type, duration, priority,
        and starts out incomplete."""
        pet = Pet("Rex", "dog", 3)
        task = make_task("Daily Feed", task_type="feeding", duration=15,
                         priority="high", recurrence="daily", pet_name="Rex")
        pet.add_task(task)
        pet.complete_task(task.task_id, today_date=TODAY)

        new_task = pet.tasks[-1]
        assert new_task.title == "Daily Feed"
        assert new_task.task_type == "feeding"
        assert new_task.duration_minutes == 15
        assert new_task.priority == "high"
        assert new_task.is_completed is False

    def test_complete_task_returns_the_completed_task(self):
        """complete_task should return the Task object that was completed."""
        pet = Pet("Rex", "dog", 3)
        task = make_task("Walk", recurrence="daily", pet_name="Rex")
        pet.add_task(task)
        result = pet.complete_task(task.task_id, today_date=TODAY)
        assert result is task


# ══════════════════════════════════════════════════════════════════════════════
# 5. TIME-SLOT ASSIGNMENT & SORTING CORRECTNESS  —  Scheduler._assign_times()
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeSlotAssignment:

    def _scheduler(self, day_start="08:00", buffer_minutes=5):
        owner = Owner("Alex", available_minutes=480,
                      day_start=day_start, buffer_minutes=buffer_minutes)
        return Scheduler(owner)

    # ── Sorting correctness ────────────────────────────────────────────────────

    def test_sort_by_time_chronological_order(self):
        """sort_by_time returns tasks earliest-to-latest; tasks with no time go last."""
        s = self._scheduler()
        t1 = make_task("C Task", scheduled_time="14:00")
        t2 = make_task("A Task", scheduled_time="08:30")
        t3 = make_task("B Task", scheduled_time="11:00")
        t4 = make_task("No Time", scheduled_time=None)

        result = s.sort_by_time([t1, t2, t3, t4])
        times = [t.scheduled_time for t in result]
        assert times == ["08:30", "11:00", "14:00", None]

    def test_assign_times_returns_chronological_order(self):
        """_assign_times must always return tasks sorted by scheduled_time."""
        s = self._scheduler()
        fixed_late  = make_task("Late Fixed",  duration=30, scheduled_time="15:00")
        fixed_early = make_task("Early Fixed", duration=30, scheduled_time="09:00")
        flex        = make_task("Flexible",    duration=20)
        result = s._assign_times([fixed_late, fixed_early, flex],
                                 day_start="08:00", buffer_minutes=5)
        times = [t.scheduled_time for t in result]
        assert times == sorted(times)

    # ── Placement correctness ──────────────────────────────────────────────────

    def test_single_flexible_task_placed_at_day_start(self):
        """A single flexible task with no fixed tasks is placed exactly at day_start."""
        s = self._scheduler(day_start="08:00")
        task = make_task("Walk", duration=30)
        result = s._assign_times([task], day_start="08:00", buffer_minutes=5)
        assert result[0].scheduled_time == "08:00"

    def test_flexible_task_moved_past_fixed_slot(self):
        """Flexible task must start at or after the fixed task's end time."""
        s = self._scheduler()
        fixed    = make_task("Fixed", duration=30, scheduled_time="08:00")
        flexible = make_task("Flexible", duration=20)
        result   = s._assign_times([fixed, flexible],
                                   day_start="08:00", buffer_minutes=0)
        times = {t.title: t.scheduled_time for t in result}
        flex_h, flex_m = map(int, times["Flexible"].split(":"))
        # Fixed ends at 08:30 → flexible must start at or after 08:30
        assert flex_h * 60 + flex_m >= 8 * 60 + 30

    def test_two_adjacent_fixed_slots_flexible_placed_after_both(self):
        """With fixed1 at 08:00 and fixed2 at 08:30 (each 30 min), the flexible
        task must start at or after 09:00 — the while-changed loop handles this."""
        s = self._scheduler()
        fixed1   = make_task("Fixed1", duration=30, scheduled_time="08:00")
        fixed2   = make_task("Fixed2", duration=30, scheduled_time="08:30")
        flexible = make_task("Flexible", duration=20)
        result   = s._assign_times([fixed1, fixed2, flexible],
                                   day_start="08:00", buffer_minutes=0)
        times = {t.title: t.scheduled_time for t in result}
        flex_h, flex_m = map(int, times["Flexible"].split(":"))
        # Both fixed slots together span 08:00–09:00
        assert flex_h * 60 + flex_m >= 9 * 60

    def test_buffer_minutes_zero_tasks_back_to_back(self):
        """With buffer_minutes=0, consecutive flexible tasks are back-to-back."""
        s = self._scheduler(buffer_minutes=0)
        t1 = make_task("Task A", duration=30)
        t2 = make_task("Task B", duration=20)
        result = s._assign_times([t1, t2], day_start="08:00", buffer_minutes=0)
        sorted_result = sorted(result, key=lambda t: t.scheduled_time)
        assert sorted_result[0].scheduled_time == "08:00"
        assert sorted_result[1].scheduled_time == "08:30"  # no gap

    def test_buffer_minutes_respected_between_flexible_tasks(self):
        """Consecutive flexible tasks must have exactly buffer_minutes gap between them."""
        s = self._scheduler(buffer_minutes=10)
        t1 = make_task("Task A", duration=30)
        t2 = make_task("Task B", duration=30)
        result = s._assign_times([t1, t2], day_start="08:00", buffer_minutes=10)
        sorted_result = sorted(result, key=lambda t: t.scheduled_time)
        t1_h, t1_m = map(int, sorted_result[0].scheduled_time.split(":"))
        t2_h, t2_m = map(int, sorted_result[1].scheduled_time.split(":"))
        gap = (t2_h * 60 + t2_m) - (t1_h * 60 + t1_m + 30)
        assert gap == 10

    def test_custom_day_start_respected(self):
        """Flexible tasks should begin at the owner's custom day_start, not 08:00."""
        s = self._scheduler(day_start="09:30")
        task = make_task("Late Start Task", duration=20)
        result = s._assign_times([task], day_start="09:30", buffer_minutes=5)
        assert result[0].scheduled_time == "09:30"


# ══════════════════════════════════════════════════════════════════════════════
# 6. URGENCY SCORING  —  Task.urgency_score()
# ══════════════════════════════════════════════════════════════════════════════

class TestUrgencyScoring:

    def test_keyword_match_returns_2(self):
        """urgency_score returns 2 when pet special_needs match the task type."""
        pet  = Pet("Rex", "dog", 3, special_needs=["requires insulin injection daily"])
        task = make_task("Insulin", task_type="medication")
        assert task.urgency_score(pet) == 2

    def test_no_keyword_match_returns_0(self):
        """urgency_score returns 0 when no special need keyword matches."""
        pet  = Pet("Luna", "cat", 2, special_needs=["likes cuddles"])
        task = make_task("Walk", task_type="walk")
        assert task.urgency_score(pet) == 0

    def test_no_pet_returns_0(self):
        """urgency_score returns 0 when pet is None."""
        task = make_task("Meds", task_type="medication")
        assert task.urgency_score(None) == 0

    def test_case_insensitive_match(self):
        """Keyword matching is case-insensitive."""
        pet  = Pet("Rex", "dog", 3, special_needs=["INSULIN management"])
        task = make_task("Meds", task_type="medication")
        assert task.urgency_score(pet) == 2

    def test_partial_keyword_match(self):
        """Substring keyword match works (e.g., 'arthrit' matches 'arthritis')."""
        pet  = Pet("Buddy", "dog", 8, special_needs=["arthritis in hind legs"])
        task = make_task("Walk", task_type="walk")
        assert task.urgency_score(pet) == 2

    def test_wrong_task_type_no_match(self):
        """A walk keyword in special_needs does not boost a medication task."""
        pet  = Pet("Rex", "dog", 3, special_needs=["mobility issues"])
        task = make_task("Meds", task_type="medication")
        assert task.urgency_score(pet) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 7. TASK FILTERS  —  TaskFilter static methods
# ══════════════════════════════════════════════════════════════════════════════

class TestTaskFilter:

    def _sample(self):
        tasks = [
            make_task("Rex Walk",  task_type="walk",      priority="high", pet_name="Rex"),
            make_task("Luna Feed", task_type="feeding",   priority="low",  pet_name="Luna"),
            make_task("Rex Meds",  task_type="medication",priority="high", pet_name="Rex"),
        ]
        tasks[0].mark_complete()   # Rex Walk is completed
        return tasks

    def test_filter_by_pet(self):
        tasks = self._sample()
        rex_tasks = TaskFilter.by_pet(tasks, "Rex")
        assert len(rex_tasks) == 2
        assert all(t.pet_name == "Rex" for t in rex_tasks)

    def test_filter_by_type(self):
        tasks = self._sample()
        walks = TaskFilter.by_type(tasks, "walk")
        assert len(walks) == 1
        assert walks[0].title == "Rex Walk"

    def test_filter_by_status_completed(self):
        tasks = self._sample()
        done = TaskFilter.by_status(tasks, completed=True)
        assert len(done) == 1
        assert done[0].title == "Rex Walk"

    def test_filter_by_status_pending(self):
        tasks = self._sample()
        pending = TaskFilter.by_status(tasks, completed=False)
        assert len(pending) == 2

    def test_filter_by_priority_high(self):
        tasks = self._sample()
        high = TaskFilter.by_priority(tasks, "high")
        assert len(high) == 2

    def test_filter_by_priority_low(self):
        tasks = self._sample()
        low = TaskFilter.by_priority(tasks, "low")
        assert len(low) == 1
        assert low[0].title == "Luna Feed"


# ══════════════════════════════════════════════════════════════════════════════
# 8. DAILY PLAN UTILITIES  —  DailyPlan helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestDailyPlan:

    def test_time_remaining_reflects_scheduled_duration(self):
        plan = DailyPlan(available_minutes=120)
        task = make_task("Walk", duration=30)
        plan.add_scheduled_task(task, "reason")
        assert plan.time_remaining() == 90

    def test_all_done_false_when_tasks_incomplete(self):
        plan = DailyPlan(available_minutes=120)
        plan.add_scheduled_task(make_task("Walk", duration=30), "reason")
        assert plan.all_done() is False

    def test_all_done_true_when_all_complete(self):
        plan = DailyPlan(available_minutes=120)
        task = make_task("Walk", duration=30)
        task.mark_complete()
        plan.add_scheduled_task(task, "reason")
        assert plan.all_done() is True

    def test_all_done_false_for_empty_plan(self):
        """An empty plan is not 'all done'."""
        plan = DailyPlan(available_minutes=120)
        assert plan.all_done() is False

    def test_get_reason_for_known_task(self):
        plan = DailyPlan(available_minutes=120)
        task = make_task("Walk", duration=30)
        plan.add_scheduled_task(task, "Included: high priority")
        assert plan.get_reason(task.task_id) == "Included: high priority"

    def test_get_reason_unknown_task_returns_default(self):
        plan = DailyPlan(available_minutes=120)
        assert plan.get_reason("nonexistent-id") == "No reason recorded."

    def test_completion_count(self):
        plan = DailyPlan(available_minutes=120)
        t1 = make_task("Walk", duration=20)
        t2 = make_task("Feed", task_type="feeding", duration=10)
        t1.mark_complete()
        plan.add_scheduled_task(t1, "reason")
        plan.add_scheduled_task(t2, "reason")
        assert plan.completion_count() == 1
