"""WebSocket hub: pushes new readings and alerts to the dashboards that are allowed to see them."""
from fastapi import WebSocket

from .. import repo


class Hub:
    def __init__(self):
        self.clients: set[tuple[WebSocket, str]] = set()

    def add(self, ws: WebSocket, email: str) -> tuple:
        client = (ws, email)
        self.clients.add(client)
        return client

    def remove(self, client: tuple) -> None:
        self.clients.discard(client)

    async def send_to_viewers(self, tank_id: int, message: dict) -> None:
        for client in list(self.clients):
            ws, email = client
            if not repo.can_view_tank(email, tank_id):
                continue
            try:
                await ws.send_json(message)
            except Exception:
                self.clients.discard(client)


hub = Hub()
