import enum
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    BigInteger,
    Enum,
    UniqueConstraint,
    Index,
    JSON,
    Text,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID  # remove JSONB usage
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base

# Enums
class EngineType(str, enum.Enum):
    xray = "xray"
    wireguard = "wireguard"

class ProtocolType(str, enum.Enum):
    vmess = "vmess"
    vless = "vless"
    trojan = "trojan"
    shadowsocks = "shadowsocks"

class TrafficSource(str, enum.Enum):
    collector = "collector"
    node_push = "node_push"
    reconcile = "reconcile"

# Core / Auth
class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")
    engine_settings = relationship("UserEngines", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(200))

    memberships = relationship("Membership", back_populates="role")

class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", back_populates="memberships")
    role = relationship("Role", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_membership_tenant_user_role"),
    )

# Node & Capacity
class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    public_ip: Mapped[str | None] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64), index=True)
    capacity_users: Mapped[int | None] = mapped_column(Integer)
    capacity_mbps: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    policy: Mapped[dict | None] = mapped_column(JSON)  # added for policy overrides
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tags = relationship("NodeTag", back_populates="node", cascade="all, delete-orphan")
    xray_inbounds = relationship("XRayInbound", back_populates="node", cascade="all, delete-orphan")
    wg_peers = relationship("WGPeer", back_populates="node", cascade="all, delete-orphan")

class NodeTag(Base):
    __tablename__ = "node_tags"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(50), nullable=False)

    node = relationship("Node", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("node_id", "tag", name="uq_node_tag"),
    )

# Plans & Subscriptions
class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quota_bytes: Mapped[int | None] = mapped_column(BigInteger)  # null = unlimited
    duration_days: Mapped[int | None] = mapped_column(Integer)  # null = no expiry baseline
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_plan_tenant_name"),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    quota_bytes_override: Mapped[int | None] = mapped_column(BigInteger)
    consumed_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

Index("uq_subscription_user_active_true", Subscription.user_id, unique=True, postgresql_where=Subscription.active)

# Credentials & Engine settings
class Credential(Base):
    __tablename__ = "credentials"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    engine: Mapped[EngineType] = mapped_column(Enum(EngineType, name="engine_type"), nullable=False)
    secret: Mapped[dict | None] = mapped_column(JSON)  # was JSONB
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="credentials")

    __table_args__ = (
        UniqueConstraint("user_id", "engine", name="uq_credential_user_engine"),
    )

class UserEngines(Base):
    __tablename__ = "user_engines"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    allow_xray: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_wireguard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="engine_settings")

# Node-specific engine config
class XRayInbound(Base):
    __tablename__ = "xray_inbounds"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(60), nullable=False)
    listen_ip: Mapped[str | None] = mapped_column(String(45))
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[ProtocolType] = mapped_column(Enum(ProtocolType, name="protocol_type"), nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON)  # was JSONB
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    node = relationship("Node", back_populates="xray_inbounds")

    __table_args__ = (
        UniqueConstraint("node_id", "port", "protocol", name="uq_inbound_node_port_proto"),
    )

class WGPeer(Base):
    __tablename__ = "wg_peers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    interface: Mapped[str] = mapped_column(String(50), nullable=False)
    public_key: Mapped[str] = mapped_column(String(60), nullable=False)
    preshared_key: Mapped[str | None] = mapped_column(String(60))
    allowed_ips: Mapped[str | None] = mapped_column(Text)
    endpoint: Mapped[str | None] = mapped_column(String(120))
    persistent_keepalive: Mapped[int | None] = mapped_column(Integer)
    last_handshake_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    node = relationship("Node", back_populates="wg_peers")

    __table_args__ = (
        UniqueConstraint("node_id", "public_key", name="uq_wgpeer_node_pubkey"),
    )

# Assignments (user-node policy overrides)
class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    policy: Mapped[dict | None] = mapped_column(JSON)  # overrides (speed caps, route sets, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "node_id", name="uq_assignment_user_node"),
    )

# Traffic events (append-only)
class TrafficEvent(Base):
    __tablename__ = "traffic_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    node_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    bytes_up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source: Mapped[TrafficSource] = mapped_column(Enum(TrafficSource, name="traffic_source"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

Index("ix_traffic_events_user_time", TrafficEvent.user_id, TrafficEvent.event_time)
Index("ix_traffic_events_node_time", TrafficEvent.node_id, TrafficEvent.event_time)

# Hourly rollups (partitioned parent) - partitions handled via migrations
class TrafficRollupHourly(Base):
    __tablename__ = "traffic_rollups_hourly"
    __table_args__ = {"postgresql_partition_by": "RANGE (day)"}

    hour_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)  # partition key part, not nullable
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # UTC date bucket
    bytes_up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

# Audit logs
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(120))
    target_id: Mapped[str | None] = mapped_column(String(120))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    metadata: Mapped[dict | None] = mapped_column(JSON)

Index("ix_audit_logs_action_time", AuditLog.action, AuditLog.created_at)
