"""The gate that stops a broken contributed case reaching a candidate."""

from __future__ import annotations

import copy

import pytest

from app.case_validator import validate_package


def _valid_package() -> dict:
    """A minimal package that passes every deterministic check."""
    return {
        "case": {
            "case_id": "contributed-test-v1",
            "title": "Northwind Cold Storage",
            "category": "profitability",
            "industry": "logistics",
            "difficulty": "intermediate",
            "source": "community",
            "candidate_opening": {
                "context": "The client runs temperature-controlled warehouses.",
                "objective": "Explain the margin decline and recommend a response.",
            },
            "objective_function": {
                "primary_metric": "EBITDA margin",
                "decision_question": "Why has margin fallen?",
                "time_horizon": "twelve months",
            },
            "case_essence": {
                "core_mechanism": "Mix shift into low-utilisation routes priced off a legacy cost base.",
                "what_the_case_wanted_to_test": "Cost-to-serve allocation accuracy.",
                "pivotal_insight": "Volume grew while contribution per unit collapsed.",
                "common_traps": [
                    "Blaming fuel inflation without testing segment cost-to-serve.",
                    "Proposing an exit rather than repricing.",
                ],
                "takeaway_lesson": "Price to route density, never to average system cost.",
            },
        },
        "facts": {
            "facts": [
                {
                    "id": "company.identity",
                    "domain": "company",
                    "release_level": "opening",
                    "content": "The client operates cold storage warehouses.",
                },
                {
                    "id": "economics.rate",
                    "domain": "economics",
                    "release_level": "sharp_question",
                    "content": "The realised rate is 20 per unit.",
                    "numeric_value": 20.0,
                },
                {
                    "id": "economics.cost",
                    "domain": "economics",
                    "release_level": "sharp_question",
                    "content": "Cost to serve is 20 per unit.",
                    "numeric_value": 20.0,
                },
                {
                    "id": "economics.contribution",
                    "domain": "economics",
                    "release_level": "hypothesis_backed",
                    "content": "Contribution per unit is zero.",
                    "numeric_value": 0.0,
                    "formula": "rate - cost",
                    "depends_on": {"rate": "economics.rate", "cost": "economics.cost"},
                    "dependencies": ["economics.rate", "economics.cost"],
                },
            ]
        },
        "conversation_policy": {
            "phase_policy": {
                "clarification": {
                    "interviewer_goal": "Confirm scope.",
                    "reveal_levels": ["opening", "broad_context", "sharp_question"],
                },
                "drill_down": {
                    "interviewer_goal": "Test a hypothesis.",
                    "reveal_levels": ["sharp_question", "hypothesis_backed"],
                },
            }
        },
    }


def test_a_well_formed_package_passes() -> None:
    result = validate_package(_valid_package())

    assert result.passed, [f.message for f in result.errors]
    assert result.errors == []


# --- Schema ------------------------------------------------------------------


def test_a_package_missing_its_case_section_fails_immediately() -> None:
    result = validate_package({"facts": {}, "conversation_policy": {}})

    assert not result.passed
    assert any(finding.check == "schema" for finding in result.errors)


def test_schema_failure_does_not_cascade_into_unrelated_noise() -> None:
    """One real error is more actionable than twenty downstream ones."""
    result = validate_package({"case": {"case_id": "x"}})

    assert not result.passed
    assert {finding.check for finding in result.errors} == {"schema"}


# --- Essence, the teeth ------------------------------------------------------


@pytest.mark.parametrize("missing", ["core_mechanism", "pivotal_insight", "takeaway_lesson"])
def test_a_case_without_its_teachable_core_is_rejected(missing: str) -> None:
    package = _valid_package()
    package["case"]["case_essence"][missing] = ""

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == missing for finding in result.errors)


def test_a_case_with_fewer_than_two_traps_is_rejected() -> None:
    """Bland, not broken, is the failure mode a crowdsourced corpus dies of."""
    package = _valid_package()
    package["case"]["case_essence"]["common_traps"] = ["Only one trap."]

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == "common_traps" for finding in result.errors)


# --- Dependency graph --------------------------------------------------------


def test_a_dangling_dependency_is_rejected() -> None:
    package = _valid_package()
    package["facts"]["facts"][0]["dependencies"] = ["economics.ghost"]

    result = validate_package(package)

    assert not result.passed
    assert any("does not exist" in finding.message for finding in result.errors)


def test_a_dependency_cycle_is_reported_with_its_path() -> None:
    """Every fact in a cycle waits forever on another, so none can ever release."""
    package = _valid_package()
    facts = package["facts"]["facts"]
    facts[0]["dependencies"] = ["economics.rate"]
    facts[1]["dependencies"] = ["company.identity"]

    result = validate_package(package)

    assert not result.passed
    cycle_errors = [f for f in result.errors if "cycle" in f.message.lower()]
    assert cycle_errors
    assert "->" in cycle_errors[0].message


def test_duplicate_fact_ids_are_rejected() -> None:
    package = _valid_package()
    package["facts"]["facts"].append(copy.deepcopy(package["facts"]["facts"][0]))

    result = validate_package(package)

    assert not result.passed
    assert any("unique" in finding.message for finding in result.errors)


# --- Reachability ------------------------------------------------------------


def test_a_fact_no_phase_can_release_is_rejected() -> None:
    """Dead content: the runtime will never surface it and never complains."""
    package = _valid_package()
    package["facts"]["facts"][1]["release_level"] = "synthesis_support"

    result = validate_package(package)

    assert not result.passed
    assert any(finding.check == "reachability" for finding in result.errors)
    assert any("no phase permits" in finding.message for finding in result.errors)


