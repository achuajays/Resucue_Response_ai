from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from models import MedicalCase, Notification
from database import get_db
import json

router = APIRouter()

@router.get("/", response_class=HTMLResponse, summary="View Medical Dashboard", description="Displays all cases in HTML.")
def display_dashboard(db: Session = Depends(get_db)):
    emergency_cases = db.query(MedicalCase).filter(MedicalCase.is_emergency == True).all()
    non_emergency_cases = db.query(MedicalCase).filter(MedicalCase.is_emergency == False).all()
    notifications = db.query(Notification).all()
    html_content = """
    <html>
        <head>
            <title>Medical Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .section { background: #fff; padding: 20px; border-radius: 8px; }
                .case-item { margin: 10px 0; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .emergency { background: #ffe6e6; border-left: 4px solid #ff4444; }
                .non-emergency { background: #e6ffe6; border-left: 4px solid #44ff44; }
                .case-header { display: flex; justify-content: space-between; }
                .severity { padding: 3px 8px; border-radius: 4px; font-weight: bold; }
                .severity-HIGH, .severity-CRITICAL { background: #ff4444; color: white; }
                .severity-MEDIUM { background: #ffaa44; color: white; }
                .severity-LOW { background: #44ff44; color: white; }
                pre { white-space: pre-wrap; }
            </style>
        </head>
        <body>
            <h1>Medical Dashboard</h1>
            <div class="dashboard">
    """
    html_content += "<div class='section'><h2>Emergency Cases</h2>"
    for case in emergency_cases:
        severity = case.analysis.get("severity_level", "UNKNOWN")
        html_content += f"""
            <div class='case-item emergency'>
                <div class='case-header'>
                    <span>Case ID: {case.case_id}</span>
                    <span class='severity severity-{severity}'>{severity}</span>
                </div>
                <pre>Timestamp: {case.timestamp}\n{json.dumps(case.analysis, indent=2)}</pre>
            </div>
        """
    html_content += "</div>"
    html_content += "<div class='section'><h2>Non-Emergency Cases</h2>"
    for case in non_emergency_cases:
        severity = case.analysis.get("severity_level", "UNKNOWN")
        html_content += f"""
            <div class='case-item non-emergency'>
                <div class='case-header'>
                    <span>Case ID: {case.case_id}</span>
                    <span class='severity severity-{severity}'>{severity}</span>
                </div>
                <pre>Timestamp: {case.timestamp}\n{json.dumps(case.analysis, indent=2)}</pre>
            </div>
        """
    html_content += "</div>"
    html_content += "<div class='section'><h2>Notifications</h2>"
    for notification in notifications:
        html_content += f"""
            <div class='case-item emergency'>
                <div>Case ID: {notification.case_id}</div>
                <pre>Timestamp: {notification.timestamp}\n{json.dumps(notification.patient_data, indent=2)}</pre>
            </div>
        """
    html_content += "</div></div></body></html>"
    return HTMLResponse(content=html_content)

@router.get("/data", summary="Get Medical Data", description="Returns emergency cases, non-emergency cases, and notifications as JSON.")
def display_data(db: Session = Depends(get_db)):
    """
    Retrieve all medical cases and notifications as JSON data.
    """
    emergency_cases = db.query(MedicalCase).filter(MedicalCase.is_emergency == True).all()
    non_emergency_cases = db.query(MedicalCase).filter(MedicalCase.is_emergency == False).all()
    notifications = db.query(Notification).all()

    emergency_cases_list = [
        {
            "id": case.id,
            "case_id": case.case_id,
            "timestamp": case.timestamp,
            "is_emergency": case.is_emergency,
            "analysis": case.analysis,
            "original_data": case.original_data
        } for case in emergency_cases
    ]
    non_emergency_cases_list = [
        {
            "id": case.id,
            "case_id": case.case_id,
            "timestamp": case.timestamp,
            "is_emergency": case.is_emergency,
            "analysis": case.analysis,
            "original_data": case.original_data
        } for case in non_emergency_cases
    ]
    notifications_list = [
        {
            "id": notification.id,
            "case_id": notification.case_id,
            "timestamp": notification.timestamp,
            "status": notification.status,
            "patient_data": notification.patient_data
        } for notification in notifications
    ]

    return {
        "emergency_cases": emergency_cases_list,
        "non_emergency_cases": non_emergency_cases_list,
        "notifications": notifications_list
    }