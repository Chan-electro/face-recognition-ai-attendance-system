"""
RAG Agent powered by OpenRouter API with Data-Aware Query Engine.

Architecture:
1. IntentClassifier  - detects if user asks a data question vs info question
2. DataQueryEngine   - runs live DB queries for attendance, marks, student lists
3. ContextBuilder    - reads DB values + document files to build rich context
4. OpenRouter LLM    - sends system prompt (context) + user question, returns answer
"""

import os
import csv
import re
import json
from datetime import datetime
from typing import Any

import requests  # pyre-ignore[21]


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = "minimax/minimax-m2.5:free"
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_BASE_PROMPT = """You are a helpful AI assistant for a college Face Recognition Attendance System.
You have access to the college's live data including students, subjects, faculty, timetable, attendance records, internal marks, and uploaded notes.

RULES:
- Answer questions clearly, concisely, and accurately using the context provided.
- When data tables are provided in the context, present them as nicely formatted lists or tables.
- If asked about specific students, attendance percentages, or marks, use the DATA QUERY RESULTS section.
- If asked to suggest important questions for an exam, generate thoughtful questions based on the subject syllabus/description provided.
- If the answer is not in the provided context, say so honestly.
- Respond in plain text without markdown formatting unless specifically asked."""


# ─────────────────────────────────────────────
# Intent Classifier (rule-based)
# ─────────────────────────────────────────────

class IntentClassifier:
    """Detects data queries and extracts parameters from user questions."""

    # Patterns that indicate a data query
    DATA_PATTERNS = [
        (r'(?:list|show|get|find|who|which)\s+(?:all\s+)?students?\s+(?:whose\s+)?(?:attendance|absent)', 'attendance_filter'),
        (r'(?:below|under|less\s+than|lower\s+than)\s+(\d+)\s*%', 'attendance_threshold'),
        (r'(?:above|over|more\s+than|greater\s+than|higher\s+than)\s+(\d+)\s*%', 'attendance_above'),
        (r'attendance\s+(?:of|for)\s+(.+?)(?:\s+in|\s+for|$)', 'student_attendance'),
        (r'(\d+)(?:st|nd|rd|th)\s+sem(?:ester)?', 'semester'),
        (r'(?:section|sec)\s*[\'"]?\s*([A-Za-z])\s*[\'"]?', 'section'),
        (r'(?:marks?|score|result|grade)\s+(?:of|for)', 'marks_query'),
        (r'(?:internal|ia|assessment)\s+marks?', 'marks_query'),
        (r'(?:important|likely|expected|probable|suggested)\s+questions?\s+(?:for|in|of)', 'exam_questions'),
        (r'(?:suggest|generate|give)\s+(?:me\s+)?(?:some\s+)?(?:important\s+)?questions?', 'exam_questions'),
        (r'exam\s+(?:preparation|prep|questions?|tips?)', 'exam_questions'),
        (r'(?:notes?|materials?|study)\s+(?:for|in|of|available)', 'notes_query'),
        (r'(?:download|get)\s+notes?', 'notes_query'),
        (r'(?:cse|computer\s+science|it|ece|eee|mech)', 'department'),
    ]

    @staticmethod
    def classify(query: str) -> dict[str, Any]:
        """Classify the query and extract parameters."""
        query_lower = query.lower().strip()
        result: dict[str, Any] = {'intents': [], 'params': {}}

        for pattern, intent_name in IntentClassifier.DATA_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                if intent_name not in result['intents']:
                    result['intents'].append(intent_name)
                # Extract numeric params
                if intent_name == 'attendance_threshold':
                    result['params']['threshold'] = int(match.group(1))
                    result['params']['direction'] = 'below'
                elif intent_name == 'attendance_above':
                    result['params']['threshold'] = int(match.group(1))
                    result['params']['direction'] = 'above'
                elif intent_name == 'semester':
                    result['params']['semester'] = int(match.group(1))
                elif intent_name == 'section':
                    result['params']['section'] = match.group(1).upper()

        # Detect subject names from query
        result['params']['subject_hint'] = query_lower

        return result


# ─────────────────────────────────────────────
# Data Query Engine — live DB queries
# ─────────────────────────────────────────────

