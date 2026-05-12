# Classroom & Teacher Management — Design Spec

**Date:** 2026-05-12  
**Status:** Approved

---

## Problem

The current system treats all teachers and students as a flat pool. Every teacher sees every subject; there is no concept of a classroom grouping students together; and teacher dashboards have no way to scope data to a specific class. Attendance analytics cannot be displayed meaningfully because there is no realistic seed data.

---

## Goals

1. Admin can create and manage named classrooms (e.g., "CSE 8th Sem A").
2. Students are individually assigned to exactly one classroom.
3. When adding/editing a teacher, admin assigns them specific `(classroom, subject)` pairs.
4. Teacher dashboard scopes all data to an active classroom, switchable via a header dropdown.
5. Every student has 30 days of randomly-generated realistic attendance data on first run.

---

## Data Model

### New table: `classrooms`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `name` | String(100) | e.g., "CSE 8th Sem A" |
| `semester` | Integer | |
| `section` | String(10) | A, B, C… |
| `department` | String(100) | |
| `academic_year` | String(20) | e.g., "2025-26" |
| `is_active` | Boolean | default True |

### New table: `teacher_assignments`

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `teacher_id` | FK → users.id | |
| `classroom_id` | FK → classrooms.id | |
| `subject_id` | FK → subjects.id | |

Unique constraint on `(teacher_id, classroom_id, subject_id)`.

A single row means: "this teacher teaches this subject in this classroom."

### Modified table: `users`

- Add `classroom_id` (FK → classrooms.id, nullable) for students.
- Existing `semester` and `section` fields are kept as denormalized copies (used by the AI RAG context builder — no change to that pipeline).

---

## Admin UI

### New: Manage Classrooms (`/admin/classrooms`)

- List view: table of classrooms with name, semester, section, student count, teacher count, active status.
- Create/edit form: name, semester, section, department, academic year.
- Delete (soft — sets `is_active=False`).

### New: Classroom Detail (`/admin/classrooms/<id>`)

Two panels:

- **Students panel**: list of students currently in this classroom. "Add student" button opens a searchable modal over all unassigned students. "Remove" unlinks a student (sets their `classroom_id` to None).
- **Teacher assignments panel**: each row shows teacher name + subject. "Add assignment" opens a form with teacher dropdown + subject dropdown. Delete removes the `teacher_assignment` row.

### Modified: Manage Users (`/admin/manage-users`)

- When adding a student: optional "Assign to Classroom" dropdown (all active classrooms). Can be set later from classroom detail page.
- Student table gains a "Classroom" column.

### Modified: Manage Users — Teacher form

- Adding/editing a teacher gains an "Assignments" section below the basic fields.
- Dynamic row list: each row has a classroom dropdown + subject dropdown. An "Add row" button appends a new blank row. Saving the form upserts all rows into `teacher_assignments` (deletes removed rows, inserts new ones).

### Navigation

A "Classrooms" link is added to the admin sidebar between "Users" and "Subjects."

---

## Teacher Dashboard

### Classroom context

- Stored in Flask session as `active_classroom_id`.
- Set automatically to the teacher's first assigned classroom on login.
- A compact dropdown in the top navbar lists all the teacher's classrooms. Selecting one updates the session and reloads the current page.
- If a teacher has exactly one classroom, the dropdown is hidden.
- If a teacher has no classrooms, a banner replaces the dashboard: "No classrooms assigned — contact admin."

### Scoped pages

| Page | Scoping change |
|------|---------------|
| Dashboard (`/teacher/dashboard`) | Stats cards (students, avg attendance, at-risk count, subjects) scoped to active classroom |
| Mark Attendance | Student list filtered to active classroom; subject dropdown filtered to teacher's subjects in that classroom |
| View Students | Only students in active classroom |
| Class Attendance | Only active classroom |
| Enter Marks | Subject dropdown filtered to teacher's assigned subjects in active classroom |

---

## Attendance Seeding

Runs inside `seed_database()` in `utils/db_utils.py`, only when the DB is empty.

### Demo data created

- **2 classrooms**: "CSE 8th Sem A" (sem 8, section A) and "CSE 8th Sem B" (sem 8, section B).
- **60 students**: `student1`–`student60`, IDs `CS001`–`CS060`. First 30 → Classroom A, next 30 → Classroom B. Password: `student123`.
- **Teacher assignments** (explicit rows in `teacher_assignments`):
  - `teacher1` → Classroom A → Data Structures
  - `teacher1` → Classroom A → Operating Systems
  - `teacher1` → Classroom B → Algorithms
  - `teacher2` → Classroom A → DBMS
  - `teacher2` → Classroom B → Web Technologies
  - `teacher2` → Classroom B → Computer Networks

### Attendance generation

For each student, for each subject they have classes in, for each of the last 30 calendar days:

- **60% of students** (randomly selected): 75–92% presence rate — randomly mark each day PRESENT or ABSENT at that rate.
- **25% of students**: 55–74% — below the 75% threshold, triggering "at risk" warnings.
- **15% of students**: 93–100% — excellent attendance.

All seeded records: `is_manual=True`, `confidence_score=None`.

### Reset

Delete `database/attendance.db` and restart — the full seed (classrooms, students, 30-day history) re-runs automatically.

---

## Out of Scope

- Face recognition enrollment for the 60 seeded students (manual attendance only in demo).
- Timetable changes (existing timetable model unchanged).
- AI RAG pipeline changes (existing context builder unchanged).
- Multi-department classrooms.
