"""
Unit tests for AceView chunking layer.
"""

import unittest
from rag.chunking import (
    count_tokens,
    assert_within_model_limit,
    _split_into_token_windows,
    build_all_chunks,
    chunk_skills,
    chunk_projects,
    chunk_resume,
    chunk_readme,
    chunk_code_summary,
    chunk_github_profile_summary,
)
from tests.fixtures import (
    TEST_CANDIDATE_ID,
    TEST_RESUME_SECTIONS,
    TEST_RESUME_SKILLS,
    TEST_RESUME_PROJECTS,
    TEST_PROJECT_LINKS,
    TEST_GITHUB_REPOS,
    TEST_GITHUB_PROFILE_SUMMARY,
)


class TestTask1TokenizerSizing(unittest.TestCase):
    def test_assert_within_model_limit(self):
        # 100 tokens synthetic string (approx 100 words repeated)
        short_text = " ".join(["distributed architecture testing framework"] * 25)
        self.assertLess(count_tokens(short_text), 480)
        # Should not raise
        assert_within_model_limit(short_text, "test-chunk-100")

        # 600 tokens synthetic string
        long_text = " ".join(["microservices distributed cache database indexing optimization"] * 150)
        self.assertGreater(count_tokens(long_text), 480)
        with self.assertRaises(ValueError) as ctx:
            assert_within_model_limit(long_text, "test-chunk-600")
        self.assertIn("exceeds maximum model token limit", str(ctx.exception))

    def test_sentence_snap_preserves_sentence_boundary(self):
        # Text with distinct sentences
        sentence_1 = "This is the first sentence about distributed systems architecture and microservices design patterns."
        sentence_2 = "This is the second sentence which details our asynchronous message queue processing with Kafka and Redis."
        sentence_3 = "This is the third sentence explaining how unit tests and integration tests verify every endpoint."
        full_text = f"{sentence_1} {sentence_2} {sentence_3}"

        # Split with window that forces cut after sentence 1 or 2
        windows = _split_into_token_windows(full_text, max_tokens=30, overlap_tokens=5)
        self.assertTrue(len(windows) >= 2)
        # The first window should end with a period (sentence snapped)
        self.assertTrue(windows[0].endswith("."))

    def test_no_chunk_exceeds_480_tokens_in_fixture(self):
        chunks = build_all_chunks(
            candidate_id=TEST_CANDIDATE_ID,
            resume_sections=TEST_RESUME_SECTIONS,
            resume_skills=TEST_RESUME_SKILLS,
            resume_projects=TEST_RESUME_PROJECTS,
            resume_links=TEST_PROJECT_LINKS,
            years_of_experience=5.0,
            github_repos=TEST_GITHUB_REPOS,
            github_profile_summary=TEST_GITHUB_PROFILE_SUMMARY,
        )
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            tok_count = count_tokens(chunk["text"])
            self.assertLessEqual(
                tok_count,
                480,
                f"Chunk {chunk['chunk_id']} ({chunk['source_type']}) has {tok_count} tokens > 480"
            )


class TestTask2DetectedTech(unittest.TestCase):
    def test_extract_tech_entities(self):
        from rag.chunking import extract_tech_entities
        text = "Built a distributed web application using React, FastAPI, PostgreSQL, and Redis."
        tech = extract_tech_entities(text)
        self.assertIn("react", tech)
        self.assertIn("fastapi", tech)
        self.assertIn("postgresql", tech)
        self.assertIn("redis", tech)

    def test_detected_tech_across_source_types(self):
        chunks = build_all_chunks(
            candidate_id=TEST_CANDIDATE_ID,
            resume_sections=TEST_RESUME_SECTIONS,
            resume_skills=TEST_RESUME_SKILLS,
            resume_projects=TEST_RESUME_PROJECTS,
            resume_links=TEST_PROJECT_LINKS,
            years_of_experience=5.0,
            github_repos=TEST_GITHUB_REPOS,
            github_profile_summary=TEST_GITHUB_PROFILE_SUMMARY,
        )

        applicable_source_types = {"skills", "project", "resume", "readme", "code_summary"}
        for chunk in chunks:
            st = chunk["source_type"]
            meta = chunk["metadata"]
            if st in applicable_source_types:
                self.assertIn(
                    "detected_tech",
                    meta,
                    f"Chunk {chunk['chunk_id']} of source_type {st} missing detected_tech"
                )
                self.assertIsInstance(
                    meta["detected_tech"],
                    list,
                    f"detected_tech in {chunk['chunk_id']} should be a list"
                )
            elif st == "github_profile_summary":
                self.assertNotIn(
                    "detected_tech",
                    meta,
                    "github_profile_summary chunk should NOT have detected_tech"
                )

        # Cross-source linkage: query for chunks where detected_tech contains 'react'
        react_chunks = [c for c in chunks if "react" in c["metadata"].get("detected_tech", [])]
        react_sources = {c["source_type"] for c in react_chunks}
        self.assertGreaterEqual(
            len(react_sources),
            2,
            f"Expected chunks with 'react' from at least 2 source types, got {react_sources}"
        )


