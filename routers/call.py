from fastapi import APIRouter, HTTPException
from schemas import CallData
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/", summary="Initiate a Bolna Call", description="Initiates a phone call to a new patient.")
async def invoke_call(data: CallData):
    try:
        if not data.phone_number:
            raise HTTPException(status_code=400, detail="Phone number is required")
        call_user_data = data.user_data or {}
        url = "https://api.bolna.dev/call"
        agent_id = os.getenv("agent_id")
        token = os.getenv("Authorization")
        if not all([agent_id, token]):
            raise HTTPException(status_code=500, detail="Missing Bolna API credentials.")
        payload = {
            "agent_id": agent_id,
            "recipient_phone_number": data.phone_number,
            "user_data": call_user_data
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        call_response = response.json()
        return {
            "status": "success",
            "message": "Call initiated successfully",
            "phone_number": data.phone_number,
            "call_response": call_response
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Call invocation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Call invocation failed: {str(e)}")