# AceView — Decisions & Rationale (v1.1)

This is the "why" document for the whole project. The PRD says **what** the product must do, the PM & Implementation Plan says **how** to build it, and this file explains **why each choice was made**, what else was considered, and which numbers are guesses that still need validating.

It complements `chunking-rationale.md` (which covers the chunking redesign in depth) rather than repeating it.

**Tags used throughout**

| Tag | Meaning |
|---|---|
| **[Built]** | Already implemented before v1.1 |
| **[New]** | Introduced in v1.1 |
| **[Assumption]** | A tunable guess. It is written down so you can test it, not because it is known to be right |

---

## 1. The project on one page

**What it is.** A mock-interview platform that reads a candidate's resume and GitHub, builds a knowledge base about them, and then interviews them by voice. The interview is planned, adaptive and grounded in their real work. Afterwards they get an explainable score report, an ATS score and a dashboard.

**Who it's for.** Software-engineering job seekers and students (primary); bootcamps and recruiters for pre-screening (later).

**What makes it different from "ask an LLM to interview me".**

1. **It knows the candidate's actual work.** Questions come from retrieved chunks of their resume, READMEs and code analysis, and every question cites the chunks it used.
2. **It checks resume claims against code evidence**, and asks about gaps openly rather than accusing.
3. **Control flow is code, not vibes.** Which question comes next, when to go deeper, when to move on, and when to raise difficulty are deterministic rules with explicit thresholds. The LLM writes questions and proposes scores; it never decides the route.
4. **Scores are explainable.** Every score decomposes into rubric, keyword, embedding and reasoning components, with a reconciliation rule for when the LLM disagrees with the cheaper signals.
5. **It is measured.** Retrieval recall, grounding rate, score agreement and latency are computed by scripts, not asserted.

**The one-sentence architecture.** Ingestion builds a typed, linked knowledge base in Postgres/pgvector; a hybrid retrieval service reads it through fixed recipes; a LangGraph state machine plans and runs the interview; a two-speed evaluation engine scores answers; a dashboard reports the result.

---

## 2. Guiding principles

These explain most individual decisions below.

| # | Principle | Consequence |
|---|---|---|
| P1 | **Deterministic where a rule will do, LLM only where language is needed.** | Planning, routing, difficulty, budgets and validation are plain code with tests. |
| P2 | **Every output must be traceable.** | Questions carry chunk ids; scores carry component breakdowns; decisions carry rule numbers. |
| P3 | **Ground before you generate.** | Retrieval happens before the LLM call, by recipe, and a validator rejects ungrounded questions. |
| P4 | **Fail soft, never loop.** | Empty retrieval, LLM errors and silence all have defined fallbacks; no topic can trap the interview. |
| P5 | **Measure early.** | A labeled retrieval set (Day 3) and labeled answers (Day 5) exist before the features that depend on them are trusted. |
| P6 | **Be fair to the candidate.** | Probes are open-ended; evidence heuristics are never presented as proof; honesty is rewarded by the claim rubric. |
| P7 | **One week means cut lines are decisions too.** | Scope cuts are listed in advance (section 8) so slipping doesn't mean improvising. |

---

## 3. Decision index

| ID | Decision | Status | Main alternative(s) rejected |
|---|---|---|---|
| D-01 | LangGraph state machine for the interview agent | New | CrewAI, Pydantic AI alone, plain Python loop, OpenAI Agents SDK |
| D-02 | Evaluator is deterministic code plus an LLM proposal, not an "agent" | New (refines v1.0) | A second LLM agent that judges answers |
| D-03 | PostgreSQL + pgvector as the single data store | Built | Chroma/other vector DB + separate relational DB |
| D-04 | LangGraph Postgres checkpointer instead of Redis | New | Redis session store |
| D-05 | bge-small-en-v1.5 embeddings (local, 384-dim) | Built | Hosted embedding APIs, larger local models |
| D-06 | Tokenizer-accurate chunk sizing with a hard ceiling | Built | Character/4 estimate |
| D-07 | Eight typed chunk kinds with cross-source links (`project_key`, `repo_id`, `detected_tech`) | Built | One generic chunk type |
| D-08 | Claims stored as their own chunks | Built | Hoping retrieval finds contradictions live |
| D-09 | Hybrid retrieval (dense + keyword + fusion + diversity) | New | Dense-only, LLM-driven tool retrieval |
| D-10 | Retrieval by fixed recipe per question intent | New | Letting the LLM choose tools/queries |
| D-11 | Session-scoped transcript chunks | New (fixes a collision) | Global transcript ids |
| D-12 | Interview blueprint computed before turn 1 | New | Improvising topics turn by turn |
| D-13 | Planned slots plus a separate flex pool | New | One shared turn counter |
| D-14 | Per-topic depth ladder (D0 to D3) with budgets | New | Fixed question count per topic; "ask until satisfied" |
| D-15 | Deterministic router with ordered rules | New | LLM decides whether to probe or move on |
| D-16 | Two-speed evaluation (fast path routes, slow path scores) | New | Single LLM judge in the loop |
| D-17 | Calibrated embedding scores | New | Raw cosine mapped to 0 to 100 |
| D-18 | Claim probes are open, never reveal evidence | New | Confrontational fact-checking |
| D-19 | Only repo-linked project claims compared with code | New | Checking every claim against GitHub |
| D-20 | Difficulty adapts on a rolling average with cooldown and a seniority cap | Refined | Adjust on every answer |
| D-21 | User settings (role, seniority, JD, length, focus, difficulty, fact-check) | New | One fixed interview format |
| D-22 | Question validator plus seed-bank fallback | New | Trusting model output |
| D-23 | Validate before speaking; no streaming of raw model output to TTS | New | Stream tokens straight to speech |
| D-24 | Browser Web Speech for MVP voice; LiveKit/Pipecat as upgrade | Kept | Real-time voice framework in week 1 |
| D-25 | Tracing plus an offline evaluation harness | New | Eyeballing transcripts |
| D-26 | Candidate scoping enforced by construction; untrusted text delimited | New | Per-query discipline only |

---

## 4. Architecture: what is used and why

```
Browser (settings, mic, speaker, dashboard)
        |
FastAPI  ----------------------------------------------------------------+
  |                                                                      |
Ingestion: resume parser, GitHub scraper/analyzer, chunker, embedder     |
  |                                                                      |
PostgreSQL + pgvector:  profiles, repos, rag_documents (vectors + FTS),  |
                        sessions, turns, evaluations, LangGraph checkpoints
  |                                                                      |
Retrieval service (hybrid search, structured fetches, context packets)   |
  |                                                                      |
LangGraph interview graph:                                               |
  blueprint -> plan -> retrieve -> generate -> deliver -> wait           |
  -> ingest -> fast_eval -> decide -> (loop | wrap_up -> report)         |
  |                              |                                       |
STT/TTS                    Evaluation: fast path (in loop),              |
                                       slow path (background)  ----------+
  |
Dashboard / report
```

