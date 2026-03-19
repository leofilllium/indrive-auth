from sqlalchemy import Column, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    device_id = Column(String, nullable=True, index=True)
