"""
API router for Feature 4: Custom Rule Studio & Ruleset Importer.

Provides full CRUD for custom compliance rulesets and rules, plus YAML/JSON
import. Users can build domain-specific rulesets (HIPAA, SOC-2, custom NDA)
without touching source code, then run compliance checks against them via the
standard /api/checks/run endpoint with the custom ruleset_id.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from backend.rules.models import RuleSet
from backend.rules.studio import (
    CreateRuleRequest,
    CreateRulesetRequest,
    add_rule_to_ruleset,
    create_custom_ruleset,
    delete_custom_ruleset,
    delete_rule_from_ruleset,
    get_custom_ruleset,
    import_ruleset_from_json,
    import_ruleset_from_yaml,
    list_custom_rulesets,
)

router = APIRouter(prefix="/api/studio", tags=["Custom Rule Studio"])


@router.get("/rulesets", response_model=list[RuleSet])
async def list_rulesets():
    """List all custom user-defined rulesets."""
    return list_custom_rulesets()


@router.post("/rulesets", response_model=RuleSet, status_code=status.HTTP_201_CREATED)
async def create_ruleset(body: CreateRulesetRequest):
    """Create a new custom ruleset with an optional initial set of rules."""
    return create_custom_ruleset(body)


@router.get("/rulesets/{ruleset_id}", response_model=RuleSet)
async def get_ruleset(ruleset_id: str):
    """Retrieve a specific custom ruleset by ID."""
    try:
        return get_custom_ruleset(ruleset_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/rulesets/{ruleset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ruleset(ruleset_id: str):
    """Permanently delete a custom ruleset and all its rules."""
    try:
        delete_custom_ruleset(ruleset_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/rulesets/{ruleset_id}/rules", response_model=RuleSet, status_code=status.HTTP_201_CREATED)
async def add_rule(ruleset_id: str, body: CreateRuleRequest):
    """Add a new rule to an existing custom ruleset."""
    try:
        return add_rule_to_ruleset(ruleset_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/rulesets/{ruleset_id}/rules/{rule_code}", response_model=RuleSet)
async def delete_rule(ruleset_id: str, rule_code: str):
    """Remove a rule by code from a custom ruleset."""
    try:
        return delete_rule_from_ruleset(ruleset_id, rule_code)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/rulesets/import/yaml", response_model=RuleSet, status_code=status.HTTP_201_CREATED)
async def import_yaml_ruleset(file: UploadFile = File(...)):
    """
    Import a ruleset from a YAML file.

    Expected schema mirrors the RuleSet Pydantic model. Example:
    ```yaml
    name: My HIPAA Ruleset
    version: "1.0.0"
    description: HIPAA-specific clause requirements
    document_type: Business Associate Agreement
    rules:
      - code: HIPAA-01
        name: PHI Handling Clause
        description: BAA must contain explicit PHI handling procedures
        rule_type: required_clause
        severity: critical
        required_elements:
          - protected health information
          - safeguards
    ```
    """
    content = await file.read()
    try:
        ruleset = import_ruleset_from_yaml(content.decode("utf-8"))
        return ruleset
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/rulesets/import/json", response_model=RuleSet, status_code=status.HTTP_201_CREATED)
async def import_json_ruleset(file: UploadFile = File(...)):
    """Import a ruleset from a JSON file that matches the RuleSet schema."""
    content = await file.read()
    try:
        ruleset = import_ruleset_from_json(content.decode("utf-8"))
        return ruleset
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
