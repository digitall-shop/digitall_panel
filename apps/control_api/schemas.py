from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import uuid

# Basic shared models
class TenantBase(BaseModel):
    name: str
class TenantCreate(TenantBase):
    class Config:
        json_schema_extra = {"example": {"name": "acme"}}
class TenantUpdate(BaseModel):
    name: Optional[str] = None
class TenantOut(TenantBase):
    id: uuid.UUID
    created_at: datetime
    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: EmailStr
class UserCreate(UserBase):
    password: str
    class Config:
        json_schema_extra = {"example": {"email": "user@example.com", "password": "S3cret!"}}
class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_active: Optional[bool] = None
class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    class Config:
        orm_mode = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
class RoleCreate(RoleBase):
    class Config:
        json_schema_extra = {"example": {"name": "admin", "description": "Administrator role"}}
class RoleOut(RoleBase):
    id: uuid.UUID
    class Config:
        orm_mode = True

class MembershipCreate(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
class MembershipOut(MembershipCreate):
    id: uuid.UUID
    class Config:
        orm_mode = True

class NodeBase(BaseModel):
    name: str
    public_ip: Optional[str] = None
    region: Optional[str] = None
    capacity_users: Optional[int] = None
    capacity_mbps: Optional[int] = None
class NodeCreate(NodeBase):
    class Config:
        json_schema_extra = {"example": {"name": "node-1", "public_ip": "198.51.100.10", "region": "eu-west"}}
class NodeUpdate(BaseModel):
    public_ip: Optional[str] = None
    region: Optional[str] = None
    capacity_users: Optional[int] = None
    capacity_mbps: Optional[int] = None
    is_enabled: Optional[bool] = None
    name: Optional[str] = None
class NodeOut(NodeBase):
    id: uuid.UUID
    is_enabled: bool
    class Config:
        orm_mode = True

class PlanBase(BaseModel):
    tenant_id: uuid.UUID
    name: str
    quota_bytes: Optional[int] = None
    duration_days: Optional[int] = None
class PlanCreate(PlanBase):
    class Config:
        json_schema_extra = {"example": {"tenant_id": "00000000-0000-0000-0000-000000000000", "name": "basic", "quota_bytes": 100000000000, "duration_days": 30}}
class PlanUpdate(BaseModel):
    name: Optional[str] = None
    quota_bytes: Optional[int] = None
    duration_days: Optional[int] = None
class PlanOut(PlanBase):
    id: uuid.UUID
    created_at: datetime
    class Config:
        orm_mode = True

class SubscriptionCreate(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    plan_id: Optional[uuid.UUID] = None
    quota_bytes_override: Optional[int] = None
    expiry_at: Optional[datetime] = None
    class Config:
        json_schema_extra = {"example": {"tenant_id": "00000000-0000-0000-0000-000000000000", "user_id": "00000000-0000-0000-0000-000000000000", "plan_id": "00000000-0000-0000-0000-000000000000"}}
class SubscriptionUpdate(BaseModel):
    plan_id: Optional[uuid.UUID] = None
    quota_bytes_override: Optional[int] = None
    expiry_at: Optional[datetime] = None
    active: Optional[bool] = None
class SubscriptionOut(SubscriptionCreate):
    id: uuid.UUID
    active: bool
    consumed_bytes: int
    class Config:
        orm_mode = True

class AssignmentCreate(BaseModel):
    user_id: uuid.UUID
    node_id: uuid.UUID
    class Config:
        json_schema_extra = {"example": {"user_id": "00000000-0000-0000-0000-000000000000", "node_id": "00000000-0000-0000-0000-000000000000"}}
class AssignmentOut(AssignmentCreate):
    id: uuid.UUID
    class Config:
        orm_mode = True
class AssignmentMove(BaseModel):
    node_id: uuid.UUID

class TrafficEventIn(BaseModel):
    user_id: Optional[uuid.UUID] = None
    node_id: Optional[uuid.UUID] = None
    bytes_up: int
    bytes_down: int
    class Config:
        json_schema_extra = {"example": {"user_id": "00000000-0000-0000-0000-000000000000", "node_id": "00000000-0000-0000-0000-000000000000", "bytes_up": 1234, "bytes_down": 5678}}
class TrafficSummaryOut(BaseModel):
    user_id: Optional[uuid.UUID]
    total_up: int
    total_down: int

class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    action: str
    actor_user_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    class Config:
        orm_mode = True

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    roles: List[str] = []

class UserEnginesUpdate(BaseModel):
    engines: List[str]
    class Config:
        json_schema_extra = {"example": {"engines": ["xray", "wireguard"]}}
