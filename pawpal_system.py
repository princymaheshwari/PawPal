import uuid
from datetime import datetime


class Pet:
    def __init__(self, name, species, age, breed="", special_needs=None):
        self.name = name
        self.species = species
        self.age = age
        self.breed = breed
        self.special_needs = special_needs if special_needs is not None else []

    def add_special_need(self, need):
        pass

    def remove_special_need(self, need):
        pass

    def has_special_needs(self):
        pass

    def __str__(self):
        pass


class Task:
    def __init__(self, title, task_type, duration_minutes, priority,
                 scheduled_time=None, pet_name=None, notes=""):
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
        pass

    def mark_incomplete(self):
        pass

    def priority_score(self):
        pass

    def is_fixed_time(self):
        pass

    def __str__(self):
        pass


class RecurringTask:
    def __init__(self, title, task_type, duration_minutes, priority,
                 frequency="daily", scheduled_time=None, days_of_week=None,
                 pet_name=None, notes=""):
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
        pass

    def to_task(self):
        pass

    def __str__(self):
        pass


class Preference:
    def __init__(self, category, task_type, value, description=""):
        self.category = category
        self.task_type = task_type
        self.value = value
        self.description = description

    def matches_task_type(self, task_type):
        pass

    def __str__(self):
        pass


class Owner:
    def __init__(self, name, available_minutes=120):
        self.name = name
        self.available_minutes = available_minutes
        self.pets = []
        self.tasks = []
        self.recurring_tasks = []
        self.preferences = []

    def add_pet(self, pet):
        pass

    def remove_pet(self, pet_name):
        pass

    def get_pet(self, pet_name):
        pass

    def add_task(self, task):
        pass

    def remove_task(self, task_id):
        pass

    def add_recurring_task(self, recurring_task):
        pass

    def remove_recurring_task(self, title):
        pass

    def add_preference(self, preference):
        pass

    def remove_preference(self, task_type):
        pass

    def set_available_time(self, minutes):
        pass

    def get_preferences_for(self, task_type):
        pass

    def all_tasks_today(self, day_of_week):
        pass


class DailyPlan:
    def __init__(self, available_minutes):
        self.scheduled_tasks = []
        self.skipped_tasks = []
        self.total_duration_minutes = 0
        self.available_minutes = available_minutes
        self.reasoning = {}
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def add_scheduled_task(self, task, reason):
        pass

    def add_skipped_task(self, task, reason):
        pass

    def get_reason(self, task_id):
        pass

    def time_remaining(self):
        pass

    def completion_count(self):
        pass

    def all_done(self):
        pass

    def summary(self):
        pass


class Scheduler:
    def __init__(self, owner):
        self.owner = owner

    def generate_plan(self, day_of_week):
        pass

    def _collect_tasks(self, day_of_week):
        pass

    def _separate_fixed(self, tasks):
        pass

    def _sort_flexible(self, tasks):
        pass

    def _apply_preferences(self, tasks):
        pass

    def _fit_tasks(self, fixed, flexible, budget):
        pass

    def _build_reasoning(self, task, included):
        pass

    def _assign_times(self, tasks):
        pass
