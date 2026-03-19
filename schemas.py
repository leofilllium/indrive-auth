from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    id: str
    device_id: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    device_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    id: str
    device_id: str
