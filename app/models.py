from datetime import datetime

from enum import Enum
from sqlalchemy import String, Integer, DateTime, Boolean, Enum as SQLEnum, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class ProtocolEnum(str, Enum):
    xray = "xray"
    wireguard = "wireguard"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["VPNAccount"]] = relationship("VPNAccount", back_populates="user", cascade="all,delete-orphan")

class VPNAccount(Base):
    __tablename__ = "vpn_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    protocol: Mapped[ProtocolEnum] = mapped_column(SQLEnum(ProtocolEnum), index=True)
    public_key: Mapped[str | None] = mapped_column(String(255))  # wireguard
    private_key: Mapped[str | None] = mapped_column(String(255))  # wireguard (store encrypted or not at all in prod)
    endpoint: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="accounts")
    usages: Mapped[list["UsageStat"]] = relationship("UsageStat", back_populates="account", cascade="all,delete-orphan")

class UsageStat(Base):
    __tablename__ = "usage_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("vpn_accounts.id", ondelete="CASCADE"), index=True)
    bytes_up: Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_down: Mapped[int] = mapped_column(BigInteger, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    account: Mapped[VPNAccount] = relationship("VPNAccount", back_populates="usages")

