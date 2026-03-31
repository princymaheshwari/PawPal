import pathlib
import streamlit as st
from datetime import datetime, date
from pawpal_system import (Owner, Pet, Task, RecurringTask, Preference, Scheduler, TaskFilter,
                           PRIORITY_EMOJI, TASK_TYPE_EMOJI, STATUS_EMOJI)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner — powered by smart scheduling algorithms.")

DATA_FILE = pathlib.Path("data.json")

def save_data():
    """Write the current owner state to data.json."""
    if st.session_state.owner is not None:
        st.session_state.owner.save_to_json(DATA_FILE)

# ---------------------------------------------------------------------------
# Session state initialisation — load from data.json if it exists
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    if DATA_FILE.exists():
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = None
    else:
        st.session_state.owner = None
if "plan" not in st.session_state:
    st.session_state.plan = None

# ---------------------------------------------------------------------------
# Section 1: Owner setup  (Algorithm D: day_start + buffer_minutes)
# ---------------------------------------------------------------------------
st.header("1. Owner Setup")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
        available_minutes = st.number_input(
            "Minutes available today",
            min_value=10, max_value=480, value=120, step=10,
        )
    with col2:
        day_start = st.text_input(
            "Day start time (HH:MM)",
            value="08:00",
            help="Flexible tasks are placed starting from this time.",
        )
        buffer_minutes = st.number_input(
            "Buffer between tasks (minutes)",
            min_value=0, max_value=30, value=5, step=1,
            help="Gap inserted between consecutive flexible tasks so the schedule isn't artificially packed.",
        )
    submitted = st.form_submit_button("Save owner")
    if submitted:
        if st.session_state.owner is None:
            st.session_state.owner = Owner(
                name=owner_name,
                available_minutes=int(available_minutes),
                day_start=day_start.strip(),
                buffer_minutes=int(buffer_minutes),
            )
        else:
            st.session_state.owner.name = owner_name
            st.session_state.owner.set_available_time(int(available_minutes))
            st.session_state.owner.day_start = day_start.strip()
            st.session_state.owner.buffer_minutes = int(buffer_minutes)
        save_data()
        st.success(
            f"Owner saved: {owner_name} | {available_minutes} min | "
            f"starts {day_start} | {buffer_minutes}-min buffer"
        )

if st.session_state.owner is None:
    st.info("Fill in the owner form above to get started.")
    st.stop()

owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Section 2: Add a pet
# ---------------------------------------------------------------------------
st.header("2. Add a Pet")

with st.form("pet_form"):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "bird", "other"])
    with col2:
        age = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
        breed = st.text_input("Breed (optional)", value="")
    special_needs = st.text_input(
        "Special needs (comma-separated)",
        value="",
        help="e.g. 'insulin injection, arthritis' — tasks whose type matches a keyword here get a +2 urgency boost and float to the top of the schedule.",
    )
    add_pet = st.form_submit_button("Add pet")
    if add_pet:
        if owner.get_pet(pet_name) is not None:
            st.warning(f"{pet_name} is already added.")
        else:
            needs = [n.strip() for n in special_needs.split(",") if n.strip()]
            new_pet = Pet(name=pet_name, species=species, age=age, breed=breed, special_needs=needs)
            owner.add_pet(new_pet)
            save_data()
            st.success(f"Added {new_pet}")

if owner.pets:
    st.write("**Your pets:**")
    for pet in owner.pets:
        needs_label = ", ".join(pet.special_needs) if pet.has_special_needs() else "none"
        st.write(f"- **{pet.name}** ({pet.species}, {pet.age} yr) | Special needs: _{needs_label}_")
else:
    st.info("No pets added yet.")

# ---------------------------------------------------------------------------
# Section 3: Add one-off tasks
# ---------------------------------------------------------------------------
st.header("3. Add Tasks")

if not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            task_pet = st.selectbox("Which pet?", pet_names)
            task_title = st.text_input("Task title", value="Morning walk")
            task_type = st.selectbox(
                "Task type",
                ["medication", "feeding", "walk", "grooming", "appointment", "other"],
                help="Tasks are scheduled in clinical order: medication → feeding → walk → grooming → appointment",
            )
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            scheduled_time = st.text_input("Fixed time (HH:MM, blank = flexible)", value="")
        notes = st.text_input("Notes (optional)", value="")
        add_task = st.form_submit_button("Add task")
        if add_task:
            time_val = scheduled_time.strip() if scheduled_time.strip() else None
            new_task = Task(
                title=task_title,
                task_type=task_type,
                duration_minutes=int(duration),
                priority=priority,
                scheduled_time=time_val,
                pet_name=task_pet,
                notes=notes,
            )
            owner.get_pet(task_pet).add_task(new_task)
            save_data()
            st.success(f"Added task: {new_task}")

    total_tasks = sum(len(p.tasks) for p in owner.pets)
    if total_tasks > 0:
        st.write("**Current tasks:**")
        for pet in owner.pets:
            if pet.tasks:
                st.write(f"_{pet.name}_")
                for t in pet.tasks:
                    time_label = f" @ {t.scheduled_time}" if t.scheduled_time else " (flexible)"
                    st.write(f"  - [{t.priority.upper()}] {t.title} — {t.duration_minutes} min{time_label}")
    else:
        st.info("No tasks added yet.")

