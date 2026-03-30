# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**Core User Actions**

The core actions a user should be able to perform are:

1. **Add a pet** — The user can enter basic information about their pet (name, species, age, and any special needs). This gives the scheduler the context it needs to tailor task recommendations to that specific animal.

2. **Add and manage care tasks** — The user can create tasks such as morning walks, feedings, medication doses, grooming sessions, or vet appointments. Each task includes a title, estimated duration, and a priority level (low, medium, or high) so the scheduler knows what to fit in first.

3. **Set available time and preferences** — Before generating a plan, the user tells the app how much free time they have today (e.g., 90 minutes) and any personal preferences (e.g., prefer walks in the morning, medications must happen at a fixed time). This acts as the main constraint the scheduler works within.

4. **Generate and view the daily schedule** — The user can request a prioritized daily plan. The app orders tasks by priority and fits them within the available time window, then displays the schedule clearly along with a short explanation of why each task was included and when it should happen.

5. **Mark tasks as completed** — Throughout the day, the user can check off tasks as they finish them. This lets the app track what still needs to be done and could be used in future sessions to surface recurring tasks that are often skipped.

6. **Add a recurring appointment** — The user can schedule standing appointments (e.g., weekly vet checkup, daily 7 AM feeding) that automatically appear in the plan every day or on a set schedule, so the user does not have to re-enter them manually.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
