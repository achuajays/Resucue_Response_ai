from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String , name="hashed_password")  # Plain text password

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