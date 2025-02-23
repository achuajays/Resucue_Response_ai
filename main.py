from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database configuration
DATABASE_URL = "postgresql://myuser:92keOF3QWIoNwDILM8TWfrRwaSOlrEgN@dpg-cutdjj5ds78s738uukag-a.oregon-postgres.render.com/mydatabase_0xgr"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Define the Issue model (table structure)
class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String, index=True)
    issue = Column(String)

# Create the table in the database (if it doesn't exist)
Base.metadata.create_all(bind=engine)

# Pydantic model for request data
class IssueCreate(BaseModel):
    name: str
    location: str
    issue: str

# Pydantic model for response data
class IssueResponse(BaseModel):
    id: int
    name: str
    location: str
    issue: str

    class Config:
        orm_mode = True  # Allows Pydantic to work with SQLAlchemy ORM objects

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize FastAPI app
app = FastAPI()

# POST endpoint to create an issue
@app.post("/issues/", response_model=IssueResponse)
def create_issue(issue: IssueCreate, db: Session = Depends(get_db)):
    # Create a new Issue instance
    db_issue = Issue(name=issue.name, location=issue.location, issue=issue.issue)
    # Add it to the session
    db.add(db_issue)
    # Commit the transaction
    db.commit()
    # Refresh the instance to get the generated ID
    db.refresh(db_issue)
    # Return the created issue
    return db_issue