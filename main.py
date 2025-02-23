import os
import json
import requests
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from passlib.context import CryptContext
from cors_config import add_cors  # Assuming you have cors.py

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class MedicalCase(Base):
    __tablename__ = "medical_cases"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    timestamp = Column(String)
    is_emergency = Column(Boolean)
    analysis = Column(JSON)
    original_data = Column(JSON)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("medical_cases.id"))
    timestamp = Column(String)
    status = Column(String)
    patient_data = Column(JSON)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="Medical Emergency Webhook API",
    description="API to capture medical webhooks, initiate calls, manage users, and display results.",
    version="1.0.0",
)
add_cors(app)  # Apply CORS
client = Groq(api_key=os.getenv("groq_api_key"))

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class WebhookData(BaseModel):
    extracted_data: Optional[Dict] = None
    class Config:
        schema_extra = {
            "example": {
                "extracted_data": {
                    "name": "John Doe",
                    "location": "New York",
                    "phone_number": "+10123456789",
                    "symptoms": "chest pain, shortness of breath"
                }
            }
        }

class CallData(BaseModel):
    phone_number: str
    user_data: Optional[Dict] = None
    class Config:
        schema_extra = {
            "example": {
                "phone_number": "+10123456789",
                "user_data": {
                    "patient_name": "Jane Doe",
                    "reason": "General inquiry"
                }
            }
        }

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# Bolna API Call Function
async def make_bolna_call(recipient_phone_number: str, user_data: Dict) -> Dict:
    url = "https://api.bolna.dev/call"
    agent_id = os.getenv("agent_id")
    token = os.getenv("Authorization")
    if not all([agent_id, token]):
        raise HTTPException(status_code=500, detail="Missing Bolna API credentials.")
    payload = {
        "agent_id": agent_id,
        "recipient_phone_number": recipient_phone_number,
        "user_data": user_data
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Bolna API call failed: {str(e)}")

# Emergency Analysis Function
async def analyze_emergency_status(data: Dict) -> tuple[bool, Dict]:
    content_str = json.dumps(data)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical triage assistant. Analyze the provided medical data and determine if it's an emergency.
                    Respond with a JSON object containing:
                    {
                        "is_emergency": boolean,
                        "severity_level": string (LOW|MEDIUM|HIGH|CRITICAL),
                        "reason": string,
                        "recommended_action": string,
                        "processed_data": object,
                        "required_specialists": array of strings
                    }
                    """
                },
                {"role": "user", "content": f"Analyze this medical data: {content_str}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_completion_tokens=1024,
            top_p=1,
            stream=False
        )
        analysis = json.loads(chat_completion.choices[0].message.content)
        return analysis["is_emergency"], analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Signup Endpoint
@app.post("/signup", summary="Create a New User", description="Register a new user with username and password.")
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user by storing their username and hashed password in the database.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password
    hashed_password = pwd_context.hash(user.password)

    # Create new user
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"status": "success", "message": "User created successfully", "username": user.username}

# Login Endpoint
@app.post("/login", summary="User Login", description="Login with username and password.")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user by checking username and password.
    """
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"status": "success", "message": "Login successful", "username": user.username}

# Webhook Endpoint
@app.post("/webhook", summary="Process Medical Webhook Data", description="Receives medical data via webhook.")
async def webhook(data: WebhookData, db: Session = Depends(get_db)):
    try:
        extracted_data = data.extracted_data
        if not extracted_data:
            return {"status": "success", "message": "No data to process"}
        timestamp = datetime.now().isoformat()
        is_emergency, analysis = await analyze_emergency_status(extracted_data)
        medical_case = MedicalCase(
            timestamp=timestamp,
            is_emergency=is_emergency,
            analysis=analysis,
            original_data=extracted_data
        )
        db.add(medical_case)
        db.commit()
        db.refresh(medical_case)
        case_id_str = f"CASE-{medical_case.id:04d}"
        medical_case.case_id = case_id_str
        db.commit()
        response_data = {
            "status": "success",
            "case_id": case_id_str,
            "severity": analysis["severity_level"]
        }
        if is_emergency:
            response_data["message"] = "Emergency data processed (call via /call)"
        else:
            response_data["message"] = "Non-emergency data processed"
        return response_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

# Call Endpoint
@app.post("/call", summary="Initiate a Bolna Call", description="Initiates a phone call to a new patient.")
async def invoke_call(data: CallData):
    try:
        if not data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required")
        call_user_data = data.user_data or {}
        call_response = await make_bolna_call(data.phone_number, call_user_data)
        return {
            "status": "success",
            "message": "Call initiated successfully",
            "phone_number": data.phone_number,
            "call_response": call_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Call invocation failed: {str(e)}")

# Display Endpoint
@app.get("/display", response_class=HTMLResponse, summary="View Medical Dashboard", description="Displays all cases.")
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

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Medical Emergency Webhook API",
        version="1.0.0",
        description="A FastAPI application to process medical webhooks, initiate calls, and display results.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)