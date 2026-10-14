"""
Feature 4: Custom Rule Studio & Ruleset Importer.

Provides CRUD operations and YAML/JSON import for custom compliance rules and
rulesets. Users can define domain-specific rules (e.g., SOC-2, HIPAA, custom
NDA clauses) without modifying code. Rules are persisted to the uploads dir
as JSON files and hot-loaded into the rule engine registry.
"""

import json
import logging
import os
import uuid
from datetime import UTC, datetime

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from pydantic import BaseModel, Field, ValidationError

from backend.app.config import settings
from backend.rules.models import ComplianceRule, RuleSet, RuleType, Severity

logger = logging.getLogger(__name__)

STUDIO_DIR = os.path.join(settings.UPLOAD_DIR, ".studio")


def _ensure_studio_dir() -> None:
    os.makedirs(STUDIO_DIR, exist_ok=True)


def _ruleset_path(ruleset_id: str) -> str:
    return os.path.join(STUDIO_DIR, f"{ruleset_id}.json")


# -- In-memory registry --------------------------------------------------------
_custom_rulesets: dict[str, RuleSet] = {}


def _load_all_custom_rulesets() -> None:
    """Load all persisted custom rulesets from disk into memory on startup."""
    _ensure_studio_dir()
    for fname in os.listdir(STUDIO_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(STUDIO_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            ruleset = RuleSet.model_validate(data)
            _custom_rulesets[ruleset.id] = ruleset
            logger.info("Loaded custom ruleset: %s v%s (%d rules)", ruleset.id, ruleset.version, len(ruleset.rules))
        except Exception as exc:
            logger.warning("Failed to load custom ruleset from %s: %s", path, exc)


_load_all_custom_rulesets()


# -- Public API ----------------------------------------------------------------


class CreateRuleRequest(BaseModel):
    """Request body for creating a single custom compliance rule."""

    code: str = Field(..., min_length=2, max_length=32, pattern=r"^[A-Z0-9_\-]+$")
    name: str = Field(..., min_length=3, max_length=128)
    description: str
    rule_type: RuleType
    severity: Severity
    applicable_document_types: list[str] = Field(default_factory=lambda: ["NDA"])
    deterministic_regex: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    guidance: str | None = None
    prohibited_terms: list[str] | None = None
    required_elements: list[str] | None = None
    max_threshold: float | None = None
    approved_values: list[str] | None = None


class CreateRulesetRequest(BaseModel):
    """Request body for creating a full custom ruleset."""

    name: str
    version: str = "1.0.0"
    description: str
    document_type: str = "NDA"
    rules: list[CreateRuleRequest] = Field(default_factory=list)


def create_custom_ruleset(req: CreateRulesetRequest) -> RuleSet:
    """Create and persist a new custom ruleset."""
    ruleset_id = f"ruleset-custom-{uuid.uuid4().hex[:8]}"
    rules = [_make_rule(ruleset_id, r) for r in req.rules]
    ruleset = RuleSet(
        id=ruleset_id,
        name=req.name,
        version=req.version,
        description=req.description,
        document_type=req.document_type,
        rules=rules,
        is_default=False,
    )
    _persist_ruleset(ruleset)
    return ruleset


def add_rule_to_ruleset(ruleset_id: str, req: CreateRuleRequest) -> RuleSet:
    """Add a new rule to an existing custom ruleset."""
    ruleset = get_custom_ruleset(ruleset_id)
    new_rule = _make_rule(ruleset_id, req)
    ruleset.rules.append(new_rule)
    ruleset.updated_at = datetime.now(UTC).isoformat()  # type: ignore[attr-defined]
    _persist_ruleset(ruleset)
    return ruleset


def delete_rule_from_ruleset(ruleset_id: str, rule_code: str) -> RuleSet:
    """Remove a rule by code from a custom ruleset."""
    ruleset = get_custom_ruleset(ruleset_id)
    before = len(ruleset.rules)
    ruleset.rules = [r for r in ruleset.rules if r.code != rule_code]
    if len(ruleset.rules) == before:
        raise KeyError(f"Rule '{rule_code}' not found in ruleset '{ruleset_id}'.")
    _persist_ruleset(ruleset)
    return ruleset


def import_ruleset_from_yaml(yaml_text: str) -> RuleSet:
    """Parse a YAML-encoded ruleset and persist it."""
    if not YAML_AVAILABLE:
        raise RuntimeError("PyYAML is not installed. Add 'pyyaml' to dependencies.")
    data = yaml.safe_load(yaml_text)
    return _import_from_dict(data)


def import_ruleset_from_json(json_text: str) -> RuleSet:
    """Parse a JSON-encoded ruleset and persist it."""
    data = json.loads(json_text)
    return _import_from_dict(data)


def get_custom_ruleset(ruleset_id: str) -> RuleSet:
    if ruleset_id not in _custom_rulesets:
        raise KeyError(f"Custom ruleset '{ruleset_id}' not found.")
    return _custom_rulesets[ruleset_id]


def list_custom_rulesets() -> list[RuleSet]:
    return list(_custom_rulesets.values())


def delete_custom_ruleset(ruleset_id: str) -> None:
    if ruleset_id not in _custom_rulesets:
        raise KeyError(f"Custom ruleset '{ruleset_id}' not found.")
    del _custom_rulesets[ruleset_id]
    path = _ruleset_path(ruleset_id)
    if os.path.exists(path):
        os.remove(path)


# -- Helpers -------------------------------------------------------------------


def _make_rule(ruleset_id: str, req: CreateRuleRequest) -> ComplianceRule:
    from backend.rules.models import RuleParameters

    params = RuleParameters(
        prohibited_terms=req.prohibited_terms,
        required_elements=req.required_elements,
        max_threshold=req.max_threshold,
        approved_values=req.approved_values,
    )
    return ComplianceRule(
        id=f"rule-custom-{uuid.uuid4().hex[:8]}",
        code=req.code,
        name=req.name,
        rule_set_id=ruleset_id,
        description=req.description,
        rule_type=req.rule_type,
        severity=req.severity,
        applicable_document_types=req.applicable_document_types,
        deterministic_regex=req.deterministic_regex,
        search_queries=req.search_queries,
        guidance=req.guidance,
        parameters=params,
    )


def _persist_ruleset(ruleset: RuleSet) -> None:
    _ensure_studio_dir()
    _custom_rulesets[ruleset.id] = ruleset
    path = _ruleset_path(ruleset.id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ruleset.model_dump(), f, indent=2)
    logger.info("Persisted custom ruleset: %s", ruleset.id)


def _import_from_dict(data: dict) -> RuleSet:
    """Validate and import a raw dict as a RuleSet."""
    try:
        # Assign a new ID to prevent collisions on import
        if "id" not in data or not data["id"].startswith("ruleset-custom-"):
            data["id"] = f"ruleset-custom-{uuid.uuid4().hex[:8]}"
        ruleset = RuleSet.model_validate(data)
        _persist_ruleset(ruleset)
        return ruleset
    except ValidationError as exc:
        raise ValueError(f"Invalid ruleset format: {exc}") from exc
