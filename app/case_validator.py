"""The gate every contributed case must pass before a candidate can play it.

A broken case is worse than no case. Someone spends thirty minutes on a world
whose numbers do not reconcile or whose diagnosis does not follow, and they do
not blame the contributor, they blame Leo. So the gate runs automatically on
submission and its verdict is recorded with the package.

Six checks, in cost order so the cheap structural ones fail fast before anything
reaches a model:

1. **Schema** - the package parses into the authored models at all.
2. **Dependency graph** - no cycles, no dangling references.
3. **Reachability** - every fact can actually be released by some phase. This
   catches a real and currently undetectable class of defect: an authored fact
   whose release level appears in no phase is dead content that no candidate can
   ever earn, and nothing in the runtime complains.
4. **Arithmetic closure** - derived facts and quantitative steps recompute from
   their own formulas. Decided in code, never by a model, because multi-constraint
   numeric closure is exactly where models produce confident wrong numbers.
5. **Safety** - personal data and real company names.
6. **Solvability** - the case is played headlessly and must reach its own stated
   diagnosis from released evidence alone.

Checks 1 to 5 are deterministic and run here. Check 6 needs a model and a live
runtime, so it lives in :mod:`app.case_solver` and is invoked separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import ValidationError

from app.expressions import ExpressionError, evaluate, referenced_names
from app.models import CaseManifest, FactsPackage, QuantPackage
from app.personas import RELEASE_LEVEL_LADDER


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    """One thing wrong with a contributed package."""

    check: str
    severity: Severity
    message: str
    target: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "target": self.target,
        }


@dataclass
class ValidationResult:
    """The gate's verdict, stored alongside the package for the admin to read."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def passed(self) -> bool:
        """Warnings do not block. They are for the admin's judgement, not the gate's."""
        return not self.errors

    def add(self, check: str, severity: Severity, message: str, target: str = "") -> None:
        self.findings.append(Finding(check, severity, message, target))

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [finding.as_dict() for finding in self.findings],
        }


# Fields without which a case has no teeth. A contributor remembers that a case
# was hard; they do not spontaneously volunteer what made it hard. If extraction
# does not hunt for these, the result is a technically valid case that feels like
# every other one, which is the failure mode that actually kills a crowdsourced
# corpus. Blocking here is what forces the extraction agent to go and get them.
REQUIRED_ESSENCE_FIELDS = ("core_mechanism", "pivotal_insight", "takeaway_lesson")
MINIMUM_TRAPS = 2

# Deliberately narrow. A broad name list would fire on ordinary business nouns and
# train the admin to ignore the check.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s-]?)?\d{10}(?!\d)")
_LINKEDIN = re.compile(r"linkedin\.com/in/[\w-]+", re.IGNORECASE)
_URL = re.compile(r"https?://\S+")

# Real firms a recalled case might name. Contributed cases are re-skinned by the
# synthesis pass, so any of these surviving into the package is a signal that the
# re-skin did not happen rather than a naming coincidence.
_REAL_ORGANISATIONS = (
    "mckinsey",
    "bain & company",
    "boston consulting",
    "accenture",
    "deloitte",
    "reliance",
    "tata ",
    "adani",
    "infosys",
    "flipkart",
    "swiggy",
    "zomato",
    "amazon",
    "unilever",
)


def validate_package(package: dict[str, Any]) -> ValidationResult:
    """Run every deterministic check over a stored package payload."""
    result = ValidationResult()

    manifest = _check_schema(package, result)
    if manifest is None:
        # Nothing downstream can be trusted once the shape is wrong, and cascading
        # errors from a malformed package would bury the one that matters.
        return result

    facts = _facts_of(package, result)
    _check_essence(manifest, result)
    _check_dependencies(facts, result)
    _check_reachability(package, facts, result)
    _check_arithmetic(facts, package, result)
    _check_safety(package, result)
    return result


# --- 1. Schema ---------------------------------------------------------------


def _check_schema(package: dict[str, Any], result: ValidationResult) -> CaseManifest | None:
    case_data = package.get("case")
    if not isinstance(case_data, dict):
        result.add("schema", "error", "Package has no 'case' section")
        return None
    try:
        manifest = CaseManifest.model_validate(case_data)
    except ValidationError as error:
        for problem in error.errors()[:10]:
            location = ".".join(str(part) for part in problem["loc"])
            result.add("schema", "error", problem["msg"], location)
        return None

    if not isinstance(package.get("facts"), dict):
        result.add("schema", "error", "Package has no 'facts' section")
        return None
    if not isinstance(package.get("conversation_policy"), dict):
        result.add("schema", "error", "Package has no 'conversation_policy' section")
        return None
    return manifest