class TestTask3ProjectKey(unittest.TestCase):
    def test_normalize_project_key(self):
        from rag.chunking import normalize_project_key
        self.assertEqual(normalize_project_key("AceView Cloud"), "aceview-cloud")
        self.assertEqual(normalize_project_key("my_cool.project!"), "my-cool-project")
        self.assertEqual(normalize_project_key("  --Special-Repo-- "), "special-repo")
        self.assertEqual(normalize_project_key(""), "")

    def test_project_key_cross_source_linkage(self):
        chunks = build_all_chunks(
            candidate_id=TEST_CANDIDATE_ID,
            resume_sections=TEST_RESUME_SECTIONS,
            resume_skills=TEST_RESUME_SKILLS,
            resume_projects=TEST_RESUME_PROJECTS,
            resume_links=TEST_PROJECT_LINKS,
            years_of_experience=5.0,
            github_repos=TEST_GITHUB_REPOS,
            github_profile_summary=TEST_GITHUB_PROFILE_SUMMARY,
        )

        # Filtering on project_key == 'aceview-cloud'
        aceview_chunks = [c for c in chunks if c["metadata"].get("project_key") == "aceview-cloud"]
        self.assertGreater(len(aceview_chunks), 0)

        aceview_sources = {c["source_type"] for c in aceview_chunks}
        # Acceptance criteria: returns chunks from project, readme, and code_summary simultaneously
        self.assertIn("project", aceview_sources)
        self.assertIn("readme", aceview_sources)
        self.assertIn("code_summary", aceview_sources)

        # Resume-only project should also have a valid project_key
        offline_chunks = [c for c in chunks if c["metadata"].get("project_key") == "offline-analyzer"]
        self.assertGreaterEqual(len(offline_chunks), 1)
        self.assertEqual(offline_chunks[0]["source_type"], "project")


class TestTask4CodeSummarySplit(unittest.TestCase):
    def test_repo_produces_3_code_summary_sub_chunks(self):
        chunks = build_all_chunks(
            candidate_id=TEST_CANDIDATE_ID,
            resume_sections=TEST_RESUME_SECTIONS,
            resume_skills=TEST_RESUME_SKILLS,
            resume_projects=TEST_RESUME_PROJECTS,
            resume_links=TEST_PROJECT_LINKS,
            years_of_experience=5.0,
            github_repos=TEST_GITHUB_REPOS,
            github_profile_summary=TEST_GITHUB_PROFILE_SUMMARY,
        )

        code_chunks = [c for c in chunks if c["source_type"] == "code_summary"]
        # In fixtures we have 2 repos: aceview-cloud and headingless-tool
        # Each must produce exactly 3 chunks -> total 6
        self.assertEqual(len(code_chunks), 2 * 3)

        # Check aceview-cloud repo specifically
        aceview_code_chunks = [
            c for c in code_chunks
            if c["metadata"].get("project_key") == "aceview-cloud"
        ]
        self.assertEqual(len(aceview_code_chunks), 3)

        kinds = {c["metadata"].get("summary_kind") for c in aceview_code_chunks}
        self.assertEqual(kinds, {"architecture", "testing", "commits"})

        # Check chunk_id format
        repo_id = TEST_GITHUB_REPOS[0]["id"]
        expected_ids = {f"{repo_id}-architecture", f"{repo_id}-testing", f"{repo_id}-commits"}
        actual_ids = {c["chunk_id"] for c in aceview_code_chunks}
        self.assertEqual(actual_ids, expected_ids)

    def test_testing_sub_chunk_content_isolation(self):
        chunks = build_all_chunks(
            candidate_id=TEST_CANDIDATE_ID,
            github_repos=TEST_GITHUB_REPOS,
        )

        testing_chunks = [
            c for c in chunks
            if c["source_type"] == "code_summary" and c["metadata"].get("summary_kind") == "testing"
        ]
        self.assertEqual(len(testing_chunks), len(TEST_GITHUB_REPOS))

        for tc in testing_chunks:
            text_lower = tc["text"].lower()
            # Must mention testing/quality/complexity/documentation
            self.assertIn("testing score", text_lower)
            self.assertIn("complexity score", text_lower)
            # Must NOT mention architecture score or commit score
            self.assertNotIn("architecture score", text_lower)
            self.assertNotIn("commit history score", text_lower)


