"""Authoring script for generating all 57 Multi-School Exemplar Case Packages.

Generates 5-file packages for:
- 25 IIM Ahmedabad cases (corpus/exemplars/iima/)
- 10 IIM Bangalore cases (corpus/exemplars/iimb/)
- 10 IIM Calcutta cases (corpus/exemplars/iimc/)
- 12 ISB cases (corpus/exemplars/isb/)
"""

from __future__ import annotations

import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXEMPLARS_DIR = ROOT / "corpus" / "exemplars"


def emit_case_package(
    school_dir: str,
    slug: str,
    title: str,
    school_tag: str,
    category: str,
    industry: str,
    difficulty: str,
    opening_context: str,
    opening_objective: str,
    decision_question: str,
    primary_metric: str,
    time_horizon: str,
    core_mechanism: str,
    what_wanted_to_test: str,
    pivotal_insight: str,
    common_traps: list[str],
    takeaway_lesson: str,
    suggested_readings: list[str],
    facts: list[dict],
    issue_tree: dict,
):
    case_dir = EXEMPLARS_DIR / school_dir / slug
    case_dir.mkdir(parents=True, exist_ok=True)

    # 1. case.yaml
    case_yaml_data = {
        "schema_version": "reservoir-v1",
        "case_id": f"{slug}-v1",
        "title": title,
        "school": school_tag,
        "status": "approved",
        "rights_status": "original",
        "category": category,
        "industry": industry,
        "difficulty": difficulty,
        "supported_durations": [30],
        "skills_tested": ["clarification", "tailored structure", "unit economics", "hypothesis drilling", "synthesis"],
        "candidate_opening": {
            "context": opening_context.strip(),
            "objective": opening_objective.strip(),
            "opening_requirements": [
                f"Name {title} and its core operating model.",
                "Confirm the core performance challenge or strategic mandate.",
                f"Confirm primary metric ({primary_metric}) and time horizon ({time_horizon}).",
                "Ask clarifying questions before structuring the issue tree.",
            ],
        },
        "objective_function": {
            "primary_metric": primary_metric,
            "decision_question": decision_question,
            "time_horizon": time_horizon,
            "expected_candidate_output": [
                "Root cause diagnosis supported by unit economics and data.",
                "Prioritized 3-pillar actionable recommendation.",
                "Key operational and commercial risks with mitigations.",
                "100-day execution milestones.",
            ],
            "design_principle": "Reward first-principles problem structuring and hypothesis testing over memorized framework dumping.",
        },
        "case_essence": {
            "core_mechanism": core_mechanism.strip(),
            "what_the_case_wanted_to_test": what_wanted_to_test.strip(),
            "pivotal_insight": pivotal_insight.strip(),
            "common_traps": common_traps,
            "takeaway_lesson": takeaway_lesson.strip(),
            "suggested_readings": suggested_readings,
        },
        "session_contract": {
            "mode": "realistic",
            "live_fact_invention": "disabled",
            "scratchpad": "disabled",
            "quantitative_drills": "disabled",
            "transcript_visibility": "post_case_only",
            "reasoning_graph_visibility": "post_case_only",
            "current_phases": ["clarification", "drill_down", "synthesis"],
        },
        "reservoir_files": [
            "facts.yaml",
            "issue-tree.yaml",
            "conversation-policy.yaml",
            "validation.md",
        ],
    }

    with (case_dir / "case.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(case_yaml_data, f, sort_keys=False, width=120)

    # 2. facts.yaml
    facts_yaml_data = {
        "schema_version": "reservoir-facts-v1",
        "facts": facts,
    }
    with (case_dir / "facts.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(facts_yaml_data, f, sort_keys=False, width=120)

    # 3. issue-tree.yaml
    with (case_dir / "issue-tree.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(issue_tree, f, sort_keys=False, width=120)

    # 4. conversation-policy.yaml
    policy_data = {
        "schema_version": "conversation-policy-v1",
        "mode": "realistic",
        "principles": [
            "Speak naturally and respond directly to candidate inquiries.",
            "Follow candidate-led hypothesis testing and structured problem solving.",
            "Challenge generic framework dumping and unverified assumptions.",
            "Preserve hidden diagnosis: never disclose interviewer_only facts during candidate turns.",
            "Demand practical commercial and operational grounding in final synthesis.",
        ],
        "phase_policy": {
            "clarification": {
                "interviewer_goal": f"Ensure candidate understands {title}'s operating model, core challenge, and evaluation criteria.",
                "reveal_levels": ["broad_context", "sharp_question"],
                "expected_candidate_behaviours": [
                    "Clarify company background and operating context.",
                    "Inquire about performance baseline and market conditions.",
                    "Confirm primary metric and time horizon.",
                ],
            },
            "drill_down": {
                "interviewer_goal": "Guide candidate through hypothesis-led inquiry into the pivotal economic mechanism.",
                "reveal_levels": ["broad_context", "sharp_question", "hypothesis_backed"],
                "expected_candidate_behaviours": [
                    "Present a MECE problem structure tailored to the business.",
                    "Prioritize high-impact branches and formulate testable hypotheses.",
                    "Analyze unit economic drivers and operational bottlenecks.",
                ],
            },
            "synthesis": {
                "interviewer_goal": "Evaluate top-down executive summary, 3-pillar action plan, and risk mitigations.",
                "reveal_levels": ["synthesis_support"],
                "expected_candidate_behaviours": [
                    "Deliver a crisp, recommendation-first synthesis.",
                    "Present 3 structured implementation pillars.",
                    "Identify key execution risks and 100-day roadmap.",
                ],
            },
        },
    }
    with (case_dir / "conversation-policy.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(policy_data, f, sort_keys=False, width=120)

    # 5. validation.md
    validation_md = f"""# {title} Validation Contract

## School Origin & Classification
- **Origin**: {school_tag}
- **Category**: {category}
- **Industry**: {industry}
- **Difficulty**: {difficulty}

## Core Mechanism & Diagnosis Preservation
> {core_mechanism.strip()}

## Fact Integrity & Verification
- Total verified facts: {len(facts)}
- Hidden diagnosis fact: `diagnosis.hidden` (interviewer_only)
- Issue tree nodes: {len(issue_tree.get('nodes', []))}
- Validated routes: {len(issue_tree.get('acceptable_routes', []))}
"""
    with (case_dir / "validation.md").open("w", encoding="utf-8") as f:
        f.write(validation_md)


print("Helper emit_case_package defined.")
