
from typing import Optional, Any
from uuid import UUID
from datetime import datetime, UTC
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator
from src.utils.security import generate_salt, hash_password

class FRTUPlatformAdminBase(BaseModel):
    name: str = Field(..., description="Name field is required")
    # password: str = Field(..., description="Password field is required")
    mobile_no: str
    email: Optional[EmailStr] = None
    attribute: Optional[dict] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

class FRTUPlatformAdminCreate(FRTUPlatformAdminBase):
    @field_validator("last_update_time")
    def set_last_update_time(cls, value: datetime):
        return datetime.now(UTC)

    @field_validator("creation_time")
    def set_creation_time(cls, value: datetime):
        return datetime.now(UTC)
    
  # salt: Optional[str] = None
    # password_hash: Optional[str] = None
    # creation_time: Optional[datetime] = None
    # last_update_time: Optional[datetime] = None

    # @model_validator(mode="before")
    # @classmethod
    # def generate_password_fields(cls, data: dict) -> dict:
    #     if hasattr(data, '__dict__'):
    #         data = data.__dict__.copy()
    #     elif isinstance(data, dict):
    #         data = data.copy()
    #     else:
    #         return data

    #     # Ensure password exists
    #     password = data.get("password")
    #     if not password:
    #         raise ValueError("Password is required")

    #     salt = generate_salt()
    #     data["salt"] = generate_salt()
    #     data["password_hash"] = hash_password(password, salt)
    #     data.setdefault("creation_time", datetime.now(UTC))
    #     data.setdefault("last_update_time", datetime.now(UTC))

    #     return data

    def to_orm(self):
        orm_data = self.model_dump(exclude={"password"})
        return {k: v for k, v in orm_data.items() if v is not None}
    


class FRTUPlatformAdminUpdate(BaseModel):
    name: Optional[str] = None
    # password_hash: Optional[str] = None
    # salt: Optional[str] = None
    mobile_no: Optional[str] = None
    email: Optional[EmailStr] = None
    attribute: Optional[dict[str, Any]] = None


class FRTUPlatformAdminOut(FRTUPlatformAdminBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

