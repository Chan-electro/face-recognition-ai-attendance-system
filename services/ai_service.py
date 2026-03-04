"""
RAG Agent powered by OpenRouter API (acree-ai/trinity-large-preview:free)

Architecture:
1. Context Builder  - reads live DB values + document files to build rich context
2. RAG Retriever    - keyword-matches the query to select the most relevant context chunks
3. OpenRouter LLM   - sends system prompt (context) + user question, streams the answer
"""

import os
import csv
import json
import requests
from datetime import datetime


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL   = "arcee-ai/trinity-large-preview:free"
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_BASE_PROMPT = """You are a helpful AI assistant for a college Face Recognition Attendance System.
You have access to the college's data including subjects, faculty, timetable, attendance policies, and FAQs.
Answer student questions clearly, concisely, and accurately using the context provided.
If the answer is not in the provided context, say so honestly and suggest where the student can find the information.
Respond in plain text without markdown formatting unless specifically asked."""


# ─────────────────────────────────────────────
# Context Builder — reads DB + documents
# ─────────────────────────────────────────────

class ContextBuilder:
    """Builds rich context from database records and training documents."""

    def __init__(self, training_folder: str):
        self.training_folder = training_folder
        self._doc_cache: list[dict] = []   # [{text, keywords, source}, ...]
        self._load_documents()

    # ── Document loading ──────────────────────

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

    # ── Database context ──────────────────────

    @staticmethod
    def _get_db_context() -> str:
        """Query the live database and build a context string."""
        try:
            from models.subject import Subject
            from models.faculty import Faculty
            from models.timetable import Timetable

            lines = []

            # Subjects
            subjects = Subject.query.filter_by(is_active=True).all()
            if subjects:
                lines.append("=== SUBJECTS ===")
                for s in subjects:
                    faculty_name = s.faculty.name if s.faculty else "TBA"
                    lines.append(f"  [{s.code}] {s.name} | Credits: {s.credits} | Semester: {s.semester} | Faculty: {faculty_name}")
                lines.append("")

            # Faculty
            faculties = Faculty.query.filter_by(is_active=True).all()
            if faculties:
                lines.append("=== FACULTY ===")
                for f in faculties:
                    lines.append(f"  {f.name} ({f.designation}) | Dept: {f.department} | Email: {f.email} | Office: {f.office} | Specialization: {f.specialization}")
                lines.append("")

            # Timetable
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

    # ── RAG retrieval ─────────────────────────

    def retrieve(self, query: str, top_k: int = 8) -> list[str]:
        """Return the most relevant document chunks for a given query."""
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            # Return first top_k chunks as fallback
            return [c['text'] for c in self._doc_cache[:top_k]]

        scored = []
        for chunk in self._doc_cache:
            overlap = len(query_keywords & chunk['keywords'])
            if overlap > 0:
                scored.append((overlap, chunk['text']))

        # Sort by overlap descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:top_k]]

    def build_system_prompt(self, query: str, student_id: int | None = None) -> str:
        """Assemble system prompt: base + DB context + retrieved doc chunks."""
        parts = [SYSTEM_BASE_PROMPT, ""]

        # Live database context (always included — it's always fresh)
        db_ctx = self._get_db_context()
        if db_ctx:
            parts.append("=== LIVE DATABASE INFORMATION ===")
            parts.append(db_ctx)

        # Student-specific attendance if logged in
        if student_id:
            student_ctx = self._get_student_context(student_id)
            if student_ctx:
                parts.append("=== THIS STUDENT'S ATTENDANCE ===")
                parts.append(student_ctx)
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
    def _get_student_context(student_id: int) -> str:
        """Get this student's attendance summary from DB."""
        try:
            from services.attendance_service import AttendanceService
            stats = AttendanceService.get_attendance_stats(student_id)
            subj_attendance = AttendanceService.get_subject_wise_attendance(student_id)

            lines = [
                f"  Overall: {stats['total']} classes | Present: {stats['present']} | Absent: {stats['absent']} | Late: {stats['late']} | Percentage: {stats['percentage']}%"
            ]
            for sa in subj_attendance:
                lines.append(
                    f"  {sa['subject_name']}: {sa['percentage']}% ({sa['present']}+{sa['late']} / {sa['total']})"
                )
            return "\n".join(lines)
        except Exception as e:
            print(f"[RAG] Error reading student context: {e}")
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
            "max_tokens":  512
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
                "confidence": 1.0,   # LLM doesn't return a confidence score
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
            # Try to extract OpenRouter error message
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
# RAG AI Service (public API, replaces old AIService)
# ─────────────────────────────────────────────

class AIService:
    """
    Public-facing AI service.  Drop-in replacement for the old sentence-transformers service.
    Uses OpenRouter LLM + RAG over live DB + document files.
    """

    def __init__(self, training_folder: str, api_key: str = OPENROUTER_API_KEY):
        self.training_folder = training_folder
        self.is_trained      = True   # Always ready — no local training needed
        self._context_builder = ContextBuilder(training_folder)
        self._llm             = OpenRouterClient(api_key=api_key)
        print("✓ RAG AI Service initialized (OpenRouter backend)")

    def ask(self, question: str, student_id: int | None = None) -> dict:
        """Ask a question. Returns {answer, confidence, category}."""
        system_prompt = self._context_builder.build_system_prompt(question, student_id)
        return self._llm.ask(system_prompt, question)

    def get_stats(self) -> dict:
        doc_count = len(self._context_builder._doc_cache)
        return {
            "is_trained":    True,
            "total_qa_pairs": doc_count,
            "model_name":    OPENROUTER_MODEL,
            "backend":       "OpenRouter RAG",
            "categories":    ["faculty", "subjects", "timetable", "policy", "system", "general"]
        }

    def train(self, data_folder: str) -> bool:
        """Re-load documents (documents are always fresh from DB at query time)."""
        self._context_builder = ContextBuilder(data_folder)
        print(f"✓ RAG documents reloaded ({len(self._context_builder._doc_cache)} chunks)")
        return True


# ─────────────────────────────────────────────
# Singleton accessor (same interface as before)
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