### 4.1 Why LangGraph, and why not CrewAI (D-01, D-02)

**The shape of the problem.** An interview is a long-lived loop that pauses for a human on every turn, carries explicit state (what has been covered, how deep, which claims are open, current difficulty) and branches on thresholds after every answer. That is a state machine with cycles and interrupts.

**Why CrewAI fit poorly.**

- CrewAI's core abstraction is a *crew* of role-playing agents working through tasks to a result. The interview isn't a team solving a task; it's one conversational loop with a deterministic controller.
- The PRD's "Evaluator agent" shouldn't be an agent at all. The whole point of the evaluation engine is that scoring is reproducible and not left to an LLM's judgment. Wrapping rubric/keyword/embedding logic in an agent adds latency and non-determinism to the component meant to remove them.
- Multi-agent frameworks tend to add LLM round trips (reasoning loops, delegation). In a voice product every extra round trip is dead air.
- Framework-managed "memory" is a black box. The features that make the interview feel real (a claims ledger, depth per topic, contradiction detection) need **explicit, typed, inspectable state**.

**Why LangGraph fits.**

- Cycles, conditional edges and interrupts are first-class, so the loop above maps onto it directly.
- State is explicit and checkpointed, so a dropped connection resumes at the pending question (D-04).
- LLM calls are confined to specific nodes; routing is ordinary functions you can unit test.
- The graph is voice-agnostic: it can be run in text mode with scripted answers, which is how it gets tested.

**Alternatives.**

| Option | Verdict |
|---|---|
| Pydantic AI alone | Excellent for typed LLM calls, but agents are request-scoped, so you would hand-build session state and the loop. Reasonable as a lightweight alternative; used here only conceptually (typed structured output via Pydantic). |
| Plain Python loop + provider SDK | Honestly viable for a single-agent loop. LangGraph is chosen over it for resumable sessions, interrupts and a more defensible architecture story. |
| OpenAI Agents SDK | Clean handoffs, minimal scaffolding, but ties the design to one vendor and doesn't add much for a one-agent loop. |
| Microsoft Agent Framework | Enterprise/Azure-oriented; wrong weight class. |
| CrewAI | Keep in mind for a future multi-persona feature, not as the spine. |

**Caveat.** The framework comparisons available to me were mostly vendor and SEO-style blog posts, so use them for direction only. The case for LangGraph above rests on the shape of the problem, not on popularity claims. Before relying on any API names, check them against the installed versions (interrupt/resume in particular).

**Risk and mitigation.** LangGraph has more boilerplate and a learning curve. Keep routing and planning in plain functions with tests so the graph stays thin; build a three-node graph first; cut order is in the plan.

### 4.2 One database (D-03, D-04)

PostgreSQL holds profiles, repos, sessions, turns, evaluations, LangGraph checkpoints, vectors (pgvector) and keyword search (full-text). One service to run, one backup, one place to join structured and semantic data. Candidate-scoped data is small (hundreds of chunks), so there is no scale argument for a separate vector database. The LangGraph Postgres checkpointer replaces Redis for session state, which also makes sessions resumable.

### 4.3 Embeddings (D-05)

bge-small-en-v1.5 runs locally (no per-call cost, no network latency, no data leaving the machine) and produces 384-dim vectors, which are small and fast to search. Its max sequence length is 512 tokens; chunks are capped at 480. Hosted or larger models could retrieve slightly better, but the retrieval evaluation set (Step 5.9) is how you would find that out; don't switch without it.

---

## 5. Step-by-step rationale

### 5.1 Resume ingestion **[Built]**

**What.** PDF text extraction (PyMuPDF), header-keyword section splitting, spaCy EntityRuler skill matching against a normalized skills list, and years-of-experience extraction (explicit phrases first, summed date ranges as fallback).

**Why these choices.**

- *Rule-based skill matching against a curated list* gives exact, explainable results and is the same matcher later reused for `detected_tech`, JD terms and keyword coverage. One matcher means one vocabulary across the system.
- *Header-keyword section splitting* is crude but dependable for typical resumes, and failures are visible (empty sections), which the pipeline treats as parse failures instead of guessing.
- *Years of experience* matters now beyond parsing: it infers the default seniority (below 1 year student/intern; 1 to under 3 junior; 3 to under 6 mid; 6+ senior), which sets the question mix and difficulty cap. **[Assumption]** those cut-offs are conventional, and the user can override them.

**Known limitation.** Scanned (image-only) PDFs and heavily designed layouts will parse poorly. The ATS score reports this as a formatting issue, which is correct from an ATS point of view.

### 5.2 GitHub scraping and code analysis **[Built]**

**What.** Public repos via the REST API; top N = 5 chosen by recency 40%, stars/forks 20% and real source beyond a README 40%; shallow clones analyzed within a 300 file / 20,000 line budget; five sub-scores plus an overall score (architecture, testing, complexity, documentation, commits).

**Why.**

- *Beyond READMEs* is the product promise: READMEs describe intent, code and history show practice.
- *Simple, explainable heuristics* (folder structure, test-file ratio, cyclomatic complexity, docstring density, commit cadence) are deliberately not "AI judgments". They give stable numbers that a human can sanity-check and that the claim checker can compare against.
- *Capped budgets* protect against rate limits and slow clones (the original risk register items).

**How the scores are used downstream.** They become `code_summary` chunk metadata and drive: project ranking (evidence depth), claim-versus-evidence checks (testing and architecture scores) and the dashboard's Code Quality dimension.

**Limitations worth knowing.** Public repos are a partial view: a candidate's best work may be private or at an employer. This is exactly why claim checks are heuristics that prompt *questions* rather than verdicts (D-18, D-19).

### 5.3 Chunking and indexing **[Built] + [New] amendments**

The full rationale is in `chunking-rationale.md`. In one paragraph: the system must be able to put a resume claim and the matching GitHub evidence side by side, which requires chunks that are correctly sized, typed, and linked.

**Key decisions already made.**

| Decision | Reason |
|---|---|
| **D-06** Use the embedding model's real tokenizer, with a hard 480-token ceiling | The old chars/4 guess could be 20 to 30% off on code-heavy text, and anything over the model limit is silently truncated. Truncated chunks lose the useful back half of a README section with no error. |
| **D-07** Eight chunk types, `project_key`, `repo_id`, `detected_tech` | Lets retrieval fetch "everything about this project" or "everything mentioning Redis" exactly, instead of hoping vectors happen to be close. |
| **D-08** Claims as separate chunks | The headline feature (resume says X, code shows Y) needs the claim sentence as a standalone, labeled unit. It also reduces the chance the interviewer misremembers something, because it points at a concrete sentence. |
| Skills grouped by taxonomy category | Groups of 15 random skills mean nothing as a unit; a category chunk is coherent. |
| Resume cut by job/degree first | Prevents chunks that end mid-job and start the next one. |
| README cleaning and a no-heading fallback | Badges, tables of contents and license text add tokens but no meaning; heading-less READMEs would otherwise be one oversized chunk. |
| Tombstoning (`deleted_at`) | Removed repos and resume sections stop surfacing in search. |
| Three focused `code_summary` chunks per repo | A testing-focused question matches a testing-only chunk strongly instead of one blended paragraph. |

