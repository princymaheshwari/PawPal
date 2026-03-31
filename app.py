import streamlit as st
from datetime import datetime
from pawpal_system import Owner, Pet, Task, RecurringTask, Preference, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner.")

# ---------------------------------------------------------------------------
# Session state initialisation
# st.session_state works like a dictionary that survives page reruns.
# We only create the Owner once; every subsequent rerun finds it already there.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None   # set properly in the Owner Setup section below

# ---------------------------------------------------------------------------
# Section 1: Owner setup
# ---------------------------------------------------------------------------
st.header("1. Owner Setup")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input(
        "How many minutes do you have available today?",
        min_value=10, max_value=480, value=120, step=10,
    )
    submitted = st.form_submit_button("Save owner")
    if submitted:
        # If an owner already exists, keep their pets and preferences
        if st.session_state.owner is None:
            st.session_state.owner = Owner(name=owner_name, available_minutes=int(available_minutes))
        else:
            st.session_state.owner.name = owner_name
            st.session_state.owner.set_available_time(int(available_minutes))
        st.success(f"Owner saved: {owner_name} ({available_minutes} min available today)")

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
    special_needs = st.text_input("Special needs (comma-separated, optional)", value="")
    add_pet = st.form_submit_button("Add pet")
    if add_pet:
        # Avoid adding a duplicate pet with the same name
        if owner.get_pet(pet_name) is not None:
            st.warning(f"{pet_name} is already added.")
        else:
            needs = [n.strip() for n in special_needs.split(",") if n.strip()]
            new_pet = Pet(name=pet_name, species=species, age=age, breed=breed, special_needs=needs)
            owner.add_pet(new_pet)
            st.success(f"Added {new_pet}")

if owner.pets:
    st.write("**Your pets:**")
    for pet in owner.pets:
        needs_label = ", ".join(pet.special_needs) if pet.has_special_needs() else "none"
        st.write(f"- {pet} | Special needs: {needs_label}")
else:
    st.info("No pets added yet.")

# ---------------------------------------------------------------------------
# Section 3: Add tasks to a pet
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
            task_type = st.selectbox("Task type", ["walk", "feeding", "medication", "grooming", "appointment", "other"])
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            scheduled_time = st.text_input("Fixed time (HH:MM, leave blank if flexible)", value="")
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
            st.success(f"Added task: {new_task}")

    # Show all current tasks per pet
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
# Section 4: Scheduling preferences
# ---------------------------------------------------------------------------
st.header("4. Scheduling Preferences (optional)")

with st.form("pref_form"):
    pref_task_type = st.selectbox("Task type to set preference for", ["walk", "feeding", "medication", "grooming", "appointment", "other"])
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
        st.warning("Add at least one task before generating a schedule.")
    else:
        today = datetime.now().strftime("%A")
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan(today)
        st.session_state.plan = plan

if "plan" in st.session_state:
    plan = st.session_state.plan
    st.subheader(f"Schedule for today ({datetime.now().strftime('%A, %B %d')})")
    st.write(f"**Budget:** {plan.available_minutes} min | **Used:** {plan.total_duration_minutes} min | **Remaining:** {plan.time_remaining()} min")

    if plan.scheduled_tasks:
        st.write("**Scheduled:**")
        for task in plan.scheduled_tasks:
            time_label = task.scheduled_time if task.scheduled_time else "--:--"
            st.write(f"- `[{time_label}]` **{task.title}** ({task.duration_minutes} min) | {task.pet_name} | {task.priority.upper()}")
            st.caption(f"  {plan.get_reason(task.task_id)}")

    if plan.skipped_tasks:
        st.write("**Skipped (not enough time):**")
        for task in plan.skipped_tasks:
            st.write(f"- ~~{task.title}~~ ({task.duration_minutes} min) | {task.pet_name}")
            st.caption(f"  {plan.get_reason(task.task_id)}")
