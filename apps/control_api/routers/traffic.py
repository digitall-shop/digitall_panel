from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from ..db import get_session
from packages.common.vpnpanel_common.db.models import TrafficEvent, TrafficSource, AuditLog
from ..security import get_current_user
from .. import schemas
import uuid
from typing import List, Optional

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/events", status_code=202, summary="Ingest traffic events")
async def ingest_events(events: List[schemas.TrafficEventIn], session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    objs = []
    for ev in events:
        objs.append(TrafficEvent(event_time=now, user_id=ev.user_id, node_id=ev.node_id, bytes_up=ev.bytes_up, bytes_down=ev.bytes_down, source=TrafficSource.collector))
    session.add_all(objs)
    await log(session, user.id, "traffic.ingest", "traffic_batch", len(objs))
    await session.commit()
    return {"ingested": len(objs)}

@router.get("/summary", response_model=list[schemas.TrafficSummaryOut])
async def traffic_summary(user_id: Optional[uuid.UUID] = Query(None), session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    stmt = select(TrafficEvent.user_id, func.sum(TrafficEvent.bytes_up), func.sum(TrafficEvent.bytes_down)).group_by(TrafficEvent.user_id)
    if user_id:
        stmt = stmt.where(TrafficEvent.user_id == user_id)
    rows = (await session.execute(stmt)).all()
    return [schemas.TrafficSummaryOut(user_id=r[0], total_up=r[1] or 0, total_down=r[2] or 0) for r in rows]

