from pawpal_system import Pet, Task


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