**v1.1 amendments and why (D-11 and related).**

1. **Session-scoped transcript ids.** The reference guide's id (`{candidate}-turn-{n}`) collides with the `(user_id, chunk_id)` uniqueness constraint the second time a candidate interviews, and callbacks would pull answers from old sessions. Adding `session_id` to the id and metadata fixes both.
2. **`source_chunk_id` and `entry_index` on claims.** Lets an experience claim be linked to its job without fragile text matching.
3. **`section_order` on README chunks.** Document order for deep dives.
4. **`normalize_tech()` shared with the tagger.** Queries and tags must use the same aliases (postgres and postgresql).
5. **Indexes** (keyword `tsvector` with the `simple` config, GIN on metadata, expression indexes on `project_key` and `session_id`). The `simple` text-search config is used on purpose: it doesn't stem, so identifiers like `redis` and `kubernetes` stay intact.

**Filtered vector search at small scale.** Approximate (HNSW) indexes apply selective filters *after* the approximate scan and can return fewer than k rows. With only hundreds of chunks per candidate, an exact filtered scan is fast and correct, so either use pgvector's iterative index scan (in recent releases) or let the planner choose an exact scan. **[Assumption]** your installed pgvector version supports iterative scans; verify with `EXPLAIN ANALYZE`.

### 5.4 Retrieval (fetching) **[New]**

**What.** One `InterviewRetrievalService`, constructed per candidate, offering structured fetches (project deep-dive, claims, catalogs, listed-only skills), tech-filtered search, hybrid search, callbacks and a context-packet builder that applies a recipe per question intent.

**Why hybrid (D-09).**

- Dense vectors capture topical similarity ("caching") but are unreliable for exact identifiers (Redis, OpenTelemetry, Celery). Keyword search is the opposite. Fusing the two with reciprocal rank fusion (constant 60) gets both without having to calibrate their score scales against each other, which is the main reason RRF is used instead of a weighted score sum.
- A keyword match is treated as evidence on its own, so dense-only hits below the 0.35 similarity floor are dropped but keyword hits are kept.
- **Diversity (MMR, lambda 0.7)** stops a project chunk and its near-duplicate claim chunk from filling all result slots.
- A **cross-encoder reranker** is a stretch option. It adds latency; enable it only if the retrieval evaluation shows a gain.

**Why fixed recipes, not LLM tool-calls (D-10).**

- Deterministic: the same intent always fetches the same shape of evidence.
- Faster: no extra LLM round trip to decide what to search.
- Safer: grounding is guaranteed by construction, not by the model remembering to call a tool.
- Testable: each recipe is a function with expected outputs.

**The context packet.** A size-bounded bundle (about 900 tokens: primary up to ~500, evidence up to ~250, callback up to ~150) with chunk ids. Bounded because prompt size drives latency and cost; chunk ids because grounding must be auditable.

**Exclusion of used chunks.** Prevents two different questions resting on the same evidence, which is a major cause of repetitive interviews.

**The fallback ladder.** recipe → relaxed filters → role-level topic → seed bank. Every rung is logged. A slot that can only be served at the bottom rungs is *skipped* ("no evidence") rather than asked generically on the candidate's behalf, because a generic question about a project the system knows nothing about is worse than no question.

**Corrections to the reference guide** (they matter, they would have caused bugs):

| Issue | Why it's a bug |
|---|---|
| `.having()` with no `GROUP BY` for the similarity floor | Invalid in PostgreSQL; must be a `WHERE` condition. |
| Transcript ids/filters without a session | Collisions and cross-session leakage. |
| JSONB `?` operator | Placeholder clashes and weaker index use; containment (`@>`) is safer. |
| `get_unverified_claims` with constant similarity 1.0 and no ranking | No way to prefer important claims or skip already-probed ones. |
| Tech filter + vectors called "hybrid" | No keyword channel. |
| Unbounded, unordered README sections in deep dives | Blows the prompt budget and loses document order. |

**Prefetch.** The next planned slot is known from the blueprint, so its context packet can be built while the candidate is still answering. If the router decides to probe or deepen instead, the prefetched packet is discarded. This hides retrieval latency in the common "advance" case.

**Assumption to validate.** Whether the BGE query-instruction prefix helps short queries here. It is a config flag defaulting to off; decide by running the retrieval evaluation both ways.

**How we'll know it works.** Recall@4 and MRR on about 15 hand-labeled queries per test candidate, compared across dense-only, hybrid and hybrid+MMR. That comparison is the evidence for D-09.

### 5.5 Settings, role profiles and the blueprint **[New]**

**Why a blueprint at all (D-12).** Without a plan, an LLM interviewer drifts: it over-asks about whatever the first answer mentioned, forgets half the resume, and cannot say how much time anything deserves. Computing the plan once, deterministically, answers "what do we cover and how much" up front, and every later decision is a small deviation from a known plan.

**User settings (D-21).** Role, seniority, optional JD, length, focus, starting difficulty, fact-check intensity. They exist because "a good interview" depends on what the candidate is preparing for: a student shouldn't be grilled on distributed-systems failure modes and a senior shouldn't spend half an interview on basics. Each setting changes something concrete: question mix, difficulty cap, ranking weights, number of claim probes.

**Role profiles.** A JSON file per role (core technologies, fundamentals topics with seed terms, behavioral competencies, rubric weights). This keeps role knowledge in data, not code, and is the seam where future interviewer personalities plug in.

**JD handling.** JD terms are extracted with the same matcher as resume skills and weighted 2x against role defaults in relevance. A JD term the candidate lacks becomes a **gap question** that asks how experience with an *adjacent* skill (same taxonomy category) transfers. This is fairer and more informative than "do you know Kafka?".

**Turn accounting (D-13).**

`T` = total answers. Reserve 1 opener and 1 closing. Core `C = T - 2`. Flex pool `P = max(1, round(0.2 x C))`. Planned slots `S = C - P`.

| Length | T | Planned S | Pool P |
|---|---|---|---|
| Short | 10 | 6 | 2 |
| Standard | 15 | 10 | 3 |
| Long | 20 | 14 | 4 |

