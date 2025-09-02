from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_session
from packages.common.vpnpanel_common.db.models import User, UserEngines, AuditLog
from ..security import hash_password, get_current_user, require_admin
from .. import schemas
import uuid
import io
import base64
import qrcode
import qrcode.image.svg

router = APIRouter()

async def log(session, actor, action, target_type, target_id):
    session.add(AuditLog(action=action, actor_user_id=actor, target_type=target_type, target_id=str(target_id)))

@router.post("/", response_model=schemas.UserOut, status_code=201)
async def create_user(body: schemas.UserCreate, session: AsyncSession = Depends(get_session), actor=Depends(require_admin)):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalars().first():
        raise HTTPException(400, "user exists")
    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    await session.flush()
    # default enable both engines
    session.add(UserEngines(user_id=user.id, allow_xray=True, allow_wireguard=True))
    await log(session, actor.id, "user.create", "user", user.id)
    await session.commit(); await session.refresh(user)
    return user

@router.get("/", response_model=list[schemas.UserOut])
async def list_users(session: AsyncSession = Depends(get_session), actor=Depends(get_current_user)):
    res = await session.execute(select(User))
    return res.scalars().all()

@router.get("/{user_id}", response_model=schemas.UserOut)
async def get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor=Depends(get_current_user)):
    res = await session.execute(select(User).where(User.id == user_id))
    u = res.scalars().first()
    if not u:
        raise HTTPException(404, "user not found")
    return u

@router.patch("/{user_id}", response_model=schemas.UserOut)
async def update_user(user_id: uuid.UUID, body: schemas.UserUpdate, session: AsyncSession = Depends(get_session), actor=Depends(require_admin)):
    res = await session.execute(select(User).where(User.id == user_id))
    u = res.scalars().first()
    if not u:
        raise HTTPException(404, "user not found")
    if body.password:
        u.password_hash = hash_password(body.password)
    if body.is_active is not None:
        u.is_active = body.is_active
    await log(session, actor.id, "user.update", "user", u.id)
    await session.commit(); await session.refresh(u)
    return u

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor=Depends(require_admin)):
    res = await session.execute(select(User).where(User.id == user_id))
    u = res.scalars().first()
    if not u:
        raise HTTPException(404, "user not found")
    await log(session, actor.id, "user.delete", "user", u.id)
    await session.delete(u); await session.commit()
    return None

@router.post("/{user_id}/engines", summary="Update allowed engines")
async def update_engines(user_id: uuid.UUID, body: schemas.UserEnginesUpdate, session: AsyncSession = Depends(get_session), actor=Depends(require_admin)):
    res = await session.execute(select(UserEngines).where(UserEngines.user_id == user_id))
    ue = res.scalars().first()
    if not ue:
        raise HTTPException(404, "engine settings missing")
    requested = set(body.engines)
    invalid = requested - {"xray", "wireguard"}
    if invalid:
        raise HTTPException(400, f"invalid engines: {','.join(invalid)}")
    ue.allow_xray = "xray" in requested
    ue.allow_wireguard = "wireguard" in requested
    await log(session, actor.id, "user.engines.update", "user", user_id)
    await session.commit()
    return {"user_id": str(user_id), "engines": list(requested)}

@router.get("/{user_id}/configs")
async def user_configs(user_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor=Depends(get_current_user)):
    ures = await session.execute(select(User).where(User.id == user_id))
    user = ures.scalars().first()
    if not user:
        raise HTTPException(404, "user not found")
    eres = await session.execute(select(UserEngines).where(UserEngines.user_id == user_id))
    engines = eres.scalars().first()
    allow_xray = engines.allow_xray if engines else True
    allow_wireguard = engines.allow_wireguard if engines else True
    data = {}
    if allow_xray:
        vmess_payload = {"v": "2", "ps": f"user-{user.id.hex[:6]}", "add": "example.com", "port": "443", "id": str(user.id), "aid": "0", "net": "ws", "type": "none", "host": "example.com", "path": "/ws", "tls": "tls"}
        import json
        vmess_b64 = base64.urlsafe_b64encode(json.dumps(vmess_payload).encode()).decode()
        vmess_link = f"vmess://{vmess_b64}"
        vless_link = f"vless://{user.id}@example.com:443?encryption=none&security=tls&type=ws&host=example.com&path=%2Fws#user-{user.id.hex[:6]}"
        clash_snippet = f"- name: user-{user.id.hex[:6]}\n  type: vmess\n  server: example.com\n  port: 443\n  uuid: {user.id}\n  alterId: 0\n  cipher: auto\n  tls: true\n  network: ws\n  ws-opts:\n    path: /ws\n    headers:\n      Host: example.com"
        data["xray"] = {"vmess": vmess_link, "vless": vless_link, "clash": clash_snippet}
    if allow_wireguard:
        wireguard_conf = f"[Interface]\nPrivateKey=CHANGEME\nAddress=10.0.0.2/32\n\n[Peer]\nPublicKey=PUBKEY\nEndpoint=example.com:51820\nAllowedIPs=0.0.0.0/0"
        data["wireguard"] = {"config": wireguard_conf}
    return data

@router.get("/{user_id}/wireguard/qr", summary="WireGuard config QR", responses={200: {"content": {"image/svg+xml": {}}}})
async def wireguard_qr(user_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor=Depends(get_current_user)):
    eres = await session.execute(select(UserEngines).where(UserEngines.user_id == user_id))
    engines = eres.scalars().first()
    if engines and not engines.allow_wireguard:
        raise HTTPException(403, "wireguard disabled for user")
    wireguard_conf = f"[Interface]\nPrivateKey=CHANGEME\nAddress=10.0.0.2/32\n\n[Peer]\nPublicKey=PUBKEY\nEndpoint=example.com:51820\nAllowedIPs=0.0.0.0/0"
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(wireguard_conf, image_factory=factory)
    buf = io.BytesIO(); img.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="image/svg+xml")