# ---------------------------------------------------------------------------
# Section 3.5: Add recurring tasks  (Algorithm E)
# ---------------------------------------------------------------------------
st.header("3.5  Add Recurring Tasks")
st.caption("Recurring task templates generate a fresh task instance each day they are active.")

if not owner.pets:
    st.info("Add at least one pet before adding recurring tasks.")
else:
    with st.form("recurring_form"):
        col1, col2 = st.columns(2)
        with col1:
            rt_pet = st.selectbox("Which pet?", [p.name for p in owner.pets], key="rt_pet")
            rt_title = st.text_input("Task title", value="Daily Feeding", key="rt_title")
            rt_type = st.selectbox(
                "Task type",
                ["medication", "feeding", "walk", "grooming", "appointment", "other"],
                key="rt_type",
            )
            rt_priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="rt_priority")
        with col2:
            rt_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=10, key="rt_dur")
            rt_time = st.text_input("Fixed time (HH:MM, blank = flexible)", value="08:00", key="rt_time")
            rt_freq = st.selectbox(
                "Frequency",
                ["daily", "weekly", "biweekly", "every_n_days"],
                key="rt_freq",
                help="daily=every day | weekly=specific days | biweekly=every 14 days | every_n_days=custom interval",
            )
            rt_days = st.text_input(
                "Days of week (for weekly, e.g. Mon,Wed,Fri — leave blank otherwise)",
                value="",
                key="rt_days",
            )
            rt_interval = st.number_input(
                "Interval days (for every_n_days)",
                min_value=1, max_value=365, value=7,
                key="rt_interval",
            )
            rt_start = st.date_input(
                "Start date (for biweekly / every_n_days)",
                value=date.today(),
                key="rt_start",
            )
        rt_notes = st.text_input("Notes (optional)", value="", key="rt_notes")
        add_rt = st.form_submit_button("Add recurring task")
        if add_rt:
            days_list = [d.strip() for d in rt_days.split(",") if d.strip()] or None
            time_val = rt_time.strip() if rt_time.strip() else None
            new_rt = RecurringTask(
                title=rt_title,
                task_type=rt_type,
                duration_minutes=int(rt_duration),
                priority=rt_priority,
                frequency=rt_freq,
                scheduled_time=time_val,
                days_of_week=days_list,
                pet_name=rt_pet,
                notes=rt_notes,
                interval_days=int(rt_interval) if rt_freq == "every_n_days" else None,
                start_date=rt_start if rt_freq in ("biweekly", "every_n_days") else None,
            )
            owner.get_pet(rt_pet).add_recurring_task(new_rt)
            save_data()
            st.success(f"Added recurring task: {new_rt}")

    for pet in owner.pets:
        if pet.recurring_tasks:
            st.write(f"_{pet.name}_ recurring tasks:")
            for rt in pet.recurring_tasks:
                freq_label = rt.frequency
                if rt.interval_days:
                    freq_label += f" (every {rt.interval_days} days)"
                st.write(f"  - [{rt.priority.upper()}] {rt.title} | {rt.task_type} | {freq_label}")

# ---------------------------------------------------------------------------
# Section 4: Scheduling preferences
# ---------------------------------------------------------------------------
st.header("4. Scheduling Preferences (optional)")

with st.form("pref_form"):
    pref_task_type = st.selectbox("Task type", ["walk", "feeding", "medication", "grooming", "appointment", "other"])
    pref_value = st.selectbox("Preferred time of day", ["morning", "afternoon", "evening"])
    add_pref = st.form_submit_button("Add preference")
    if add_pref:
        pref = Preference(
            category="time_of_day",
            task_type=pref_task_type,
            value=pref_value,
            description=f"Prefer {pref_task_type}s in the {pref_value}",
        )
        owner.add_preference(pref)
        save_data()
        st.success(f"Preference saved: {pref}")

if owner.preferences:
    st.write("**Active preferences:**")
    for p in owner.preferences:
        st.write(f"- {p}")

# ---------------------------------------------------------------------------
# Section 5: Generate schedule
# ---------------------------------------------------------------------------
st.header("5. Generate Today's Schedule")

if st.button("Generate schedule", type="primary"):
    if not owner.pets or all(len(p.tasks) + len(p.recurring_tasks) == 0 for p in owner.pets):
        st.warning("Add at least one task or recurring task before generating a schedule.")
    else:
        today_dow = datetime.now().strftime("%A")
        today_date = date.today()
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan(today_dow, today_date)
        st.session_state.plan = plan

