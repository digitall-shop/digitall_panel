from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import AuditLog
from ..security import get_current_user
from .. import schemas

router = APIRouter()

@router.get("/logs", response_model=list[schemas.AuditLogOut])
async def list_audit_logs(session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    res = await session.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))
    return res.scalars().all()

