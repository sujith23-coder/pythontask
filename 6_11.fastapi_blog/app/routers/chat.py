from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import decode_token, get_current_user
from ..database import SessionLocal, get_db
from ..models import ChatMessage, PrivateMessage, User

router = APIRouter(tags=["chat"])


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active[user_id] = websocket
        print(f"[chat] user connected: {user_id}")

    def disconnect(self, user_id: int):
        if user_id in self.active:
            self.active.pop(user_id, None)
            print(f"[chat] user disconnected: {user_id}")

    async def send_json(self, user_id: int, payload: dict):
        ws = self.active.get(user_id)
        if ws:
            await ws.send_json(payload)

    async def broadcast_json(self, payload: dict, exclude_user_id: int | None = None):
        for uid, ws in list(self.active.items()):
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            await ws.send_json(payload)


manager = ConnectionManager()


@router.get("/chat/history", response_model=list[schemas.ChatMessageRead])
def chat_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ = current
    return db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(100).all()


@router.post("/chat/private", response_model=schemas.PrivateMessageRead)
def send_private_message(
    data: schemas.PrivateMessageCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receiver = db.query(User).filter(User.id == data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    msg = PrivateMessage(sender_id=current.id, receiver_id=data.receiver_id, message=data.message)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/chat/private/history/{other_user_id}", response_model=list[schemas.PrivateMessageRead])
def private_history(other_user_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(PrivateMessage)
        .filter(
            ((PrivateMessage.sender_id == current.id) & (PrivateMessage.receiver_id == other_user_id))
            | ((PrivateMessage.sender_id == other_user_id) & (PrivateMessage.receiver_id == current.id))
        )
        .order_by(PrivateMessage.timestamp.asc())
        .all()
    )


@router.websocket("/chat/")
async def websocket_chat(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        user_id = int(decode_token(token))
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    db = SessionLocal()
    try:
        while True:
            text = await websocket.receive_text()
            text = text.strip()
            if not text:
                continue

            target = None
            content = text
            if text.startswith("@") and " " in text:
                # Optional private websocket message format: "@<user_id> <message>".
                first, rest = text.split(" ", 1)
                target = first[1:]
                content = rest.strip()

            if target and target.isdigit():
                receiver_id = int(target)
                msg = PrivateMessage(sender_id=user_id, receiver_id=receiver_id, message=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = {
                    "type": "private_message",
                    "id": msg.id,
                    "sender_id": user_id,
                    "receiver_id": receiver_id,
                    "message": content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                await manager.send_json(receiver_id, payload)
                await manager.send_json(user_id, payload)
            else:
                msg = ChatMessage(sender_id=user_id, message=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = {
                    "type": "chat_message",
                    "id": msg.id,
                    "sender_id": user_id,
                    "message": content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                await manager.broadcast_json(payload)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        db.close()
