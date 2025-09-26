from typing import Optional, Any
from uuid import UUID
from datetime import datetime, UTC
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator
from src.utils.security import generate_salt, hash_password


class FRTUPlatformAdminBase(BaseModel):
    name: str = Field(..., description="Name field is required")
    mobile_no: str
    email: Optional[EmailStr] = None
    attribute: Optional[dict[str, Any]] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None


class FRTUPlatformAdminCreate(FRTUPlatformAdminBase):
    salt: Optional[str] = None
    password_hash: Optional[str] = None
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def generate_password_fields(cls, data: dict) -> dict:
        if hasattr(data, '__dict__'):
            data = data.__dict__.copy()
        elif isinstance(data, dict):
            data = data.copy()
        else:
            return data

        password = data.get("password")
        if not password:
            raise ValueError("Password is required")

        salt = generate_salt()
        data["salt"] = generate_salt()
        data["password_hash"] = hash_password(password, salt)

        now_utc_naive = datetime.now(UTC).replace(tzinfo=None)
        data.setdefault("creation_time", now_utc_naive)
        data.setdefault("last_update_time", now_utc_naive)

        if "password" in data:
            del data["password"]

        return data

    def to_orm(self):
        orm_data = self.model_dump(exclude={"password"}, exclude_none=True)
        assert "password" not in orm_data
        return orm_data


class FRTUPlatformAdminUpdate(BaseModel):
    name: Optional[str] = None
    password_hash: Optional[str] = None
    salt: Optional[str] = None
    mobile_no: Optional[str] = None
    email: Optional[EmailStr] = None
    attribute: Optional[dict[str, Any]] = None


class FRTUPlatformAdminOut(FRTUPlatformAdminBase):
    id: UUID
    creation_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