*Why separate planned slots from a pool:* probes, contradictions and extra depth are unpredictable. If they came from the same counter as planned topics, a chatty first topic would starve later ones. With a separate pool, **coverage is guaranteed by construction** and depth is a bonus. Turns a topic doesn't use flow into the pool, so interviews don't end short. **[Assumption]** 20% is a reasonable pool share; tune from transcripts.

**Bucket mix by seniority.**

| Seniority | Projects | Experience | Fundamentals | Behavioral |
|---|---|---|---|---|
| student_intern | 55% | 5% | 25% | 15% |
| junior | 50% | 15% | 20% | 15% |
| mid | 40% | 25% | 20% | 15% |
| senior | 30% | 30% | 20% | 20% |

*Why:* students and juniors are judged mostly on projects and fundamentals because they have little work history; seniors are judged on scope, trade-offs and leadership. A focus setting shifts about 15 points. Largest-remainder rounding keeps integers summing to `S`. Empty buckets (no repos, no job history) redistribute rather than leaving dead slots. **[Assumption]** all percentages; they are starting points to review against dry-run output.

**Ranking projects and jobs.** Project priority = 0.35 role relevance + 0.25 evidence depth + 0.20 recency + 0.20 claim richness. Experience priority = 0.40 recency + 0.40 role relevance + 0.20 claim richness.

*Why these inputs:* an interviewer asks most about work that is relevant to the role, shows real substance, is recent, and contains checkable claims. Resume-only projects (no repo) get evidence depth 0.3 because there is little to ask beyond the description. **[Assumption]** weights; review on the 3 test candidates before trusting.

**Budgets: how much to go into one project or job.**

| Slot | Budget | Ladder |
|---|---|---|
| Top project | 3 | walkthrough, decision, (claim probe or code-quality probe or trade-off) |
| Second project | 2 | walkthrough, decision |
| Other projects | 1 | walkthrough |
| Most recent job | 2 | walkthrough, depth |
| Older jobs | 1 | walkthrough |

*Why:* real interviewers spend disproportionate time on the one or two things that matter most. Budgets make that explicit and bounded. A D3 ("what breaks at 10x") rung exists but is reachable only by earning a stretch, because it is most useful with a candidate who has already shown command of the basics.

**Fundamentals selection.** Prefer **listed-only skills**: skills on the resume that appear in no project, README, code or claim chunk. They are the likeliest to be shallow, so they are the best targets for a depth check. Then other role-relevant skills. At most one JD-gap slot.

**Claim ledger (D-08, D-18, D-19).** See 5.9.

### 5.6 The LangGraph agent **[New]**

**Nodes.** `init_session`, `build_blueprint`, `plan_turn`, `retrieve_context`, `generate_question`, `deliver_question`, `wait_for_answer`, `ingest_answer`, `fast_eval`, `decide`, `wrap_up`, `finalize_report`.

**Why `deliver_question` and `wait_for_answer` are separate.** When a LangGraph thread resumes after an interrupt, the interrupted node re-runs from its start. Side effects placed before the interrupt (saving the turn, sending text to TTS) would therefore run twice. Keeping the interrupt node minimal and making delivery idempotent (an upsert keyed by session and turn) avoids duplicate turns and double speech.

**Why `decide` and `plan_turn` are separate.** `decide` interprets the answer (signals to decision, difficulty, tone, budgets). `plan_turn` converts a decision into the next concrete turn plan. Keeping them apart means the decision rules can be tested without any retrieval.

**Why the slow path runs outside the graph's critical path.** Fan-out branches in a graph must finish before the next step, so a slow rubric call as a parallel branch would still block the loop. It runs as a background task writing to the database; `decide` reads finished results at the start of each decision. The cost is a one-turn lag in using final scores for difficulty, which the rolling-average design tolerates (it falls back to the fast score). Because background tasks die with the process, `wrap_up` recomputes any missing evaluation; slow-path work is idempotent by session and turn.

**LLM call inventory.** One strong-tier call (question generation) and one fast-tier call (contradiction check, parallel with local scoring) on the critical path. Rubric scoring, the reasoning check and memory updates are off the critical path; claim resolution happens once at the end. This is the main lever for the latency target.

**Persistence.** Postgres checkpointer with `thread_id = session_id`; separate `interview_turns` and `answer_evaluations` tables hold the facts the dashboard needs, so the report never depends on parsing checkpoints.

**Text-mode harness.** The graph must run with scripted answers and no audio. That is what makes planning, routing and question quality reviewable, and it decouples the riskiest integration (voice) from the core logic.

### 5.7 Question generation **[New]**

**Core idea.** Questions come from a pipeline, not a prompt: *plan → retrieve → generate → validate → store*. The LLM contributes wording and key points; everything that determines *what* to ask is decided before it is called.

**Why intents (D-10).** Each question has an intent (opener, project walkthrough, decision, claim probe, code-quality probe, trade-off, experience, tech depth, JD gap, behavioral, follow-up, callback, revisit, closing). The intent selects the retrieval recipe, the rubric and the phrasing guidance. This makes questions consistent and testable, and it is how the system "asks about the right thing for the situation".

**Why difficulty and depth are separate axes.**

- *Depth* (ladder step D0 to D3): how far into the topic. Walkthrough, decision, trade-off/claim, failure/scale.
- *Difficulty* (level 1 to 5): how demanding the question is. What/why, how, trade-offs, scale and failure modes, redesign under changed requirements.

A strong answer typically raises both, but they are independent: a D1 "why this choice" question at level 4 asks for a reasoned decision under tight constraints; at level 2 it asks for one simple reason. Keeping them separate avoids one knob doing two jobs.

**Why structured output with chunk ids.** The Question object carries `grounding_chunk_ids` and `expected_key_points`. The first makes grounding auditable (and measurable as a success metric); the second feeds the evaluation engine so scoring is tied to what this specific question was meant to elicit.

**Why a deterministic validator (D-22).** Language models occasionally invent a technology, run long, repeat an earlier question or give away the analysis. The validator checks: schema and echoed plan, at most 50 words and at most 2 question marks, no markdown/URLs/code, cited chunk ids are a subset of the retrieved ones, at least one entity from the cited chunks appears in the text, claim probes contain a distinctive token of the claim, no forbidden phrases ("analysis", "flagged", "lied"), similarity to every earlier question below 0.85, and key points are well-formed and grounded. One regeneration with the failure reasons, then the seed bank. **[Assumption]** the 50-word limit and the 0.85 similarity threshold.

**Why validate before speaking, and no streaming of raw model output (D-23).** In a voice product you cannot un-say a sentence. Streaming tokens straight to TTS would let an ungrounded or revealing question be spoken before validation could reject it. Instead, latency is managed by a fast model for the parallel classifier, prefetching, small context packets and sentence-by-sentence TTS synthesis of the *validated* text. **Revisit** this only if the latency target is missed; the likely next step would be validating the `text` field as soon as it completes.

