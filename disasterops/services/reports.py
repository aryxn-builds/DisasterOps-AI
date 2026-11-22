from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Account, CitizenSafety, Incident, RescueAssignment, SOSReport, now
from ..schemas import SOS


def commit_unique(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail) from None


def save_safety(db: Session, citizen: Account, status: str) -> CitizenSafety:
    db.execute(select(Account.id).where(Account.id == citizen.id).with_for_update())
    checkin = db.get(CitizenSafety, citizen.id)
    if checkin is None:
        checkin = CitizenSafety(account_id=citizen.id)
        db.add(checkin)
    checkin.status = status
    checkin.updated_at = now()
    db.commit()
    return checkin


def record_sos(db: Session, citizen: Account, request: SOS) -> SOSReport:
    key = str(request.request_id)
    fields = request.model_dump(exclude={"request_id"})
    lookup = select(SOSReport).where(
        SOSReport.account_id == citizen.id, SOSReport.client_request_id == key
    )
    report = db.scalar(lookup)
    if not report:
        report = SOSReport(
            account_id=citizen.id, client_request_id=key, phone=citizen.phone, **fields
        )
        db.add(report)
        try:
            db.commit()
            return report
        except IntegrityError:
            db.rollback()
            report = db.scalar(lookup)
            if report is None:
                raise
    if any(getattr(report, key) != value for key, value in fields.items()):
        raise HTTPException(409, "Request ID already used with different report data")
    return report


def report_view(report: SOSReport, *, include_contact: bool = False) -> dict:
    data = {
        "id": report.id,
        "source": report.source,
        "received_at": report.received_at,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "accuracy_meters": report.accuracy_meters,
        "battery_percentage": report.battery_percentage,
        "message": report.message,
    }
    if include_contact:
        data["phone"] = report.phone
    return data


def assignment_view(assignment: RescueAssignment) -> dict:
    return {
        "id": assignment.id,
        "incident_id": assignment.incident_id,
        "status": "CONFIRMED" if assignment.confirmed_at else "PENDING",
        "confirmed_at": assignment.confirmed_at,
    }


def get_workflow(db: Session, report_id: str) -> dict:
    incident = db.scalar(select(Incident).where(Incident.report_id == report_id))
    if not incident:
        return {"incident_id": None, "assignment": None}
    assignment = db.scalar(
        select(RescueAssignment).where(RescueAssignment.incident_id == incident.id)
    )
    return {
        "incident_id": incident.id,
        "assignment": assignment_view(assignment) if assignment else None,
    }