def _facts_of(package: dict[str, Any], result: ValidationResult) -> FactsPackage:
    try:
        return FactsPackage.model_validate(package.get("facts") or {})
    except ValidationError as error:
        for problem in error.errors()[:10]:
            result.add(
                "schema", "error", problem["msg"], ".".join(str(p) for p in problem["loc"])
            )
        return FactsPackage()


def _check_essence(manifest: CaseManifest, result: ValidationResult) -> None:
    essence = manifest.case_essence
    for field_name in REQUIRED_ESSENCE_FIELDS:
        if not str(getattr(essence, field_name, "") or "").strip():
            result.add(
                "essence",
                "error",
                f"case_essence.{field_name} is empty. Without it the case has no teachable core.",
                field_name,
            )
    if len(essence.common_traps) < MINIMUM_TRAPS:
        result.add(
            "essence",
            "error",
            (
                f"case_essence.common_traps needs at least {MINIMUM_TRAPS} entries. "
                "The traps are what make a case worth solving rather than merely valid."
            ),
            "common_traps",
        )


# --- 2. Dependency graph -----------------------------------------------------


def _check_dependencies(facts: FactsPackage, result: ValidationResult) -> None:
    known = {fact.id for fact in facts.facts}
    if len(known) != len(facts.facts):
        result.add("dependencies", "error", "Fact IDs must be unique within a case")

    for fact in facts.facts:
        for dependency in fact.dependencies:
            if dependency not in known:
                result.add(
                    "dependencies",
                    "error",
                    f"Fact depends on '{dependency}', which does not exist",
                    fact.id,
                )

    # Depth-first cycle detection. A cycle makes every fact in it permanently
    # unreachable, because each is waiting on another that is waiting on it.
    graph = {fact.id: [d for d in fact.dependencies if d in known] for fact in facts.facts}
    visiting: set[str] = set()
    settled: set[str] = set()

    def walk(node: str, trail: list[str]) -> None:
        if node in settled:
            return
        if node in visiting:
            cycle = " -> ".join(trail[trail.index(node):] + [node])
            result.add("dependencies", "error", f"Dependency cycle: {cycle}", node)
            return
        visiting.add(node)
        for child in graph.get(node, []):
            walk(child, trail + [node])
        visiting.discard(node)
        settled.add(node)

    for fact_id in graph:
        walk(fact_id, [])


# --- 3. Reachability ---------------------------------------------------------


def _check_reachability(
    package: dict[str, Any], facts: FactsPackage, result: ValidationResult
) -> None:
    """Every fact must be releasable by at least one phase.

    A fact whose release level appears in no phase is dead content. The runtime
    will never surface it, no candidate can earn it, and nothing anywhere reports
    the problem, so it can sit in an authored case indefinitely.
    """
    policy = package.get("conversation_policy") or {}
    phase_policy = policy.get("phase_policy") or {}
    if not phase_policy:
        result.add("reachability", "error", "Conversation policy declares no phases")
        return

    releasable: set[str] = set()
    for phase in phase_policy.values():
        if isinstance(phase, dict):
            releasable.update(phase.get("reveal_levels") or [])

    unknown_levels = releasable - set(RELEASE_LEVEL_LADDER)
    for level in sorted(unknown_levels):
        result.add(
            "reachability",
            "warning",
            f"Phase policy names release level '{level}', which the runtime ladder does not define",
            level,
        )

    for fact in facts.facts:
        if fact.release_level == "interviewer_only":
            continue
        if fact.release_level not in releasable:
            result.add(
                "reachability",
                "error",
                (
                    f"Fact has release level '{fact.release_level}', which no phase permits, "
                    "so no candidate can ever be shown it"
                ),
                fact.id,
            )


# --- 4. Arithmetic closure ---------------------------------------------------


