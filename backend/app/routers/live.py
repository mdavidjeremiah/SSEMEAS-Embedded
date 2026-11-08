import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..security import user_from_token
from ..services.realtime import hub

router = APIRouter(tags=["live"])


@router.websocket("/ws")
async def live(ws: WebSocket):
    await ws.accept()
    try:                                   # the client sends its login token as the first message (keeps it out of URLs/logs)
        user = user_from_token(await asyncio.wait_for(ws.receive_text(), 5))
    except Exception:
        await ws.close(code=4401)
        return
    client = hub.add(ws, user["email"])
    try:
        while True:
            await ws.receive_text()        # we only push; this just notices when the browser disconnects
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(client)
