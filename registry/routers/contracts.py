from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from registry.database import get_db
from registry.models import ContractRecord
from registry.schemas import ContractDetail, ContractPublishRequest, ContractSummary

router = APIRouter()


@router.post("/", status_code=201, response_model=ContractSummary)
def publish_contract(req: ContractPublishRequest, db: Session = Depends(get_db)):
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
    record = (
        db.query(ContractRecord)
        .filter(ContractRecord.name == name, ContractRecord.is_current.is_(True))
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail=f'Contract "{name}" not found')
    record.content = json.loads(record.content)  # type: ignore[assignment]
    return record


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
    record = (
        db.query(ContractRecord)
        .filter(ContractRecord.name == name, ContractRecord.version == version)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail=f'Contract "{name}" v{version} not found')
    record.content = json.loads(record.content)  # type: ignore[assignment]
    return record
