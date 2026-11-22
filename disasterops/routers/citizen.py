from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..db import DB
from ..models import SOSReport
from ..schemas import SOS, Safety
from ..services.auth import Citizen
from ..services.reports import get_workflow, record_sos, report_view, save_safety

router = APIRouter(prefix="/citizen", tags=["citizen"])


@router.put("/safety")
def update_safety(data: Safety, db: DB, citizen: Citizen):
    checkin = save_safety(db, citizen, data.status)
    return {"status": checkin.status, "updated_at": checkin.updated_at}


@router.post("/sos", status_code=201)
def submit_sos(data: SOS, db: DB, citizen: Citizen):
    report = record_sos(db, citizen, data)
    return {
        "status": "acknowledged",
        "report_id": report.id,
        "received_at": report.received_at,
    }


@router.get("/sos")
def list_own_reports(db: DB, citizen: Citizen, offset: Annotated[int, Query(ge=0)] = 0):
    reports = db.scalars(
        select(SOSReport)
        .where(SOSReport.account_id == citizen.id)
        .order_by(SOSReport.received_at.desc(), SOSReport.id)
        .offset(offset)
        .limit(50)
    )
    return [report_view(report) | get_workflow(db, report.id) for report in reports]


@router.get("/sos/{report_id}")
def get_own_report(report_id: UUID, db: DB, citizen: Citizen):
    report = db.scalar(
        select(SOSReport).where(
            SOSReport.id == str(report_id), SOSReport.account_id == citizen.id
        )
    )
    if report is None:
        raise HTTPException(404, "Report not found")
    return report_view(report) | get_workflow(db, report.id)