**Why key points are generated with the question, and how that is kept honest.** An ideal answer is needed to measure coverage. The LLM drafts 4 to 6 key points (each with 1 to 3 match terms) from retrieved facts, the role profile's fundamentals terms, and intent rubric hints. They are model-generated, so they are not ground truth; the validator requires at least two to contain terms found in the cited chunks, and the evaluation reconciliation rule limits the influence of any single signal.

**Why claim probes are phrased the way they are (D-18).** See 5.9.

**Why follow-ups target missing key points.** "Can you elaborate?" feels generic and invites rambling. The fast path already knows which key points were not matched, so the follow-up asks for exactly those. This also bounds the follow-up (at most about 35 words).

**Why one callback every three turns at most.** Callbacks make the interview feel attentive, but a callback on every turn feels scripted. The 0.50 similarity floor is higher than for normal retrieval because a wrong callback ("earlier you mentioned...") is more jarring than none.

**Supportive tone.** In struggle mode the question gets a short acknowledging lead-in, a narrower scope and one anchor from the candidate's own earlier words. Substance still follows the (already lowered) difficulty level: support is about delivery, not dropping standards silently.

### 5.8 Depth versus breadth: when to double down, when to move on **[New]**

This is the "how much to go into a particular project or job, and when to change topic" policy.

**Design goal.** Behave like a good human interviewer: spend more time on what matters and where the candidate is strong, don't interrogate where they clearly don't know, never abandon whole areas, and never loop.

**The mechanism in four layers.**

1. **Budgets decide *how much* time a topic may get** (5.5): rank 1 project 3 turns, rank 2 two, others one; most recent job two, others one.
2. **A ladder decides *what the next question on the topic is*:** walkthrough, decision, trade-off/claim, failure/scale.
3. **Signals decide whether to use the next rung:** after each answer, `fast_eval` produces keyword coverage, calibrated embedding similarity, a don't-know flag, a contradiction flag, a too-short flag and a clarification-request flag.
4. **Ordered rules turn signals into a decision:** probe, deepen, advance, repeat, rephrase or wrap up. First match wins:

| # | Condition | Decision |
|---|---|---|
| 0a | Too short / low STT confidence (not yet re-asked) | repeat (no budget used) |
| 0b | Candidate asks for clarification (not yet rephrased) | rephrase (no budget used) |
| 1 | Turn budget reached | closing, then wrap up |
| 2 | "I don't know" | advance; record gap; no probe |
| 3 | Contradiction (probes on this question under 2) | probe (pool) |
| 4 | Shallow (keyword under 40 or embedding under 30), no probe yet, pool available | probe once (pool) |
| 5 | Shallow, no probe available | advance; record gap |
| 6 | Weak (fast score under 45) | advance; don't dig |
| 7 | Answer repeats the previous one (similarity over 0.85) | advance |
| 8 | Solid (fast 65 or more), next rung exists within budget | deepen |
| 9 | Solid, budget spent, rank 1 or 2, no stretch used, pool available | deepen (stretch, uses pool) |
| 10 | Moderate (45 to under 65), rank 1, next rung exists | deepen |
| 11 | Otherwise | advance |

**Why this order.**

- Re-asks and clarifications come first because they're not about answer quality at all.
- "I don't know" ends the topic immediately: pushing on admitted ignorance is exactly what makes AI interviewers feel hostile.
- Contradictions beat shallowness because they are the most informative event in an interview.
- Probing is limited to **once** (twice for contradictions) because repeated probing on the same point is the main way interviews turn into interrogations.
- Weak answers advance rather than deepen: don't dig deeper into what the candidate can't explain; record the gap for the report instead.
- Only **rank 1 or 2** topics earn deepening on a merely moderate answer or a stretch, because those are the topics the plan says matter most.

