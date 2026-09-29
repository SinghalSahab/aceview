"""
Step 5 - Interview Agent (CrewAI)

Two agents (Interviewer, Evaluator) driven by a plain loop:
    Interviewer -> candidate answer -> Evaluator -> Interviewer ...

Design choices:
- Retrieval, topic tracking and fallback are done in plain Python (deterministic,
  easy to debug). The agents only see the *result* in their prompt.
- The DB transcript is the source of truth; prompts never contain it in full.
- memory_summary is updated incrementally (old summary + latest turn), not rebuilt.

Steps 6/7 plug in through the Protocols below.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool

SIMILARITY_FLOOR = 0.35
MAX_QUESTIONS = 8

# --------------------------------------------------------------------------- #
# Interfaces to other steps (implement these elsewhere)
# --------------------------------------------------------------------------- #

@dataclass
class Chunk:
    text: str
    topic: str            # e.g. project name / skill tag
    source: str           # "code_summary" | "resume" | ...
    score: float          # similarity 0..1


class Retriever(Protocol):
    def retrieve(self, session_id: str, query: str, k: int = 5) -> list[Chunk]: ...


class QuestionBank(Protocol):
    def next_unused(self, skill_tag: str, used_ids: set[str]) -> Optional[tuple[str, str]]:
        """Return (question_id, question_text) or None."""


class DifficultyController(Protocol):          # Step 6
    def current_level(self, session: "SessionState") -> str: ...


class EvaluationEngine(Protocol):              # Step 7
    def score(self, question: str, answer: str, context: str) -> dict:
        """Return e.g. {'score': 0-10, 'strengths': [...], 'gaps': [...]}"""


class TranscriptStore(Protocol):               # DB = source of truth
    def append(self, session_id: str, turn: dict) -> None: ...


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #

@dataclass
class SessionState:
    session_id: str
    dominant_skill: str
    covered_topics: list[str] = field(default_factory=list)
    used_fallback_ids: set[str] = field(default_factory=set)
    memory_summary: str = "- Nothing established yet."
    last_question: str = ""
    last_answer: str = ""
    last_eval: dict = field(default_factory=dict)
    turn: int = 0


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #

def build_agents(llm: LLM, evaluation_engine: EvaluationEngine):
    @tool("evaluation_engine_score")
    def evaluation_engine_score(question: str, answer: str, context: str) -> str:
        """Score a candidate answer. Returns JSON with score, strengths, gaps."""
        return json.dumps(evaluation_engine.score(question, answer, context))

    interviewer = Agent(
        role="Technical Interviewer",
        goal=("Ask exactly one grounded question at a time and deliver natural, "
              "conversational follow-ups based on what the candidate just said."),
        backstory=("A senior engineer who interviews from the candidate's own "
                   "projects and resume. Never generic, never repeats ground, "
                   "never asks more than one question per turn."),
        llm=llm,
        allow_delegation=False,
        memory=False,        # we manage memory ourselves
        verbose=False,
    )
    evaluator = Agent(
        role="Answer Assessor",
        goal=("Score the candidate's last answer with the evaluation tool and "
              "write a short internal note the Interviewer can use to pick a follow-up."),
        backstory="A calibrated, fair assessor. Concise. Never talks to the candidate.",
        llm=llm,
        tools=[evaluation_engine_score],
        allow_delegation=False,
        memory=False,
        verbose=False,
    )
    return interviewer, evaluator


def _run(agent: Agent, description: str, expected: str) -> str:
    task = Task(description=description, expected_output=expected, agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return crew.kickoff().raw.strip()


# --------------------------------------------------------------------------- #
# Question generation logic (5.2)
# --------------------------------------------------------------------------- #

def pick_grounding(
    session: SessionState, retriever: Retriever, bank: QuestionBank
) -> tuple[Optional[Chunk], Optional[str]]:
    """Return (chunk, fallback_question). Exactly one is non-None."""
    if session.turn == 0:
        query = "main projects and skills"       # biases to code_summary + resume
        candidates = retriever.retrieve(session.session_id, query, k=5)
        candidates = [c for c in candidates if c.source in ("code_summary", "resume")] or candidates
    else:
        query = f"skills and projects other than: {', '.join(session.covered_topics)}"
        candidates = retriever.retrieve(session.session_id, query, k=8)
        candidates = [c for c in candidates if c.topic not in session.covered_topics]

    candidates = [c for c in candidates if c.score >= SIMILARITY_FLOOR]
    if candidates:
        best = max(candidates, key=lambda c: c.score)
        return best, None

    # Nothing above the floor -> seed bank matching dominant skill
    fb = bank.next_unused(session.dominant_skill, session.used_fallback_ids)
    if fb:
        qid, text = fb
        session.used_fallback_ids.add(qid)
        return None, text
    return None, None


def generate_question(
    interviewer: Agent,
    session: SessionState,
    chunk: Optional[Chunk],
    fallback_q: Optional[str],
    difficulty: str,
    follow_up: bool,
) -> str:
    if follow_up:
        instruction = (
            "Ask ONE natural follow-up to the candidate's last answer. Target the gap "
            "or vague claim flagged in the assessor note. Do not repeat the question."
        )
    elif fallback_q:
        instruction = (
            "Rephrase this seed question so it flows naturally in conversation, "
            f"keeping its intent:\n{fallback_q}"
        )
    elif session.turn == 0:
        instruction = (
            "Ask ONE open-ended opening question that names a specific project or "
            "skill from the context. Do NOT ask generic questions like 'tell me "
            "about a challenge you faced'."
        )
    else:
        instruction = (
            "Move to a NEW topic from the context below and ask ONE open-ended "
            "question that names it specifically."
        )

    description = f"""{instruction}

