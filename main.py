import asyncio
from ws.ws_audio_server import start_websocket_server

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