class DataQueryEngine:
    """Executes database queries based on classified intent."""

    @staticmethod
    def execute(intents: list[str], params: dict) -> str:
        """Run relevant queries and return formatted context string."""
        results = []

        if 'attendance_filter' in intents or 'attendance_threshold' in intents or 'attendance_above' in intents:
            data = DataQueryEngine.get_students_by_attendance(
                threshold=params.get('threshold', 75),
                direction=params.get('direction', 'below'),
                semester=params.get('semester'),
                section=params.get('section')
            )
            results.append(data)

        if 'student_attendance' in intents:
            data = DataQueryEngine.get_student_attendance_detail(params.get('subject_hint', ''))
            if data:
                results.append(data)

        if 'marks_query' in intents:
            data = DataQueryEngine.get_marks_summary(
                semester=params.get('semester'),
                section=params.get('section')
            )
            results.append(data)

        if 'exam_questions' in intents:
            data = DataQueryEngine.get_subject_syllabus_context(params.get('subject_hint', ''))
            results.append(data)

        if 'notes_query' in intents:
            data = DataQueryEngine.get_available_notes(params.get('subject_hint', ''))
            results.append(data)

        return "\n\n".join(results) if results else ""

    @staticmethod
    def get_students_by_attendance(threshold: int = 75, direction: str = 'below',
                                   semester: int | None = None, section: str | None = None) -> str:
        """Get students filtered by attendance percentage."""
        try:
            from models.user import User  # pyre-ignore[21]
            from models.attendance import Attendance  # pyre-ignore[21]
            from models.subject import Subject  # pyre-ignore[21]

            query = User.query.filter_by(role='STUDENT', is_active=True)
            if semester:
                query = query.filter_by(semester=semester)
            if section:
                query = query.filter_by(section=section)

            students = query.all()
            if not students:
                return f"=== ATTENDANCE DATA ===\nNo students found matching the criteria (semester={semester}, section={section})."

            results = []
            for s in students:
                records = Attendance.query.filter_by(student_id=s.id).all()
                total = len(records)
                if total == 0:
                    pct = 0.0
                else:
                    present = sum(1 for r in records if r.status in ('PRESENT', 'LATE'))
                    pct = round((present / total) * 100, 2)

                if (direction == 'below' and pct < threshold) or (direction == 'above' and pct >= threshold):
                    results.append({
                        'name': s.full_name,
                        'student_id': s.student_id,
                        'semester': s.semester,
                        'section': s.section or 'N/A',
                        'department': s.department or 'N/A',
                        'attendance_pct': pct,
                        'total_classes': total
                    })

            lines = [f"=== ATTENDANCE DATA (students {direction} {threshold}%) ==="]
            if semester:
                lines[0] += f" | Semester: {semester}"
            if section:
                lines[0] += f" | Section: {section}"

            if not results:
                lines.append(f"No students found with attendance {direction} {threshold}%.")
            else:
                lines.append(f"Found {len(results)} student(s):")
                for r in sorted(results, key=lambda x: x['attendance_pct']):
                    lines.append(f"  - {r['name']} (ID: {r['student_id']}) | Sem: {r['semester']} | Sec: {r['section']} | Attendance: {r['attendance_pct']}% ({r['total_classes']} classes)")

            return "\n".join(lines)
        except Exception as e:
            return f"=== ATTENDANCE DATA ===\nError querying attendance: {e}"

    @staticmethod
    def get_student_attendance_detail(hint: str) -> str:
        """Get detailed attendance for a specific student mentioned in the query."""
        try:
            from models.user import User  # pyre-ignore[21]
            from services.attendance_service import AttendanceService  # pyre-ignore[21]

            students = User.query.filter_by(role='STUDENT', is_active=True).all()
            matched = None
            for s in students:
                if s.full_name.lower() in hint or (s.student_id and s.student_id.lower() in hint):
                    matched = s
                    break

            if not matched:
                return ""

            stats = AttendanceService.get_attendance_stats(matched.id)
            subj_att = AttendanceService.get_subject_wise_attendance(matched.id)

            lines = [f"=== ATTENDANCE DETAIL FOR {matched.full_name} (ID: {matched.student_id}) ==="]
            lines.append(f"  Overall: {stats['percentage']}% | Present: {stats['present']} | Absent: {stats['absent']} | Late: {stats['late']} | Total: {stats['total']}")
            for sa in subj_att:
                lines.append(f"  {sa['subject_name']} ({sa['subject_code']}): {sa['percentage']}% ({sa['present']}+{sa['late']}/{sa['total']})")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def get_marks_summary(semester: int | None = None, section: str | None = None) -> str:
        """Get internal marks summary."""
        try:
            from models.internal_mark import InternalMark  # pyre-ignore[21]
            from models.user import User  # pyre-ignore[21]

            query = InternalMark.query
            if semester:
                query = query.filter_by(semester=semester)

            marks = query.all()
            if not marks:
                return "=== INTERNAL MARKS DATA ===\nNo internal marks data available."

            lines = ["=== INTERNAL MARKS DATA ==="]
            # Group by student
            student_marks: dict[int, list] = {}
            for m in marks:
                if section and m.student and m.student.section != section:
                    continue
                if m.student_id not in student_marks:
                    student_marks[m.student_id] = []
                student_marks[m.student_id].append(m)

            for sid, mark_list in student_marks.items():
                student = mark_list[0].student
                if student:
                    lines.append(f"  {student.full_name} (ID: {student.student_id}):")
                    for m in mark_list:
                        subj_name = m.subject.name if m.subject else 'Unknown'
                        lines.append(f"    {subj_name} - {m.exam_type}: {m.marks_obtained}/{m.max_marks}")

            return "\n".join(lines)
        except Exception as e:
            return f"=== INTERNAL MARKS DATA ===\nError: {e}"

    @staticmethod
    def get_subject_syllabus_context(hint: str) -> str:
        """Get subject details for exam question generation."""
        try:
            from models.subject import Subject  # pyre-ignore[21]

            subjects = Subject.query.filter_by(is_active=True).all()
            matched = []
            for s in subjects:
                if s.name.lower() in hint or s.code.lower() in hint:
                    matched.append(s)

            if not matched:
                matched = subjects  # Provide all if none matched

            lines = ["=== SUBJECT SYLLABUS FOR EXAM QUESTION GENERATION ==="]
            for s in matched:
                faculty_name = s.faculty.name if s.faculty else "TBA"
                lines.append(f"  [{s.code}] {s.name}")
                lines.append(f"    Description: {s.description or 'N/A'}")
                lines.append(f"    Credits: {s.credits} | Semester: {s.semester} | Faculty: {faculty_name}")
            lines.append("\nPlease generate important/likely exam questions based on the above syllabus information.")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def get_available_notes(hint: str) -> str:
        """Get list of available notes/study materials."""
        try:
            from models.note import Note  # pyre-ignore[21]

            notes = Note.query.filter_by(is_active=True).all()
            if not notes:
                return "=== AVAILABLE NOTES ===\nNo notes/study materials have been uploaded yet."

            lines = ["=== AVAILABLE NOTES ==="]
            for n in notes:
                subj_name = n.subject.name if n.subject else 'General'
                uploader = n.uploader.full_name if n.uploader else 'Unknown'
                size_mb = round(n.file_size / (1024*1024), 2) if n.file_size else 0
                lines.append(f"  - {n.title} | Subject: {subj_name} | By: {uploader} | Size: {size_mb}MB | Date: {n.uploaded_at.strftime('%Y-%m-%d') if n.uploaded_at else 'N/A'}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"


# ─────────────────────────────────────────────
# Context Builder — reads DB + documents
# ─────────────────────────────────────────────

class ContextBuilder:
    """Builds rich context from database records and training documents."""

    def __init__(self, training_folder: str):
        self.training_folder = training_folder
        self._doc_cache: list[dict[str, Any]] = []
        self._load_documents()

    def _load_documents(self):
        """Load all training documents into an in-memory list of chunks."""
        self._doc_cache = []

        # policies.txt
        policies_path = os.path.join(self.training_folder, 'policies.txt')
        if os.path.exists(policies_path):
            with open(policies_path, 'r', encoding='utf-8') as f:
                content = f.read()
            sections = [s.strip() for s in content.split('\n\n') if s.strip()]
            for section in sections:
                self._doc_cache.append({
                    'text': section,
                    'source': 'attendance_policy',
                    'keywords': self._extract_keywords(section)
                })

        # faqs.csv
        faqs_path = os.path.join(self.training_folder, 'faqs.csv')
        if os.path.exists(faqs_path):
            with open(faqs_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('question') and row.get('answer'):
                        text = f"Q: {row['question']}\nA: {row['answer']}"
                        self._doc_cache.append({
                            'text': text,
                            'source': f"faq_{row.get('category', 'general')}",
                            'keywords': self._extract_keywords(text)
                        })

        # subjects.csv
        subjects_path = os.path.join(self.training_folder, 'subjects.csv')
        if os.path.exists(subjects_path):
            with open(subjects_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    text = f"Subject {row.get('code','')}: {row.get('name','')} - {row.get('description','')}"
                    if row.get('faculty'):
                        text += f" Taught by {row['faculty']}."
                    self._doc_cache.append({
                        'text': text,
                        'source': 'subjects_csv',
                        'keywords': self._extract_keywords(text)
                    })

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        stopwords = {'the','a','an','is','in','of','to','and','or','for','with','as','by','at'}
        words = text.lower().replace('?','').replace(',','').split()
        return {w for w in words if len(w) > 3 and w not in stopwords}

    @staticmethod
    def _get_db_context() -> str:
        """Query the live database and build a context string."""
        try:
            from models.subject import Subject  # pyre-ignore[21]
            from models.faculty import Faculty  # pyre-ignore[21]
            from models.timetable import Timetable  # pyre-ignore[21]

            lines = []

            subjects = Subject.query.filter_by(is_active=True).all()
            if subjects:
                lines.append("=== SUBJECTS ===")
                for s in subjects:
                    faculty_name = s.faculty.name if s.faculty else "TBA"
                    lines.append(f"  [{s.code}] {s.name} | Credits: {s.credits} | Semester: {s.semester} | Faculty: {faculty_name}")
                lines.append("")

            faculties = Faculty.query.filter_by(is_active=True).all()
            if faculties:
                lines.append("=== FACULTY ===")
                for f in faculties:
                    lines.append(f"  {f.name} ({f.designation}) | Dept: {f.department} | Email: {f.email} | Office: {f.office} | Specialization: {f.specialization}")
                lines.append("")

            timetable = Timetable.query.filter_by(is_active=True).order_by(
                Timetable.day_of_week, Timetable.start_time
            ).all()
            if timetable:
                lines.append("=== TIMETABLE ===")
                for t in timetable:
                    subj_name = t.subject.name if t.subject else "Unknown"
                    start = t.start_time.strftime('%I:%M %p') if t.start_time else '?'
                    end   = t.end_time.strftime('%I:%M %p') if t.end_time else '?'
                    lines.append(f"  {t.day_of_week}: {subj_name} | {start}-{end} | Room: {t.room}")
                lines.append("")

            return "\n".join(lines) if lines else ""
        except Exception as e:
            print(f"[RAG] Error reading DB context: {e}")
            return ""

    def retrieve(self, query: str, top_k: int = 8) -> list[str]:
        """Return the most relevant document chunks for a given query."""
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            from itertools import islice
            return [c['text'] for c in islice(self._doc_cache, top_k)]

        scored = []
        for chunk in self._doc_cache:
            overlap = len(query_keywords & chunk['keywords'])
            if overlap > 0:
                scored.append((overlap, chunk['text']))

        scored.sort(key=lambda x: x[0], reverse=True)
        from itertools import islice
        return [text for _, text in islice(scored, top_k)]

    def build_system_prompt(self, query: str, user_id: int | None = None,
                            user_role: str | None = None) -> str:
        """Assemble system prompt: base + DB context + data query results + doc chunks."""
        parts = [SYSTEM_BASE_PROMPT, ""]

        # Live database context
        db_ctx = self._get_db_context()
        if db_ctx:
            parts.append("=== LIVE DATABASE INFORMATION ===")
            parts.append(db_ctx)

        # User context
        if user_id:
            user_ctx = self._get_user_context(user_id)
            if user_ctx:
                parts.append("=== CALLER (USER) INFORMATION ===")
                parts.append(user_ctx)
                parts.append("")

        # Data Query Engine — detect intent and run DB queries
        classification = IntentClassifier.classify(query)
        if classification['intents']:
            data_results = DataQueryEngine.execute(
                classification['intents'],
                classification['params']
            )
            if data_results:
                parts.append("=== DATA QUERY RESULTS ===")
                parts.append(data_results)
                parts.append("")

        # Retrieved document chunks
        relevant_chunks = self.retrieve(query)
        if relevant_chunks:
            parts.append("=== RELEVANT KNOWLEDGE BASE ===")
            for i, chunk in enumerate(relevant_chunks, 1):
                parts.append(f"[{i}] {chunk}")
            parts.append("")

        parts.append(f"Current date/time: {datetime.now().strftime('%A, %d %B %Y %I:%M %p')}")
        return "\n".join(parts)

    @staticmethod
    def _get_user_context(user_id: int) -> str:
        """Get the calling user's personal context and attendance if applicable."""
        try:
            from models.user import User  # pyre-ignore[21]
            user = User.query.get(user_id)
            if not user:
                return ""

            lines = [
                f"  Your Name (The User): {user.full_name}",
                f"  Your Role: {user.role}",
                f"  Your Email: {user.email}",
                f"  Your Username: {user.username}",
            ]
            if user.department:
                lines.append(f"  Your Department: {user.department}")

            if user.role == 'STUDENT' and user.student_id:
                lines.append(f"  Your Student ID: {user.student_id}")

            if user.role == 'STUDENT' and user.id:
                from services.attendance_service import AttendanceService  # pyre-ignore[21]
                stats = AttendanceService.get_attendance_stats(user.id)
                subj_attendance = AttendanceService.get_subject_wise_attendance(user.id)

                lines.append("  === YOUR ATTENDANCE ===")
                lines.append(f"    Overall: {stats['total']} classes | Present: {stats['present']} | Absent: {stats['absent']} | Late: {stats['late']} | Percentage: {stats['percentage']}%")

                for sa in subj_attendance:
                    lines.append(f"    {sa['subject_name']}: {sa['percentage']}% ({sa['present']}+{sa['late']} / {sa['total']})")

            return "\n".join(lines)
        except Exception as e:
            print(f"[RAG] Error reading user context: {e}")
            return ""


# ─────────────────────────────────────────────
# OpenRouter LLM Client
# ─────────────────────────────────────────────

class OpenRouterClient:
    """Calls the OpenRouter API to get an LLM response."""

    def __init__(self, api_key: str = OPENROUTER_API_KEY, model: str = OPENROUTER_MODEL):
        self.api_key = api_key
        self.model   = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:5000",
            "X-Title":       "Face Recognition Attendance System"
        }

    def ask(self, system_prompt: str, user_question: str) -> dict:
        """Send the RAG-enriched question to the LLM and return the parsed result."""
        payload = {
            "model":    self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_question}
            ],
            "temperature": 0.3,
            "max_tokens":  1024
        }

        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            answer = (
                data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
            )
            if not answer:
                answer = "I'm sorry, I couldn't generate a response. Please try again."

            return {
                "answer":     answer,
                "confidence": 1.0,
                "category":   "llm",
                "model":      data.get("model", self.model)
            }

        except requests.exceptions.Timeout:
            return {
                "answer":     "The AI service timed out. Please try again in a moment.",
                "confidence": 0.0,
                "category":   "error"
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            try:
                err_body = e.response.json()
                msg = err_body.get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            print(f"[RAG] OpenRouter HTTP {status}: {msg}")
            return {
                "answer":     f"AI service error ({status}): {msg}",
                "confidence": 0.0,
                "category":   "error"
            }
        except Exception as e:
            print(f"[RAG] Unexpected error calling OpenRouter: {e}")
            return {
                "answer":     "An unexpected error occurred. Please try again.",
                "confidence": 0.0,
                "category":   "error"
            }


# ─────────────────────────────────────────────
# RAG AI Service (public API)
# ─────────────────────────────────────────────

class AIService:
    """
    Public-facing AI service. Uses OpenRouter LLM + RAG over live DB + document files.
    """

    def __init__(self, training_folder: str, api_key: str = OPENROUTER_API_KEY):
        self.training_folder = training_folder
        self.is_trained      = True
        self._context_builder = ContextBuilder(training_folder)
        self._llm             = OpenRouterClient(api_key=api_key)
        print("RAG AI Service initialized (OpenRouter backend)")

    def ask(self, question: str, user_id: int | None = None,
            user_role: str | None = None) -> dict:
        """Ask a question. Returns {answer, confidence, category}."""
        system_prompt = self._context_builder.build_system_prompt(
            question, user_id, user_role
        )
        return self._llm.ask(system_prompt, question)

    def get_stats(self) -> dict:
        doc_count = len(self._context_builder._doc_cache)
        return {
            "is_trained":    True,
            "total_qa_pairs": doc_count,
            "model_name":    OPENROUTER_MODEL,
            "backend":       "OpenRouter RAG + Data Query Engine",
            "categories":    ["faculty", "subjects", "timetable", "policy", "attendance_data", "marks_data", "notes", "exam_questions"]
        }

    def train(self, data_folder: str) -> bool:
        """Re-load documents."""
        self._context_builder = ContextBuilder(data_folder)
        print(f"RAG documents reloaded ({len(self._context_builder._doc_cache)} chunks)")
        return True


# ─────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────

_ai_service: AIService | None = None


def get_ai_service(config=None) -> AIService | None:
    """Get or create the RAG AI service singleton."""
    global _ai_service

    if _ai_service is None and config:
        _ai_service = AIService(
            training_folder=config['AI_TRAINING_FOLDER'],
            api_key=OPENROUTER_API_KEY
        )

    return _ai_service
