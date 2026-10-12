from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from backend.rules.models import RuleSet, ComplianceRule, PrecheckResult
from backend.rules.engine import rule_engine
from backend.rules.precheck import run_deterministic_precheck

router = APIRouter(prefix="/api/rules", tags=["Rules Engine"])


class CreateVersionRequest(BaseModel):
    version: str
    updated_rules: List[ComplianceRule]
    description: Optional[str] = None


class PrecheckRequest(BaseModel):
    candidate_text: str
    rule_id: str
    ruleset_id: Optional[str] = "ruleset-nda-commercial"
    version: Optional[str] = None


@router.get("/sets", response_model=List[RuleSet])
async def list_rule_sets():
    """List all registered compliance rule sets (latest active versions)."""
    return rule_engine.list_rule_sets()


@router.get("/sets/{ruleset_id}", response_model=RuleSet)
async def get_rule_set(ruleset_id: str, version: Optional[str] = None):
    """Get a compliance rule set by ID, optionally specifying version."""
    return rule_engine.get_rule_set(ruleset_id, version=version)


@router.get("/sets/{ruleset_id}/versions", response_model=List[str])
async def list_rule_set_versions(ruleset_id: str):
    """List all available version tags for a given rule set."""
    return rule_engine.list_versions_for_set(ruleset_id)


@router.post("/sets/{ruleset_id}/version", response_model=RuleSet, status_code=status.HTTP_201_CREATED)
async def publish_rule_set_version(ruleset_id: str, body: CreateVersionRequest):
    """Publish a new immutable version of a rule set without overwriting past versions."""
    return rule_engine.create_new_version(
        ruleset_id=ruleset_id,
        new_version=body.version,
        updated_rules=body.updated_rules,
        description=body.description
    )


@router.post("/precheck", response_model=PrecheckResult)
async def execute_rule_precheck(body: PrecheckRequest):
    """Run deterministic regex / numeric pre-check against candidate text for a rule."""
    ruleset = rule_engine.get_rule_set(body.ruleset_id or "ruleset-nda-commercial", version=body.version)
    target_rule = next((r for r in ruleset.rules if r.id == body.rule_id or r.code == body.rule_id), None)
    if not target_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{body.rule_id}' not found in rule set '{ruleset.id}'."
        )
    return run_deterministic_precheck(candidate_text=body.candidate_text, rule=target_rule)
