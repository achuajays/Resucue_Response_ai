from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import MedicalCase
from schemas import WebhookData
from database import get_db
from dependencies import client
import json
from datetime import datetime

router = APIRouter()

@router.post("/", summary="Process Medical Webhook Data", description="Receives medical data via webhook.")
async def webhook(data: WebhookData, db: Session = Depends(get_db)):
    try:
        extracted_data = data.extracted_data
        if not extracted_data:
            return {"status": "success", "message": "No data to process"}
        timestamp = datetime.now().isoformat()
        content_str = json.dumps(extracted_data)
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
        is_emergency = analysis["is_emergency"]
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