class TestTask5ClaimChunking(unittest.TestCase):
    def test_claims_extraction_metric_and_architecture(self):
        from tests.fixtures import TEST_RESUME_TEXT
        from rag.chunking import chunk_claim, chunk_projects

        proj_chunks = chunk_projects(
            candidate_id=TEST_CANDIDATE_ID,
            projects=TEST_RESUME_PROJECTS,
            project_links=TEST_PROJECT_LINKS,
        )

        claim_chunks = chunk_claim(
            resume_text=TEST_RESUME_TEXT,
            project_chunks=proj_chunks,
            candidate_id=TEST_CANDIDATE_ID,
        )
        self.assertGreater(len(claim_chunks), 0)

        # 1. Assert metric claim is extracted ("reduced latency by 40%")
        metric_claims = [
            c for c in claim_chunks
            if c.metadata.get("claim_type") == "metric" and "reduced latency by 40%" in c.text.lower()
        ]
        self.assertGreaterEqual(
            len(metric_claims),
            1,
            "Expected 'reduced latency by 40%' to be extracted as a metric claim"
        )
        self.assertFalse(metric_claims[0].metadata["verified"])
        self.assertIn("redis", metric_claims[0].metadata["detected_tech"])

        # 2. Assert architecture claim is extracted ("built a scalable microservices architecture")
        arch_claims = [
            c for c in claim_chunks
            if c.metadata.get("claim_type") == "architecture" and "scalable microservices architecture" in c.text.lower()
        ]
        self.assertGreaterEqual(
            len(arch_claims),
            1,
            "Expected 'built a scalable microservices architecture' to be extracted as an architecture claim"
        )
        self.assertFalse(arch_claims[0].metadata["verified"])
        self.assertIn("fastapi", arch_claims[0].metadata["detected_tech"])
        self.assertIn("postgresql", arch_claims[0].metadata["detected_tech"])

        # 3. Assert project_key is assigned when claim comes from an identifiable project
        project_claims = [
            c for c in claim_chunks
            if c.metadata.get("project_key") == "aceview-cloud"
        ]
        self.assertGreaterEqual(
            len(project_claims),
            1,
            "Expected claims from AceView Cloud to carry project_key='aceview-cloud'"
        )


class TestTask6TranscriptChunking(unittest.TestCase):
    def test_chunk_transcript_creation_and_upsert_id(self):
        from rag.chunking import chunk_transcript

        t1 = chunk_transcript(
            question="How do you handle Redis cache invalidation?",
            answer="We use write-through caching and TTL eviction with FastAPI and Redis.",
            candidate_id=TEST_CANDIDATE_ID,
            turn_number=1,
            question_topic="caching_strategy",
            evaluation_score=None,
        )

        self.assertEqual(t1.source_type, "transcript")
        self.assertEqual(t1.chunk_id, f"{TEST_CANDIDATE_ID}-turn-1")
        self.assertEqual(t1.metadata["turn_number"], 1)
        self.assertEqual(t1.metadata["question_topic"], "caching_strategy")
        self.assertIsNone(t1.metadata["evaluation_score"])
        self.assertIn("redis", t1.metadata["detected_tech"])
        self.assertIn("fastapi", t1.metadata["detected_tech"])

        # Second call with updated answer and evaluation_score
        t2 = chunk_transcript(
            question="How do you handle Redis cache invalidation?",
            answer="Updated answer: We use write-through caching with Redis, Celery, and PostgreSQL.",
            candidate_id=TEST_CANDIDATE_ID,
            turn_number=1,
            question_topic="caching_strategy",
            evaluation_score=92,
        )

        # Same candidate_id and turn_number must yield the identical chunk_id (for upserting)
        self.assertEqual(t1.chunk_id, t2.chunk_id)
        self.assertEqual(t2.metadata["evaluation_score"], 92)

    def test_store_chunks_accepts_transcript_chunk_and_preserves_upsert(self):
        from unittest.mock import MagicMock
        from rag.chunking import chunk_transcript
        from rag.embeddings import store_chunks

        mock_session = MagicMock()
        t = chunk_transcript(
            question="What is GraphQL?",
            answer="A query language for APIs using FastAPI.",
            candidate_id=TEST_CANDIDATE_ID,
            turn_number=2,
            question_topic="api_design",
            evaluation_score=85,
        )

        # store_chunks accepts [t] directly (Chunk dataclass instance) without throwing TypeError
        count = store_chunks(mock_session, [t])
        self.assertEqual(count, 1)
        self.assertTrue(mock_session.execute.called)
        self.assertTrue(mock_session.commit.called)


