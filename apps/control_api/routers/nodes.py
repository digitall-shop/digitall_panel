from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import Node, AuditLog
from .. import schemas
from ..security import require_admin
import uuid

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.NodeOut, status_code=201, summary="Create node", description="Register a new node in control plane")
async def create_node(body: schemas.NodeCreate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    exists = await session.execute(select(Node).where(Node.name == body.name))
    if exists.scalars().first():
        raise HTTPException(400, "node exists")
    node = Node(**body.model_dump())
    session.add(node)
    await log(session, user.id, "node.create", "node", node.id)
    await session.commit(); await session.refresh(node)
    return node

@router.get("/", response_model=list[schemas.NodeOut])
async def list_nodes(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Node))
    return res.scalars().all()

@router.get("/{node_id}", response_model=schemas.NodeOut)
async def get_node(node_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Node).where(Node.id == node_id))
    node = res.scalars().first()
    if not node:
        raise HTTPException(404, "not found")
    return node

@router.patch("/{node_id}", response_model=schemas.NodeOut)
async def update_node(node_id: uuid.UUID, body: schemas.NodeUpdate, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Node).where(Node.id == node_id))
    node = res.scalars().first()
    if not node:
        raise HTTPException(404, "not found")
    data = body.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(node, k, v)
    await log(session, user.id, "node.update", "node", node.id)
    await session.commit(); await session.refresh(node)
    return node

@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: uuid.UUID, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Node).where(Node.id == node_id))
    node = res.scalars().first()
    if not node:
        raise HTTPException(404, "not found")
    await log(session, user.id, "node.delete", "node", node.id)
    await session.delete(node); await session.commit()
    return None

@router.post("/{node_id}/policy", summary="Update node policy")
async def update_policy(node_id: uuid.UUID, policy: dict, session: AsyncSession = Depends(get_session), user=Depends(require_admin)):
    res = await session.execute(select(Node).where(Node.id == node_id))
    node = res.scalars().first()
    if not node:
        raise HTTPException(404, "not found")
    node.policy = policy
    await log(session, user.id, "node.policy.update", "node", node.id)
    await session.commit()
    return {"status": "ok", "policy": node.policy}

@router.get("/{node_id}/health", summary="Node health placeholder")
async def node_health(node_id: uuid.UUID):
    return {"node_id": str(node_id), "status": "healthy"}