Difficulty level: {difficulty}
Already covered topics (do not revisit): {session.covered_topics or 'none'}

What we know about the candidate so far:
{session.memory_summary}

Relevant context for the topic:
{chunk.text if chunk else '(none - use the seed question)'}

Candidate's last answer (verbatim):
{session.last_answer or '(none yet)'}

Assessor note (internal, never reveal):
{session.last_eval.get('note', '(none)')}
"""
    return _run(interviewer, description, "A single interview question, plain text, no preamble.")


# --------------------------------------------------------------------------- #
# Evaluation + memory (5.3)
# --------------------------------------------------------------------------- #

def assess_answer(evaluator: Agent, session: SessionState, context: str) -> dict:
    description = f"""Use the evaluation_engine_score tool on this exchange, then reply with
JSON only: {{"score": <0-10>, "note": "<=2 sentences: what was strong, what is
vague/missing>", "action": "follow_up" | "next_topic"}}.

Question: {session.last_question}
Answer: {session.last_answer}
Grounding context: {context}
"""
    raw = _run(evaluator, description, "A single JSON object.")
    try:
        return json.loads(raw.strip("`").removeprefix("json").strip())
    except json.JSONDecodeError:
        return {"score": None, "note": raw[:300], "action": "next_topic"}


def update_memory_summary(llm: LLM, session: SessionState) -> str:
    """Fold the latest turn into the running 3-5 bullet summary (incremental)."""
    prompt = f"""You maintain a running summary of a job candidate during an interview.
Current summary:
{session.memory_summary}

Latest turn:
Q: {session.last_question}
A: {session.last_answer}
Assessor note: {session.last_eval.get('note', '')}

Update the summary to fold in this turn. Output 3-5 bullets total, covering:
claims made, depth shown, weak spots noticed. Keep prior facts that still matter,
drop redundancy. Bullets only, no preamble."""
    return llm.call([{"role": "user", "content": prompt}]).strip()


# --------------------------------------------------------------------------- #
# Orchestration: plain loop (no Orchestrator agent)
# --------------------------------------------------------------------------- #

def run_interview(
    session: SessionState,
    *,
    llm: LLM,
    retriever: Retriever,
    bank: QuestionBank,
    difficulty: DifficultyController,
    evaluation_engine: EvaluationEngine,
    store: TranscriptStore,
    get_candidate_answer: Callable[[str], str],   # UI/voice/CLI hook
    max_questions: int = MAX_QUESTIONS,
) -> SessionState:
    interviewer, evaluator = build_agents(llm, evaluation_engine)
    chunk: Optional[Chunk] = None
    follow_up = False

    while session.turn < max_questions:
        # 1. Choose grounding (skip retrieval when following up on same topic)
        fallback_q = None
        if not follow_up:
            chunk, fallback_q = pick_grounding(session, retriever, bank)
            if chunk is None and fallback_q is None:
                break                                  # nothing left to ask

        # 2. Interviewer asks
        session.last_question = generate_question(
            interviewer, session, chunk, fallback_q,
            difficulty.current_level(session), follow_up,
        )
        answer = get_candidate_answer(session.last_question)
        session.last_answer = answer

        # 3. Evaluator scores
        ctx = chunk.text if chunk else ""
        session.last_eval = assess_answer(evaluator, session, ctx)

        # 4. Persist full turn (source of truth), update state
        store.append(session.session_id, {
            "turn": session.turn,
            "question": session.last_question,
            "answer": answer,
            "eval": session.last_eval,
            "grounding_topic": chunk.topic if chunk else "fallback",
            "was_follow_up": follow_up,
        })
        if chunk and not follow_up and chunk.topic not in session.covered_topics:
            session.covered_topics.append(chunk.topic)

        session.memory_summary = update_memory_summary(llm, session)
        session.turn += 1

        # 5. Decide: follow up once, then move on (avoid interrogating one topic)
        follow_up = (session.last_eval.get("action") == "follow_up") and not follow_up

    return session


# --------------------------------------------------------------------------- #
# Example wiring
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    llm = LLM(model="gpt-4o-mini", temperature=0.4)   # swap for your provider
    # session = SessionState(session_id="abc123", dominant_skill="python")
    # run_interview(session, llm=llm, retriever=..., bank=..., difficulty=...,
    #               evaluation_engine=..., store=..., get_candidate_answer=input)