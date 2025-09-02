یسfrom datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class ProtocolEnum(str, Enum):
    xray = "xray"
    wireguard = "wireguard"

# User schemas
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64)

class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)

class UserRead(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# VPN Account
class VPNAccountBase(BaseModel):
    protocol: ProtocolEnum

class VPNAccountCreate(VPNAccountBase):
    pass

class VPNAccountRead(VPNAccountBase):
    id: int
    user_id: int
    public_key: Optional[str]
    endpoint: Optional[str]
    disabled: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UsageStatRead(BaseModel):
    id: int
    account_id: int
    bytes_up: int
    bytes_down: int
    period_start: datetime

    class Config:
        from_attributes = True

class UserWithAccounts(UserRead):
    accounts: List[VPNAccountRead] = []