**Struggle handling.** Two consecutive weak answers (a don't-know counts as weak) set supportive tone, lower difficulty by one immediately (bypassing the cooldown), and move to the pending slot with the strongest evidence. Weak-topic revisits are disabled while struggling. This implements the user story "stay supportive if I'm struggling" and prevents piling onto weak areas. It exits after one solid answer.

**Spending leftover pool turns.** When all planned slots are done: (1) probe the top unprobed claim; (2) revisit the weakest topic (average under 45, not in struggle mode) from a different angle using unused chunks; (3) stretch the strongest rank-1 or rank-2 topic; (4) otherwise end early rather than pad with generic questions.

**Scheduling between topics.** Buckets are interleaved (largest remaining allocation first, projects first on ties) and, within a bucket, the highest-ranked pending slot is next. This avoids long runs of one kind of question and puts the strongest project early.

**Thresholds are provisional [Assumption].** 65 (solid), 45 (weak), 40/30 (shallow), 80/45 (difficulty), 0.85 (repetition) are starting values. They are tuned against the scripted strong/weak fixtures and calibrated embedding scores (5.13); the table-driven tests (Step 9.8) lock the intended behavior.

**Worked example.** The 15-turn example in the PM plan (Step 9.7) shows every rule firing: a deepen, a difficulty rise with cooldown, a claim probe, a clarifying probe, a don't-know advance, a callback, a contradiction probe and a final stretch.

### 5.9 Claims: using resume-versus-code evidence in questions **[New use of a Built feature]**

**The idea.** "Built a scalable microservices architecture" versus a repo that is one Node file is exactly what a sharp reviewer would notice. The system stores each checkable sentence as a claim chunk (D-08) and builds a **claim ledger** at interview start.

**Evidence status (heuristics, deterministic).**

| Claim kind | Check | Result |
|---|---|---|
| No linked repo (employer work) | None possible | unverifiable |
| Testing/coverage claim, repo linked | `testing_score` under 40 unsupported; 60 or more supported | else unverifiable |
| Architecture assertion, repo linked | `architecture_score` under 50 | unsupported (weak) |
| Claims a technology absent from the repo's chunks | Tag union check | unsupported (weak) |
| Metric (percentages, latencies) | Numbers can't be verified from code | unverifiable |
| Leadership | Not checkable from GitHub | unverifiable |

**Why only repo-linked project claims are compared (D-19).** A claim about latency at a past employer cannot be checked from a candidate's public GitHub. Treating "no evidence" as "false" there would be unfair and wrong. Such claims are used for *depth* ("how did you measure that?") instead.

**Why absence of evidence is not proof (P6).** A public repo may be a fraction of the real work; a monorepo or private fork changes everything. So statuses are labeled heuristics, the report uses "worth discussing", and no question ever states the evidence.

**Priority.** `impact x gap multiplier x (0.5 + 0.5 x role relevance)`, with impact metric 1.0, architecture 0.9, leadership 0.6, other 0.3, and gap multiplier unsupported 1.5, unverifiable 1.2, supported 0.8. The top N (fact-check setting 1, 2 or 3) become probes; the rest stay available for leftover pool turns. **[Assumption]** all weights.

**Why probes replace the D2 rung (rather than adding turns).** A claim probe *is* a depth question, and a more informative one than a generic trade-off question because it tests a specific assertion. Replacing D2 keeps budgets honest.

**Why probes are open (D-18).** "How did you measure that, and which parts did it cover?" lets an honest candidate shine and a bluffing candidate reveal themselves, without a confrontation that destroys the practice value of a mock interview. The **claim-defense rubric** rewards specificity, method, honesty about limits and clarity; saying "it was approximate" is not penalized.

**Resolution after the interview.** For each probed claim a fast-tier model returns consistent, contradicted or unresolved (don't-know answers resolve to unresolved with no model call). The result goes into the report and onto the claim chunk's metadata. Only the report ever shows the comparison.

### 5.10 Difficulty adaptation **[Refined]**

**Levels.** 1 warm-up, 2 standard, 3 solid mid-level, 4 advanced, 5 expert/edge-case.

**Rule.** After each scored answer from the second non-opener answer onward, take the average of the last two scores (final score if the slow path has finished, else fast score). 80 or more raises difficulty by one; 45 or less lowers it by one.

**Why a two-answer rolling average.** A single answer is noisy (a lucky or unlucky topic). Two is responsive enough for a 10 to 20 turn interview.

**Why a one-turn cooldown.** Overlapping windows mean one great answer after another could raise difficulty every turn. The cooldown spaces changes out. Struggle handling is the exception because a struggling candidate should not wait.

**Why exclude the opener.** The opener is deliberately easy; including it would bias the first adjustment upward.

**Why a seniority cap (level 4 for students/interns).** Level 5 (redesign under changed requirements) is unfair for someone with a few months of experience, and producing nothing but unanswerable questions teaches the candidate nothing.

### 5.11 Memory **[New design for a Built concept]**

Three mechanisms, each with a different job:

| Mechanism | Holds | Used for |
|---|---|---|
| Rolling memory summary (3 to 5 bullets, about 120 words) | What the candidate has established: claims they made, depth per topic, weak spots, contradictions | Every question prompt and the contradiction check |
| Transcript chunks (session-scoped, in the vector store) | Each Q and A pair | Callbacks to specific earlier answers |
| `interview_turns` table | The full transcript, signals and decisions | The dashboard and audit |

The full transcript is never pasted into a prompt, which keeps prompts small and fast. The summary is updated incrementally in the slow path (previous summary plus latest turn), so it lags by up to one turn; prompts therefore also include the last answer verbatim.

**Contradiction check inputs.** The new answer, the memory summary, and the resume claims for the current project. Checking against the resume as well as earlier answers catches "led 8 engineers" versus "mentored 4".

### 5.12 Voice **[Kept]**

**MVP.** Browser Web Speech API in both directions (fast to integrate, free, good enough to demo), with Whisper/TTS APIs as an upgrade if time remains. A text input fallback is required for accessibility and microphone failures.

**Why not LiveKit/Pipecat in week 1.** They would give barge-in, turn detection and WebRTC transport and are the natural upgrade, but they add infrastructure and integration time to the riskiest part of the schedule. Because the graph is voice-agnostic, adopting one later wraps the same graph without changes.

**Silence detection (about 1.5 s) and a visible processing state** are cheap ways to make the interview feel responsive. Barge-in is explicitly out of the MVP.

**STT confidence.** Web Speech reports confidence; Whisper does not, so the router also uses a too-short rule (under 3 words). A garbled transcript triggers a free re-ask rather than a score on nonsense.

### 5.13 Evaluation engine **[Built design, [New] refinements]**

**Why not an LLM judge alone (D-02).** LLM scores vary run to run and cannot be explained beyond their own justification. The engine combines independent signals so a score is traceable and a single noisy signal can't dominate.

**Signals and weights.**

`final = 0.35 x rubric + 0.20 x keyword + 0.25 x embedding + 0.20 x reasoning`

| Signal | What it is | Why it's included |
|---|---|---|
| Rubric | Strong-tier LLM scores each criterion with a justification | Captures correctness and depth, which cheap signals can't |
| Keyword | Share of key points with any match term present | Cheap, deterministic, sensitive to exact terminology |
| Embedding | Per-key-point best sentence similarity, calibrated | Catches paraphrase that keywords miss |
| Reasoning | STAR for behavioral; cause-effect and trade-off language for technical | Rewards structure, not just content |

**Why per-key-point matching** (instead of comparing the whole answer to a concatenated ideal answer): coverage is the goal, and averaging the best match per key point rewards covering many points and doesn't let one verbose paragraph score high by matching a single point well. A key point counts as covered when *any* of its match terms appears, which tolerates paraphrase better than counting every individual term.

**Two paths (D-16).**

- **Fast path** (keyword, embedding, don't-know, contradiction) runs in the loop in well under a second and drives routing: `fast_score = 0.4 x keyword + 0.6 x embedding`, capped at 20 on don't-know.
- **Slow path** (rubric, reasoning, reconciliation, memory update) runs in the background and feeds difficulty (when finished), the dashboard and the report.

*Why:* routing needs an immediate answer; rubric scoring needs a strong model and several seconds. Splitting them keeps the conversation fluid without giving up rigor.

**Calibration (D-17).** Cosine similarities between on-topic texts cluster in a narrow, high band, so mapping [0, 1] straight onto [0, 100] would give mediocre answers around 60. The plan calibrates with about 30 hand-scored answers: low anchor near the 10th percentile of raw scores among answers you rated under 30, high anchor near the 90th among answers rated 80 or above, linear map, clamped. Provisional anchors are 0.40 and 0.80 until then. **[Assumption]** those provisional anchors. All embedding-based thresholds (embedding under 30, etc.) are defined on the calibrated scale.

**Reconciliation.** If the rubric score differs from the mean of keyword and embedding by more than 30 points, flag the answer and halve the rubric weight (to 0.175), renormalizing all weights by 0.825. *Why:* a large disagreement means either the LLM or the cheap signals are wrong; down-weighting the LLM, which is the less reproducible signal, is the conservative choice, and flagged answers are visible in the report. This is the concrete implementation of "the LLM proposes, the engine decides".

**Rubrics.** technical_depth, problem_solving, communication, behavioral, claim_defense (criteria and points in the PM plan, Step 12.1). Claim-defense exists so that honesty and specificity are rewarded over confident vagueness.

**How we know it works.** (1) Spearman correlation with your hand scores (target 0.7 or better on about 30 answers); (2) lower repeat-scoring variance than an LLM-only judge on the same answers; (3) an excellent and a weak scripted answer differ by at least 40 points with a readable breakdown.

### 5.14 ATS score **[Kept]**

Keyword match 40%, formatting/parseability 30%, completeness 20%, readability 10%. Keyword match reuses the skills matcher against JD terms (or role profile terms if no JD). It is deliberately rule-based: an ATS is a parser, and the useful feedback ("your dates are inconsistent", "these JD keywords are missing") is concrete. The weights are conventional, not scientific; the point is a transparent score with suggestions from the lowest-scoring components. **[Assumption]** weights.

### 5.15 Dashboard **[Kept, [New] panels]**

- **Technical, communication and confidence scores** from stored per-question components, not from a new LLM call.
- **Radar** across technical depth, problem solving, communication, code quality (from the GitHub overall score) and confidence.
- **Strengths and weaknesses** are the top and bottom dimensions or topics, each shown with the stored rubric justification.
- **Claim review panel (new):** resume wording, evidence status and reason, answer summary, resolution, using "worth discussing" language.
- **Coverage map (new):** topics covered, depth reached, score per topic and recorded gaps, including topics skipped for lack of evidence. This makes the depth/breadth policy visible to the candidate.
- **Hiring recommendation is rule-based**: average final score 75 or more with no majority of flagged answers is "Strong Hire signal"; 55 to 74 "Mixed, proceed with caution"; below 55 "Not ready yet". Contributing scores are shown. **[Assumption]** bands. The recommendation is deliberately mechanical so it is explainable; it is a practice signal, not a hiring decision.
- **Confidence score** is a heuristic from answer-length stability, hedging phrases and probe rate. It is the weakest metric on the dashboard and should be presented as an indicator, not a measurement.

### 5.16 Observability and the offline evaluation harness **[New]**

**Why (D-25, P5).** Without numbers you cannot tell whether a change helped, and you cannot defend the design in an interview. Tracing records, per turn: intent, retrieval rung, chunk ids, validator results, signals, the rule that fired, difficulty and tone, and per-stage latency. The harness scripts produce: retrieval recall@4 and MRR for dense, hybrid and hybrid+MMR; validator first-pass and fallback rates; score agreement versus hand labels (and versus an LLM-only baseline); score variance across repeats; latency p50/p95 per stage; maximum pairwise question similarity across scripted runs.

**Why Langfuse (self-hostable, framework-neutral).** LangSmith is an equally valid alternative. Either works; pick the one you can set up fastest.

**These are also your resume numbers.** "Hybrid retrieval improved recall@4 from X to Y over dense-only" and "hybrid scoring cut repeat-score variance by Z% versus an LLM-only judge" are far stronger than naming frameworks.

### 5.17 Security and privacy **[New]**

- **Candidate scoping by construction (D-26).** The retrieval service is built for one candidate and no method accepts another candidate id; every query includes the candidate filter and the not-deleted filter. A cross-candidate leak test is part of the suite. *Why:* with transcripts and resumes in one table, "remember to add the filter" is the kind of discipline that fails once.
- **Prompt injection.** Resumes, READMEs, GitHub text and candidate answers are written by other people. Every prompt delimits them, labels them untrusted and tells the model never to follow instructions inside them; outputs are schema-validated; the validator blocks reveals. This is mitigation, not elimination.
- **Privacy.** Transcripts are private per candidate and never publicly exposed.

### 5.18 Deployment and operations **[Kept]**

One combined container for the backend in week 1, a quick host (Render, Railway or Fly.io) with Postgres and pgvector, environment variables for all keys. Pin dependency versions at setup: LangGraph interrupt/resume names and pgvector iterative-scan support in particular are version-dependent.

---

## 6. Latency budget (target: final transcript to first audio, p50 2.5 s, p95 4 s)

| Stage | Expected | Notes |
|---|---|---|
| `fast_eval` (keyword + embedding, plus fast-tier contradiction call in parallel) | about 0.5 to 0.8 s | The model call dominates; local signals take tens of milliseconds |
| `decide` / `plan_turn` | negligible | Plain functions |
| `retrieve_context` | about 0.1 to 0.2 s, or about 0 with a prefetched packet | Prefetch only helps the "advance" branch |
| `generate_question` (strong tier, structured output) | about 1.0 to 1.8 s | Largest single cost; keep the prompt small |
| Validator | about 0.05 s | Includes one embedding for repetition check |
| TTS first audio | about 0.3 to 0.5 s | Sentence-level synthesis |
| **Total** | about 2 to 3.2 s | **[Assumption]** these are planning estimates to be replaced by traced measurements |

If the target is missed, the first things to try are: a smaller context packet, a faster model tier for generation on routine intents, running the contradiction check only when the memory summary contains relevant claims, and validating the `text` field early so synthesis can begin before the key points finish.

---

## 7. Scope: what is deliberately not in week 1

| Not built | Why | How the design keeps the door open |
|---|---|---|
| Multiple interviewer personalities | Needs distinct rubrics and question mixes; adds scope without proving the core | Role profiles and rubric ids are already data-driven |
| Live coding with AI review | Separate product surface (editor, sandbox, reviewer) | Would be a new intent and node set in the same graph |
| Multi-candidate comparison / recruiter tools | Different users | Candidate-scoped data model already separates candidates |
| Real-time voice framework (barge-in) | Highest integration risk | Graph is voice-agnostic |
| Cross-encoder reranker | Latency cost unproven | Single function boundary in `hybrid_search` |
| Revealing code evidence during the interview | Risks accusatory feel and false accusations | Evidence is stored and shown in the report |

**Cut order if the schedule slips:** (1) reranker, (2) tracing UI polish (keep logging), (3) reasoning-quality heuristic, (4) the "thorough" fact-check level, (5) role profiles beyond backend/frontend/full-stack/generic, (6) real-time voice framework. **Never cut:** the retrieval evaluation set, the router tests, the grounding validator, the claim ledger.

---

## 8. Assumptions to validate

| # | Assumption | How to validate | If wrong |
|---|---|---|---|
| A1 | Resume entry 1 is the most recent job | Check on the sample resumes; use parsed end dates if available | Order by date instead |
| A2 | Provisional embedding anchors (0.40 / 0.80) | Calibration with about 30 labeled answers | Use measured anchors; reduce embedding weight if correlation is weak |
| A3 | 20% flex pool | Read 5 or more transcripts: too many probes or interviews ending early | Adjust the share |
| A4 | Bucket mix by seniority | Dry-run on 3 candidates; read the plan | Tune percentages |
| A5 | Project and experience ranking weights | Does the top project match what a human would pick? | Tune weights |
| A6 | Router thresholds (65, 45, 40/30, 80/45, 0.85) | Scripted strong/weak fixtures; table-driven tests | Tune on the fixtures, keep tests in sync |
| A7 | BGE query instruction helps | Run retrieval evaluation both ways | Leave the flag off |
| A8 | pgvector version supports iterative scans | Check version; EXPLAIN ANALYZE on a filtered query | Use exact filtered scan |
| A9 | 50-word question limit is comfortable for listening | Listen to 10 generated questions | Raise or lower the limit |
| A10 | Latency estimates | Tracing on a real run | Apply the mitigations in section 6 |
| A11 | Evidence heuristics (testing under 40, architecture under 50) flag what a human would flag | Hand-check claims on test candidates | Tune thresholds; relax to "unverifiable" |
| A12 | Hiring recommendation bands (75, 55) | Compare against your own judgment of scripted runs | Adjust bands |
| A13 | Fast-tier model is reliable for the contradiction yes/no | Spot-check on contradicting and consistent fixtures | Add a deterministic pre-check or use a stronger tier |

---

## 9. Parameter reference (all tunable numbers in one place)

| Area | Parameter | Value |
|---|---|---|
| Embeddings | Model / dimension | bge-small-en-v1.5 / 384 |
| Chunking | Chunk token ceiling (model limit 512) | 480 |
| Retrieval | Semantic similarity floor (dense-only) | 0.35 |
| Retrieval | Callback similarity floor | 0.50 |
| Retrieval | Dense / keyword candidates per channel | 20 / 20 |
| Retrieval | RRF constant; fused set size | 60; 12 |
| Retrieval | MMR lambda | 0.7 |
| Retrieval | Context packet budget | about 900 tokens (primary about 500, evidence about 250, callback about 150) |
| Retrieval | Callback spacing | at most 1 per 3 turns |
| Retrieval | Database latency target | p95 150 ms or less at about 500 chunks |
| Plan | Length to turns | 10 / 15 / 20 |
| Plan | Opener + closing | 2 turns |
| Plan | Flex pool share | 20% of core turns, minimum 1 |
| Plan | Project budgets | 3 / 2 / 1 |
| Plan | Experience budgets | 2 / 1 |
| Plan | Project priority weights | 0.35 relevance, 0.25 evidence, 0.20 recency, 0.20 claims |
| Plan | Experience priority weights | 0.40 recency, 0.40 relevance, 0.20 claims |
| Plan | Recency decay | linear to 0 over 36 months |
| Claims | Impact weights | metric 1.0, architecture 0.9, leadership 0.6, other 0.3 |
| Claims | Gap multipliers | unsupported 1.5, unverifiable 1.2, supported 0.8 |
| Claims | Number of probes | 1 / 2 / 3 by fact-check setting |
| Claims | Evidence thresholds | testing under 40 unsupported, 60 or more supported; architecture under 50 weak |
| Questions | Max words / max question marks | 50 / 2 (follow-ups about 35 words) |
| Questions | Repetition threshold | cosine 0.85 |
| Questions | Key points per question | 4 to 6, each with 1 to 3 terms |
| Router | Shallow | keyword under 40 or embedding under 30 |
| Router | Weak / solid | fast under 45 / 65 or more |
| Router | Probes per question | 1 (2 for contradictions) |
| Router | Repeated-answer similarity | over 0.85 |
| Router | Struggle trigger | 2 consecutive weak answers |
| Difficulty | Up / down | rolling average of last 2 at 80 or more / 45 or less |
| Difficulty | Cooldown / cap | 1 turn / 4 for student_intern, else 5 |
| Fast score | Weights; don't-know cap | 0.4 keyword + 0.6 embedding; 20 |
| Evaluation | Final weights | 0.35 rubric, 0.20 keyword, 0.25 embedding, 0.20 reasoning |
| Evaluation | Reconciliation | gap over 30 flags the answer and halves rubric weight (renormalize by 0.825) |
| Evaluation | Provisional embedding anchors | 0.40 to 0, 0.80 to 100 |
| ATS | Weights | 0.4 keyword, 0.3 formatting, 0.2 completeness, 0.1 readability |
| Dashboard | Hiring bands | 75 or more / 55 to 74 / under 55 |
| Voice | Silence gap | about 1.5 s |
| Latency | Targets | p50 2.5 s, p95 4 s |

---

## 10. Talking points for interviews

**"Why LangGraph and not CrewAI?"** The interview is a long-lived, human-paced loop with explicit state and a deterministic controller. CrewAI models a team executing tasks; a graph runtime with interrupts and checkpoints models my problem directly. I'd reconsider CrewAI for multi-persona interviewers.

**"Why isn't the evaluator an agent?"** Scoring must be reproducible and explainable. The LLM proposes a score; the engine reconciles it with rubric, keyword and embedding signals and down-weights large disagreements.

**"How does it decide when to go deeper?"** Each topic has a budget and a depth ladder. After every answer, deterministic rules compare keyword coverage and calibrated embedding similarity with the budgets and decide to probe, deepen or move on. Planned slots and a separate flex pool guarantee coverage while still allowing depth.

**"How do you stop it hallucinating about the candidate?"** Retrieval runs before generation by fixed recipe; the model must cite chunk ids; a validator checks entities against those chunks and rejects ungrounded or repeated questions; failures fall back to a seed bank.

**"What about the resume-versus-GitHub check?"** Claims are stored as their own chunks and ranked by impact and evidence gap. Only repo-linked project claims are compared with code. The interviewer asks open questions without revealing the evidence; the comparison appears afterwards as "worth discussing". Missing evidence in a public repo is not proof of absence.

**"How do you know it works?"** Quote the numbers: retrieval recall@4 for dense versus hybrid, grounding rate, score agreement and variance versus an LLM-only judge, and latency percentiles.

**"What would you do next?"** Real-time voice with barge-in, interviewer personas as role profiles, a cross-encoder reranker if the evaluation justifies it, and a live-coding intent.

---

## 11. Glossary

| Term | Meaning |
|---|---|
| Chunk | A small unit of text plus metadata stored with an embedding |
| Embedding | A numeric vector representing a text's meaning |
| `detected_tech` | Lowercased technology tags found in a chunk |
| `project_key` | Normalized project slug shared by all chunks about one project |
| Claim | A checkable sentence from the resume or project description |
| Claim ledger | Per-session record of each claim's evidence status and probe status |
| Blueprint | The pre-computed interview plan: slots, budgets, ladders, ledger |
| Slot | One planned topic with a budget (a project, job, fundamentals topic or behavioral question) |
| Ladder | The ordered question depths within a slot (D0 to D3) |
| Flex pool | Turns reserved for probes, contradictions, revisits and stretches |
| Probe | A same-depth clarifying follow-up |
| Deepen / stretch | Move to the next ladder rung / go one rung beyond the budget using the pool |
| Fast path / slow path | Local, in-loop signals that drive routing / background rubric scoring and reconciliation |
| Context packet | The size-bounded evidence bundle assembled for one question |
| Fallback ladder | recipe, relaxed, role topic, seed bank |
| RRF | Reciprocal rank fusion: merges ranked lists by summing 1/(60 + rank) |
| MMR | Maximal marginal relevance: picks results that are relevant and not redundant |
| Checkpointer | LangGraph component that saves graph state so a session can resume |
