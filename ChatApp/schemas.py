# TechApp/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class IncomingMessage(BaseModel):
    """Payload sent by client to server"""
    message: str = Field(..., min_length=1, description="Message content")
    sender_type: str = Field(..., pattern="^(student|mentor)$", description="Sender type")
    sender_id: int = Field(..., description="Sender user ID")  # changed to int


class OutgoingMessage(BaseModel):
    """Payload sent by server to clients"""
    message: str
    sender_type: str
    sender_id: int  # changed to int
    sender_name: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    is_own: bool = False

    class Config:
        # Automatically convert datetime to ISO string when calling .dict() or .json()
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorMessage(BaseModel):
    """Standardized error payload"""
    error: str = Field(..., description="Error type or code")
    detail: Optional[str] = Field(None, description="Detailed explanation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