def test_an_interviewer_only_fact_is_exempt_from_reachability() -> None:
    """The hidden diagnosis is meant to be unreachable by the candidate."""
    package = _valid_package()
    package["facts"]["facts"].append(
        {
            "id": "diagnosis.hidden",
            "domain": "diagnosis",
            "release_level": "interviewer_only",
            "content": "The hidden driver is the mix shift.",
        }
    )

    result = validate_package(package)

    assert result.passed, [f.message for f in result.errors]


def test_a_policy_with_no_phases_is_rejected() -> None:
    package = _valid_package()
    package["conversation_policy"]["phase_policy"] = {}

    result = validate_package(package)

    assert not result.passed
    assert any(finding.check == "reachability" for finding in result.errors)


# --- Arithmetic closure ------------------------------------------------------


def test_numbers_that_do_not_close_are_rejected() -> None:
    """The check the whole gate exists for."""
    package = _valid_package()
    package["facts"]["facts"][3]["numeric_value"] = 7.5  # formula computes 0

    result = validate_package(package)

    assert not result.passed
    failure = next(f for f in result.errors if f.check == "arithmetic")
    assert "do not close" in failure.message
    assert "7.5" in failure.message


def test_a_zero_expected_value_still_validates_correctly() -> None:
    """Zero contribution margin is a real answer, not a missing one."""
    package = _valid_package()

    result = validate_package(package)

    assert result.passed
    assert package["facts"]["facts"][3]["numeric_value"] == 0.0


def test_a_formula_referencing_an_unmapped_name_is_rejected() -> None:
    package = _valid_package()
    package["facts"]["facts"][3]["formula"] = "rate - cost - overhead"

    result = validate_package(package)

    assert not result.passed
    assert any("overhead" in finding.message for finding in result.errors)


def test_a_formula_input_pointing_at_a_non_numeric_fact_is_rejected() -> None:
    package = _valid_package()
    package["facts"]["facts"][3]["depends_on"]["cost"] = "company.identity"

    result = validate_package(package)

    assert not result.passed
    assert any("numeric_value" in finding.message for finding in result.errors)


def test_an_unsafe_formula_is_rejected_rather_than_executed() -> None:
    package = _valid_package()
    package["facts"]["facts"][3]["formula"] = "__import__('os').system('echo pwned')"

    result = validate_package(package)

    assert not result.passed
    assert any(finding.check == "arithmetic" for finding in result.errors)


def test_a_quant_step_whose_expected_value_is_wrong_is_rejected() -> None:
    package = _valid_package()
    package["quant"] = {
        "quant_steps": [
            {
                "id": "quant.contribution",
                "intent": "Compute contribution per unit.",
                "kind": "unit_economics",
                "formula": "rate - cost",
                "inputs": {"rate": "economics.rate", "cost": "economics.cost"},
                "expected_value": 5.0,
                "unit": "per unit",
            }
        ]
    }

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == "quant.contribution" for finding in result.errors)


def test_a_correct_quant_step_passes() -> None:
    package = _valid_package()
    package["quant"] = {
        "quant_steps": [
            {
                "id": "quant.contribution",
                "intent": "Compute contribution per unit.",
                "kind": "unit_economics",
                "formula": "rate - cost",
                "inputs": {"rate": "economics.rate", "cost": "economics.cost"},
                "expected_value": 0.0,
                "unit": "per unit",
            }
        ]
    }

    result = validate_package(package)

    assert result.passed, [f.message for f in result.errors]


def test_a_case_with_no_quantitative_surface_is_perfectly_valid() -> None:
    """Quant is optional per case, permanently. Its absence is not a defect."""
    package = _valid_package()
    package["facts"]["facts"] = package["facts"]["facts"][:1]

    result = validate_package(package)

    assert result.passed, [f.message for f in result.errors]


# --- Safety ------------------------------------------------------------------


@pytest.mark.parametrize(
    "leak",
    [
        "Contact the CEO at priya.sharma@example.com for details.",
        "The founder's number is 9876543210.",
        "See linkedin.com/in/some-candidate for background.",
        "Full deck at https://drive.example.com/deck",
    ],
)
def test_personal_data_anywhere_in_the_package_is_rejected(leak: str) -> None:
    """Checked over every nested string, so a buried field cannot slip through."""
    package = _valid_package()
    package["facts"]["facts"][0]["content"] = leak

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == "personal_data" for finding in result.errors)


def test_a_real_organisation_surviving_the_reskin_is_rejected() -> None:
    """Re-skinning is the defensible position, and only holds if it is enforced."""
    package = _valid_package()
    package["case"]["case_essence"]["core_mechanism"] = "Reliance undercut the client on price."

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == "real_organisation" for finding in result.errors)


def test_the_safety_check_reads_deeply_nested_fields() -> None:
    package = _valid_package()
    package["case"]["case_essence"]["common_traps"].append("Email ops@realco.com to confirm.")

    result = validate_package(package)

    assert not result.passed
    assert any(finding.target == "personal_data" for finding in result.errors)


# --- Verdict shape -----------------------------------------------------------


def test_warnings_do_not_block_publication() -> None:
    """Warnings are for the admin's judgement; only errors are the gate's."""
    package = _valid_package()
    package["quant"] = {
        "quant_steps": [
            {"id": "quant.freeform", "intent": "Estimate the market.", "kind": "market_sizing"}
        ]
    }

    result = validate_package(package)

    assert result.passed
    assert result.warnings
    assert any(finding.target == "quant.freeform" for finding in result.warnings)


def test_the_verdict_serialises_for_the_admin_console() -> None:
    package = _valid_package()
    package["facts"]["facts"][3]["numeric_value"] = 99.0

    payload = validate_package(package).as_dict()

    assert payload["passed"] is False
    assert payload["error_count"] >= 1
    assert payload["findings"][0]["check"]
    assert payload["findings"][0]["message"]