if st.session_state.plan is not None:
    plan = st.session_state.plan
    today_label = datetime.now().strftime("%A, %B %d")
    st.subheader(f"Schedule for {today_label}")

    # --- Algorithm G: Overload Warning ---
    if plan.overload_warning:
        st.warning(f"**Overload Warning:** {plan.overload_warning}")

    if plan.conflicts:
        for msg in plan.conflicts:
            st.error(f"**Scheduling Conflict:** {msg}")

    # --- Budget Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Budget", f"{plan.available_minutes} min")
    col2.metric("Scheduled", f"{plan.total_duration_minutes} min")
    col3.metric("Remaining", f"{plan.time_remaining()} min")
    col4.metric("Tasks Done", f"{plan.completion_count()} / {len(plan.scheduled_tasks)}")

    # --- Scheduled tasks table ---
    if plan.scheduled_tasks:
        st.subheader("Scheduled Tasks")
        st.caption(
            "Tasks are ordered by urgency → clinical dependency "
            "(medication → feeding → walk → grooming → appointment) → priority."
        )

        rows = []
        for task in plan.scheduled_tasks:
            time_label = task.scheduled_time if task.scheduled_time else "--:--"
            reason = plan.get_reason(task.task_id)
            is_urgent = "urgent" in reason.lower() or "special need" in reason.lower()
            urgency_flag = "⚡ " if is_urgent else ""
            rows.append({
                "Time": time_label,
                "Task": f"{urgency_flag}{task.title}",
                "Pet": task.pet_name or "-",
                "Type": TASK_TYPE_EMOJI.get(task.task_type, task.task_type),
                "Priority": PRIORITY_EMOJI.get(task.priority, task.priority),
                "Duration (min)": task.duration_minutes,
                "Reason": reason,
            })

        st.table(rows)

        # Highlight any urgency-boosted tasks separately
        urgent_tasks = [
            t for t in plan.scheduled_tasks
            if "urgent" in plan.get_reason(t.task_id).lower()
            or "special need" in plan.get_reason(t.task_id).lower()
        ]
        if urgent_tasks:
            st.info(
                f"**Priority boost applied:** {len(urgent_tasks)} task(s) were moved to the top "
                f"because they match your pet's special needs: "
                + ", ".join(t.title for t in urgent_tasks)
            )

    # --- Skipped tasks ---
    if plan.skipped_tasks:
        st.subheader("Skipped Tasks (over budget)")
        skipped_rows = []
        for task in plan.skipped_tasks:
            skipped_rows.append({
                "Task": task.title,
                "Pet": task.pet_name or "-",
                "Type": TASK_TYPE_EMOJI.get(task.task_type, task.task_type),
                "Priority": PRIORITY_EMOJI.get(task.priority, task.priority),
                "Duration (min)": task.duration_minutes,
                "Reason": plan.get_reason(task.task_id),
            })
        st.table(skipped_rows)

    if plan.all_done():
        st.success("All scheduled tasks are complete!")
    elif not plan.scheduled_tasks:
        st.info("No tasks were scheduled.")

# ---------------------------------------------------------------------------
# Section 6: Filter & View  (Algorithm F — TaskFilter)
# ---------------------------------------------------------------------------
st.header("6. Filter & View Tasks")
st.caption("Slice the full task list without touching the schedule.")

if not owner.pets or all(len(p.tasks) + len(p.recurring_tasks) == 0 for p in owner.pets):
    st.info("Add tasks first.")
else:
    today_dow = datetime.now().strftime("%A")
    all_tasks = owner.all_tasks_today(today_dow, date.today())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_pet = st.selectbox(
            "Filter by pet", ["All"] + [p.name for p in owner.pets], key="f_pet"
        )
    with col2:
        filter_type = st.selectbox(
            "Filter by type",
            ["All", "medication", "feeding", "walk", "grooming", "appointment", "other"],
            key="f_type",
        )
    with col3:
        filter_status = st.selectbox(
            "Filter by status", ["All", "Pending", "Completed"], key="f_status"
        )
    with col4:
        filter_priority = st.selectbox(
            "Filter by priority", ["All", "high", "medium", "low"], key="f_priority"
        )

    filtered = all_tasks
    if filter_pet != "All":
        filtered = TaskFilter.by_pet(filtered, filter_pet)
    if filter_type != "All":
        filtered = TaskFilter.by_type(filtered, filter_type)
    if filter_status == "Pending":
        filtered = TaskFilter.by_status(filtered, completed=False)
    elif filter_status == "Completed":
        filtered = TaskFilter.by_status(filtered, completed=True)
    if filter_priority != "All":
        filtered = TaskFilter.by_priority(filtered, filter_priority)

    # Sort the filtered result by scheduled time (Algorithm: sort_by_time)
    if filtered:
        scheduler = Scheduler(owner)
        filtered_sorted = scheduler.sort_by_time(filtered)
        st.write(f"**{len(filtered_sorted)} task(s) match your filters:**")
        filter_rows = []
        for t in filtered_sorted:
            filter_rows.append({
                "Time": t.scheduled_time if t.scheduled_time else "(flexible)",
                "Task": t.title,
                "Pet": t.pet_name or "-",
                "Type": TASK_TYPE_EMOJI.get(t.task_type, t.task_type),
                "Priority": PRIORITY_EMOJI.get(t.priority, t.priority),
                "Duration (min)": t.duration_minutes,
                "Status": STATUS_EMOJI.get(t.is_completed, "-"),
            })
        st.table(filter_rows)
    else:
        st.info("No tasks match the selected filters.")
