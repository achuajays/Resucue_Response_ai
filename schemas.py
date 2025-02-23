from pydantic import BaseModel
from typing import Dict, Optional

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