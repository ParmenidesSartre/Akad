from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from akad.differ import DiffSeverity, diff_contracts
from akad.models.contract import DataContract
from registry.database import get_db
from registry.models import ContractRecord
from registry.schemas import ContractDetail, ContractPublishRequest, ContractSummary

router = APIRouter()


def _get_or_404(db: Session, *filters: Any, detail: str) -> ContractRecord:
    record = db.query(ContractRecord).filter(*filters).first()
    if not record:
        raise HTTPException(status_code=404, detail=detail)
    record.content = json.loads(record.content)  # type: ignore[assignment]
    return record


def _breaking_changes(old_content: dict[str, Any], new_content: dict[str, Any]) -> list[dict[str, str]]:
    """Diff two raw contract dicts, returning only the breaking changes.

    Either side failing to parse as a DataContract degrades gracefully —
    skips the check rather than blocking a publish over unrelated bad data
    (e.g. a malformed historical record that predates schema validation).
    """
    try:
        old = DataContract.model_validate(old_content)
        new = DataContract.model_validate(new_content)
    except ValidationError:
        return []
    return [
        {"path": e.path, "message": e.message}
        for e in diff_contracts(old, new)
        if e.severity == DiffSeverity.BREAKING
    ]


@router.post("/", status_code=201, response_model=ContractSummary)
def publish_contract(req: ContractPublishRequest, db: Session = Depends(get_db)):
    current = db.query(ContractRecord).filter(
        ContractRecord.name == req.name,
        ContractRecord.is_current.is_(True),
    ).first()

    if current is not None and not req.force:
        breaking = _breaking_changes(json.loads(current.content), req.content)
        if breaking:
            raise HTTPException(status_code=409, detail={
                "message": (
                    f'Publishing "{req.name}" v{req.version} would introduce '
                    f"{len(breaking)} breaking change(s) relative to the current "
                    f"v{current.version}. Pass force=true to publish anyway."
                ),
                "breaking_changes": breaking,
            })

    # Mark all previous versions of this contract as not current
    db.query(ContractRecord).filter(
        ContractRecord.name == req.name,
        ContractRecord.is_current.is_(True),
    ).update({"is_current": False})

    record = ContractRecord(
        name=req.name,
        version=req.version,
        content=json.dumps(req.content),
        is_current=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[ContractSummary])
def list_contracts(db: Session = Depends(get_db)):
    return db.query(ContractRecord).filter(ContractRecord.is_current.is_(True)).all()


@router.get("/{name}", response_model=ContractDetail)
def get_contract(name: str, db: Session = Depends(get_db)):
    return _get_or_404(
        db, ContractRecord.name == name, ContractRecord.is_current.is_(True),
        detail=f'Contract "{name}" not found',
    )


@router.get("/{name}/versions", response_model=list[ContractSummary])
def list_versions(name: str, db: Session = Depends(get_db)):
    return (
        db.query(ContractRecord)
        .filter(ContractRecord.name == name)
        .order_by(ContractRecord.published_at.desc())
        .all()
    )


@router.get("/{name}/versions/{version}", response_model=ContractDetail)
def get_version(name: str, version: str, db: Session = Depends(get_db)):
    return _get_or_404(
        db, ContractRecord.name == name, ContractRecord.version == version,
        detail=f'Contract "{name}" v{version} not found',
    )
