from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from ..db import DB
from ..models import (
    Account,
    Incident,
    LocationRequest,
    RescueAssignment,
    SOSReport,
    now,
)
from ..schemas import Assign, OpenIncident
from ..services.auth import Dispatcher, Responder
from ..services.reports import assignment_view, commit_unique, get_workflow, report_view

router = APIRouter(prefix="/rescue", tags=["rescue"])


@router.get("/reports")
def review_reports(
    db: DB, dispatcher: Dispatcher, offset: Annotated[int, Query(ge=0)] = 0
):
    reports = db.scalars(
        select(SOSReport)
        .order_by(SOSReport.received_at.desc(), SOSReport.id)
        .offset(offset)
        .limit(50)
    ).all()
    current_request = {}
    rows = db.execute(
        select(LocationRequest.report_id, LocationRequest.id)
        .where(
            LocationRequest.requested_by == dispatcher.id,
            LocationRequest.report_id.in_([report.id for report in reports]),
        )
        .order_by(LocationRequest.expires_at.desc())
    )
    for report_id, request_id in rows:
        current_request.setdefault(report_id, request_id)
    return [
        report_view(report, include_contact=True)
        | get_workflow(db, report.id)
        | {"location_request_id": current_request.get(report.id)}
        for report in reports
    ]


@router.post("/incidents", status_code=201)
def open_incident(data: OpenIncident, db: DB, dispatcher: Dispatcher):
    report = db.get(SOSReport, str(data.report_id))
    if report is None:
        raise HTTPException(404, "Report not found")
    incident = Incident(report_id=report.id, opened_by=dispatcher.id)
    db.add(incident)
    commit_unique(db, "An incident already exists for this report")
    return {"id": incident.id, "report_id": incident.report_id}


@router.post("/incidents/{incident_id}/assignments", status_code=201)
def assign(incident_id: UUID, data: Assign, db: DB, dispatcher: Dispatcher):
    incident = db.get(Incident, str(incident_id))
    if incident is None:
        raise HTTPException(404, "Incident not found")
    responder = db.scalar(
        select(Account).where(
            Account.username == data.responder_username, Account.role == "responder"
        )
    )
    if responder is None:
        raise HTTPException(404, "Responder not found")
    assignment = RescueAssignment(
        incident_id=incident.id, responder_id=responder.id, assigned_by=dispatcher.id
    )
    db.add(assignment)
    commit_unique(db, "An assignment already exists for this incident")
    return assignment_view(assignment)


@router.get("/assignments")
def my_assignments(
    db: DB, responder: Responder, offset: Annotated[int, Query(ge=0)] = 0
):
    rows = db.execute(
        select(RescueAssignment, SOSReport)
        .join_from(
            RescueAssignment, Incident, RescueAssignment.incident_id == Incident.id
        )
        .join_from(Incident, SOSReport, Incident.report_id == SOSReport.id)
        .where(RescueAssignment.responder_id == responder.id)
        .order_by(RescueAssignment.assigned_at.desc(), RescueAssignment.id)
        .offset(offset)
        .limit(50)
    )
    return [
        assignment_view(assignment)
        | {"report": report_view(report, include_contact=True)}
        for assignment, report in rows
    ]


@router.post("/assignments/{assignment_id}/confirm")
def confirm(assignment_id: UUID, db: DB, responder: Responder):
    assignment = db.scalar(
        select(RescueAssignment)
        .where(
            RescueAssignment.id == str(assignment_id),
            RescueAssignment.responder_id == responder.id,
        )
        .with_for_update()
    )
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    if assignment.confirmed_at is None:
        assignment.confirmed_at = now()
        db.commit()
    return assignment_view(assignment)
