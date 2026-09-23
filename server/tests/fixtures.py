"""
Candidate test fixtures for verifying chunking and metadata enrichment.
"""

from typing import Any

TEST_CANDIDATE_ID = "00000000-0000-0000-0000-000000000001"

TEST_RESUME_TEXT = """
Prakhar Singhal
Senior Software Engineer
Email: prakhar@example.com | Phone: +1 555-0199 | Location: San Francisco, CA
GitHub: https://github.com/testuser

Professional Summary:
Experienced software engineer specializing in distributed systems and AI platforms. Built high-scale cloud native applications using FastAPI, React, PostgreSQL, and Redis.

Work Experience:
Senior Software Engineer | TechCorp Inc. (Jan 2022 - Present)
- Built a scalable microservices architecture with FastAPI and PostgreSQL handling 50k requests/sec.
- Reduced latency by 40% using Redis caching and connection pooling.
- Led a team of 4 engineers in migrating legacy infrastructure to Docker and Kubernetes on AWS.

Software Engineer | StartupLabs (Jun 2019 - Dec 2021)
- Developed responsive web interfaces using React, Redux, and TailwindCSS.
- Improved CI/CD deployment pipelines, cutting build times by 35%.
- Implemented automated end-to-end testing with pytest and Cypress.

Education:
B.S. in Computer Science | State University (2015 - 2019)
- Graduated magna cum laude. Courses: Distributed Systems, Operating Systems, Machine Learning.
"""

TEST_RESUME_SECTIONS = {
    "Summary": "Experienced software engineer specializing in distributed systems and AI platforms. Built high-scale cloud native applications using FastAPI, React, PostgreSQL, and Redis.",
    "Experience": "Senior Software Engineer | TechCorp Inc. (Jan 2022 - Present)\n- Built a scalable microservices architecture with FastAPI and PostgreSQL handling 50k requests/sec.\n- Reduced latency by 40% using Redis caching and connection pooling.\n- Led a team of 4 engineers in migrating legacy infrastructure to Docker and Kubernetes on AWS.\n\nSoftware Engineer | StartupLabs (Jun 2019 - Dec 2021)\n- Developed responsive web interfaces using React, Redux, and TailwindCSS.\n- Improved CI/CD deployment pipelines, cutting build times by 35%.\n- Implemented automated end-to-end testing with pytest and Cypress.",
    "Education": "B.S. in Computer Science | State University (2015 - 2019)\n- Graduated magna cum laude. Courses: Distributed Systems, Operating Systems, Machine Learning."
}

TEST_RESUME_SKILLS = [
    "Python", "FastAPI", "React", "PostgreSQL", "Redis",
    "Docker", "Kubernetes", "AWS", "Git", "TypeScript",
    "Redux", "CI/CD", "Linux", "PyTest", "GraphQL"
]

TEST_RESUME_PROJECTS = [
    {
        "title": "AceView Cloud",
        "description": "AI interview platform built with React, FastAPI and PostgreSQL. Reduced latency by 40% using Redis.",
        "technologies": ["React", "FastAPI", "PostgreSQL", "Redis"],
        "url": "https://github.com/testuser/aceview-cloud"
    },
    {
        "title": "Offline Analyzer",
        "description": "Local data analysis tool written in Python. Processes CSV and parquet files.",
        "technologies": ["Python", "Pandas"],
        "url": ""
    }
]

TEST_PROJECT_LINKS = [
    {
        "project_name": "AceView Cloud",
        "uri": "https://github.com/testuser/aceview-cloud",
        "context": "Main repository link for AceView Cloud"
    }
]

TEST_GITHUB_REPOS = [
    {
        "id": "c1b3f9b2-3211-4712-b918-6c8411bcf234",
        "name": "aceview-cloud",
        "url": "https://github.com/testuser/aceview-cloud",
        "description": "AI interview platform with React, FastAPI and Redis",
        "languages": {"Python": 65000, "TypeScript": 35000},
        "readme_text": """[![Build](https://img.shields.io/badge/build-passing-green.svg)](https://example.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://example.com)

# AceView Cloud

AI interview platform built with React, FastAPI and PostgreSQL.

## Architecture
The system uses a microservices architecture deployed on Kubernetes with Redis caching.

## Testing
We maintain 90% test coverage using pytest. All pull requests run automated CI testing.

## License
MIT License. Copyright 2026.
""",
        "overall_code_score": 88.0,
        "architecture_score": 90.0,
        "testing_score": 85.0,
        "complexity_score": 80.0,
        "documentation_score": 82.0,
        "commit_score": 92.0
    },
    {
        "id": "e2c4a1b3-4322-5823-c029-7d9522cdf345",
        "name": "headingless-tool",
        "url": "https://github.com/testuser/headingless-tool",
        "description": "A headingless utility tool for data conversion and batch processing.",
        "languages": {"Python": 12000},
        "readme_text": (
            "A lightweight utility tool for data transformation and batch processing. "
            "It provides simple CLI utilities for batch data processing, normalization, and stream validation. "
            "This utility reads raw CSV and JSON files and converts them into normalized database tables with schema validation. "
            "It is written in Python and uses SQLite for local caching. It has no section headers anywhere in the file.\n\n"
            "The pipeline architecture ingests streaming data sources, cleanses anomalies, and serializes payloads into standard columnar formats. "
            "Each batch worker processes transactions asynchronously using multiprocessing pools and in-memory ring buffers with zero external dependencies.\n\n"
            "Configuration is handled entirely through environment variables or JSON configuration profiles loaded on startup. "
            "The daemon monitors input directories for new records, applies transformation rules, and exports structured results to PostgreSQL or AWS S3 buckets."
        ),
        "overall_code_score": 75.0,
        "architecture_score": 70.0,
        "testing_score": 72.0,
        "complexity_score": 78.0,
        "documentation_score": 65.0,
        "commit_score": 74.0
    }
]

TEST_GITHUB_PROFILE_SUMMARY = {
    "username": "testuser",
    "rag_summary": "Active open source developer with 1,200 contributions over the past year. High commit consistency and strong collaboration in Python and TypeScript ecosystems.",
    "score_data": {
        "overall_score": 86.5,
        "sub_scores": {
            "activity": 88.0,
            "consistency": 90.0,
            "collaboration": 82.0,
            "maturity": 85.0,
            "diversity": 87.0
        }
    }
}