class TestTask7ChunkLevelCleanup(unittest.TestCase):
    def test_skills_category_clustering_isolation(self):
        from rag.chunking import chunk_skills, classify_skill_category

        chunks = chunk_skills(TEST_CANDIDATE_ID, TEST_RESUME_SKILLS)
        self.assertGreater(len(chunks), 0)

        observed_categories = set()
        for c in chunks:
            cat = c.metadata.get("skill_category")
            self.assertIsNotNone(cat)
            self.assertIn(cat, {"language", "backend", "frontend", "infra", "data", "tools"})
            observed_categories.add(cat)

            # Acceptance criteria: No skills chunk mixes more than one category
            for skill in c.metadata["skills"]:
                self.assertEqual(
                    classify_skill_category(skill),
                    cat,
                    f"Skill '{skill}' does not belong to chunk category '{cat}'",
                )

        # Confirm multiple distinct categories were extracted from the fixture
        self.assertTrue(len(observed_categories) >= 3)

    def test_resume_chunk_per_logical_entry_isolation(self):
        from rag.chunking import chunk_resume

        chunks = chunk_resume(
            candidate_id=TEST_CANDIDATE_ID,
            sections=TEST_RESUME_SECTIONS,
            skills=None,
            projects=None,
        )

        exp_chunks = [c for c in chunks if c.section == "Experience"]
        self.assertGreaterEqual(len(exp_chunks), 2)

        # Acceptance criteria: No resume chunk contains text from two different job/education entries
        techcorp_found = False
        startuplabs_found = False
        for c in exp_chunks:
            has_techcorp = "techcorp" in c.text.lower()
            has_startuplabs = "startuplabs" in c.text.lower()

            if has_techcorp:
                techcorp_found = True
                self.assertFalse(
                    has_startuplabs,
                    "Resume chunk contains text from both TechCorp and StartupLabs entries!",
                )
            if has_startuplabs:
                startuplabs_found = True
                self.assertFalse(
                    has_techcorp,
                    "Resume chunk contains text from both StartupLabs and TechCorp entries!",
                )

        self.assertTrue(techcorp_found)
        self.assertTrue(startuplabs_found)

    def test_headingless_readme_produces_multiple_chunks(self):
        from rag.chunking import chunk_readme

        headingless_repo = next(r for r in TEST_GITHUB_REPOS if r["name"] == "headingless-tool")
        chunks = chunk_readme(
            candidate_id=TEST_CANDIDATE_ID,
            repo_name=headingless_repo["name"],
            readme_text=headingless_repo["readme_text"],
            repo_id=headingless_repo["id"],
        )

        # Acceptance criteria: A heading-less README fixture still produces multiple reasonably-sized chunks
        self.assertGreaterEqual(
            len(chunks),
            2,
            f"Expected headingless README to produce multiple chunks, got {len(chunks)}",
        )
        for c in chunks:
            self.assertLessEqual(count_tokens(c.text), 150)

    def test_readme_badge_toc_license_stripping(self):
        from rag.chunking import chunk_readme

        aceview_repo = next(r for r in TEST_GITHUB_REPOS if r["name"] == "aceview-cloud")
        chunks = chunk_readme(
            candidate_id=TEST_CANDIDATE_ID,
            repo_name=aceview_repo["name"],
            readme_text=aceview_repo["readme_text"],
            repo_id=aceview_repo["id"],
        )

        self.assertGreater(len(chunks), 0)
        # Acceptance criteria: Badge/TOC/license lines do not appear in any stored readme chunk text
        for c in chunks:
            text_lower = c.text.lower()
            self.assertNotIn("shields.io", text_lower)
            self.assertNotIn("[![build]", text_lower)
            self.assertNotIn("[![license]", text_lower)
            self.assertNotIn("mit license. copyright", text_lower)


if __name__ == "__main__":
    unittest.main()