def _check_arithmetic(
    facts: FactsPackage, package: dict[str, Any], result: ValidationResult
) -> None:
    """Recompute every stated number from its own formula.

    In code, never by a model. This is the check the whole gate exists for: a
    synthesis pass will happily produce fifteen mutually plausible numbers whose
    arithmetic does not close, and a candidate discovers that thirty minutes in.
    """
    numeric_by_id = {
        fact.id: fact.numeric_value for fact in facts.facts if fact.numeric_value is not None
    }

    for fact in facts.facts:
        if not fact.formula.strip():
            continue
        _recompute(
            check="arithmetic",
            target=fact.id,
            formula=fact.formula,
            inputs=fact.depends_on,
            expected=fact.numeric_value,
            numeric_by_id=numeric_by_id,
            result=result,
            what="Derived fact",
        )

    quant_data = package.get("quant")
    if not isinstance(quant_data, dict):
        return
    try:
        quant = QuantPackage.model_validate(quant_data)
    except ValidationError as error:
        for problem in error.errors()[:10]:
            result.add(
                "schema", "error", problem["msg"], ".".join(str(p) for p in problem["loc"])
            )
        return

    for step in quant.quant_steps:
        if not step.formula.strip():
            result.add(
                "arithmetic",
                "warning",
                "Quantitative step has no formula, so the candidate's answer cannot be graded in code",
                step.id,
            )
            continue
        _recompute(
            check="arithmetic",
            target=step.id,
            formula=step.formula,
            inputs=step.inputs,
            expected=step.expected_value,
            numeric_by_id=numeric_by_id,
            result=result,
            what="Quantitative step",
        )


def _recompute(
    *,
    check: str,
    target: str,
    formula: str,
    inputs: dict[str, str],
    expected: float | None,
    numeric_by_id: dict[str, float],
    result: ValidationResult,
    what: str,
) -> None:
    try:
        needed = referenced_names(formula)
    except ExpressionError as error:
        result.add(check, "error", f"{what} formula is invalid: {error}", target)
        return

    missing_mapping = sorted(needed - set(inputs))
    if missing_mapping:
        result.add(
            check,
            "error",
            f"{what} formula uses {', '.join(missing_mapping)} but maps no fact to them",
            target,
        )
        return

    values: dict[str, float] = {}
    for name in needed:
        fact_id = inputs[name]
        if fact_id not in numeric_by_id:
            result.add(
                check,
                "error",
                f"{what} input '{name}' points at '{fact_id}', which carries no numeric_value",
                target,
            )
            return
        values[name] = numeric_by_id[fact_id]

    try:
        computed = evaluate(formula, values)
    except ExpressionError as error:
        result.add(check, "error", f"{what} formula does not compute: {error}", target)
        return

    if expected is None:
        result.add(
            check,
            "warning",
            f"{what} has a formula but no expected value to check it against",
            target,
        )
        return

    # A relative comparison, because these are business quantities at wildly
    # different scales. The tolerance is for floating point, not for sloppiness.
    scale = max(abs(computed), abs(expected), 1e-9)
    if abs(computed - expected) / scale > 1e-6:
        result.add(
            check,
            "error",
            (
                f"{what} states {expected:g} but its own formula computes {computed:g}. "
                "The case's numbers do not close."
            ),
            target,
        )


# --- 5. Safety ---------------------------------------------------------------


def _all_text(value: Any) -> list[str]:
    """Every string anywhere in the package, so a check cannot miss a nested field."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _all_text(item)]
    if isinstance(value, list):
        return [text for item in value for text in _all_text(item)]
    return []


def _check_safety(package: dict[str, Any], result: ValidationResult) -> None:
    """Personal data and un-reskinned real organisations.

    Contributed cases are always re-skinned by the synthesis pass rather than
    published verbatim. That is the defensible position on recalled interview
    content, and it only holds if it is enforced rather than assumed.
    """
    texts = _all_text(package)
    joined = "\n".join(texts)
    lowered = joined.lower()

    for label, pattern in (
        ("an email address", _EMAIL),
        ("a phone number", _PHONE),
        ("a LinkedIn profile", _LINKEDIN),
        ("a URL", _URL),
    ):
        match = pattern.search(joined)
        if match:
            result.add(
                "safety",
                "error",
                f"Package contains what looks like {label}: {match.group()[:60]}",
                "personal_data",
            )

    for organisation in _REAL_ORGANISATIONS:
        if organisation in lowered:
            result.add(
                "safety",
                "error",
                (
                    f"Package names a real organisation ({organisation.strip()}). "
                    "Contributed cases must be re-skinned, never published verbatim."
                ),
                "real_organisation",
            )
