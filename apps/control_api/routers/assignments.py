from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Assignment, User, Node, AuditLog
from .. import schemas
from ..security import require_admin
from uuid import UUID

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.AssignmentOut, status_code=201)
async def create_assignment(body: schemas.AssignmentCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    for model, field, value in [(User, User.id, body.user_id), (Node, Node.id, body.node_id)]:
        res = await session.execute(select(model).where(field == value))
        if res.scalars().first() is None:
            raise HTTPException(404, f"{model.__name__} not found")
    existing = await session.execute(select(Assignment).where(Assignment.user_id==body.user_id, Assignment.node_id==body.node_id))
    if existing.scalars().first():
        raise HTTPException(400, "assignment exists")
    a = Assignment(user_id=body.user_id, node_id=body.node_id)
    session.add(a)
    await log(session, user.id, "assignment.create", "assignment", a.id)
    await session.commit(); await session.refresh(a)
    return a

@router.get("/", response_model=list[schemas.AssignmentOut])
async def list_assignments(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Assignment))
    return res.scalars().all()

@router.post("/{assignment_id}/move", response_model=schemas.AssignmentOut, summary="Move assignment to new node")
async def move_assignment(assignment_id: UUID, body: schemas.AssignmentMove, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Assignment).where(Assignment.id == assignment_id))
    a = res.scalars().first()
    if not a:
        raise HTTPException(404, "assignment not found")
    nres = await session.execute(select(Node).where(Node.id == body.node_id))
    if not nres.scalars().first():
        raise HTTPException(404, "node not found")
    a.node_id = body.node_id
    await log(session, user.id, "assignment.move", "assignment", a.id)
    await session.commit(); await session.refresh(a)
    return a

@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Assignment).where(Assignment.id == assignment_id))
    a = res.scalars().first()
    if not a:
        raise HTTPException(404, "assignment not found")
    await log(session, user.id, "assignment.delete", "assignment", a.id)
    await session.delete(a); await session.commit()
    return None
