import asyncio
import websockets
import json
import random
import http
import pathlib
from engine.player import Player
from engine.game import Game

# -------------------------------------------------------
# STATIC FILE MAP
# Maps URL paths to local files so the WebSocket server
# can also serve the frontend without needing a separate
# HTTP server. This lets everything run on one port.
# -------------------------------------------------------
STATIC_FILES = {
    "/":           ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/game.html":  ("game.html",  "text/html"),
    "/main.js":    ("main.js",    "application/javascript"),
    "/style.css":  ("style.css",  "text/css"),
}


# -------------------------------------------------------
# HTTP HANDLER
# Called by the websockets library before the WebSocket
# handshake. If the request is a plain HTTP request for
# a file (not a WebSocket upgrade), we serve the file
# and return early. Otherwise we return None so the
# normal WebSocket handshake can proceed.
# -------------------------------------------------------
async def http_handler(_connection, request):
    from websockets.http11 import Response
    from websockets.datastructures import Headers

    # Let WebSocket upgrade requests through untouched
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None

    path = request.path.split("?")[0]
    if path in STATIC_FILES:
        filename, content_type = STATIC_FILES[path]
        file_path = pathlib.Path(__file__).parent / filename
        try:
            body = file_path.read_bytes()
            headers = Headers([
                ("Content-Type", content_type),
                ("Content-Length", str(len(body)))
            ])
            return Response(http.HTTPStatus.OK.value, http.HTTPStatus.OK.phrase, headers, body)
        except FileNotFoundError:
            pass

    return Response(http.HTTPStatus.NOT_FOUND.value, http.HTTPStatus.NOT_FOUND.phrase, Headers(), b"Page not found\n")

# -------------------------------------------------------
# ROOM STORAGE
# A dictionary that maps each room code (e.g. "7342") to
# its Room object. Multiple games can run simultaneously,
# each isolated in their own room.
# -------------------------------------------------------
rooms = {}


# -------------------------------------------------------
# ROOM CLASS
# Represents a single game lobby. Each room has its own
# set of connected players, a ready tracker, and a Game
# instance. Players are grouped into a room by their code.
# -------------------------------------------------------
class Room:
    def __init__(self, code):
        self.code = code
        self.connected_players = {}  # websocket -> Player
        self.ready_players = set()   # websockets of players who clicked Ready
        self.game = None             # Set once the game starts
        self.starting_chips = 1000
        self.small_blind    = 5
        self.big_blind      = 10

    # ---------------------------------------------------
    # BROADCAST
    # Sends a message to every player in this room.
    # Used to keep all players in the room in sync.
    # ---------------------------------------------------
    async def broadcast(self, message):
        if self.connected_players:
            payload = json.dumps(message)
            await asyncio.gather(*[ws.send(payload) for ws in self.connected_players], return_exceptions=True)

    # ---------------------------------------------------
    # START GAME
    # Called once all players in the room are ready.
    # Notifies everyone, then loops through full hands of
    # poker until fewer than 4 players remain connected.
    # Resets the game to None when it's over so a new
    # game can be started if players reconnect.
    # ---------------------------------------------------
    async def start_game(self):
        self.ready_players = set()
        players = list(self.connected_players.values())

        await self.broadcast({
            "event": "game_starting",
            "players": [p.name for p in players]
        })

        self.game = Game(players, small_blind=self.small_blind, big_blind=self.big_blind)
        try:
            while len(self.connected_players) >= 4:
                await self.game.gamePlay()
        except Exception as e:
            print(f"[!] Room {self.code} game ended: {e}")
            await self.broadcast({
                "event": "game_over",
                "reason": "A player disconnected."
            })
        finally:
            self.game = None


# -------------------------------------------------------
# GENERATE CODE
# Produces a random 4-digit room code as a string.
# The server keeps regenerating until it finds one that
# isn't already in use.
# -------------------------------------------------------
def generate_code():
    return str(random.randint(1000, 9999))


# -------------------------------------------------------
# HANDLE PLAYER
# This runs once per connected player for their entire
# session. It handles three phases:
#   1. Route — create a new room or join an existing one
#   2. Register — add the player to the room and broadcast
#   3. Ready — wait for the player to click Ready, then
#      start the game if everyone in the room is ready
# After that it waits for the connection to close, then
# cleans up. If the room is now empty, it is deleted.
# -------------------------------------------------------
async def handle_player(websocket):
    player = None
    room = None
    try:
        # First message from the client: name + action (create or join)
        raw = await asyncio.wait_for(websocket.recv(), timeout=30.0)
        data = json.loads(raw)
        player_name = data.get("name", "Unknown")
        action = data.get("action")

        # --- CREATE: generate a unique code and open a new room ---
        if action == "create":
            code = generate_code()
            while code in rooms:
                code = generate_code()
            room = Room(code)
            room.starting_chips = int(data.get("chips", 1000))
            room.small_blind    = int(data.get("sb",    5))
            room.big_blind      = int(data.get("bb",    10))
            rooms[code] = room
            # Send the code back so the client can display it
            await websocket.send(json.dumps({
                "event": "room_created",
                "code": code
            }))

        # --- JOIN: look up the room by the code the player entered ---
        elif action == "join":
            code = str(data.get("code", "")).strip()
            if code not in rooms:
                await websocket.send(json.dumps({
                    "event": "error",
                    "message": "Room not found. Check the code and try again."
                }))
                return
            room = rooms[code]

        else:
            return  # Unknown action — drop the connection

        # Register the player in the room and tell everyone
        player = Player(name=player_name, chips=room.starting_chips, websocket=websocket)
        room.connected_players[websocket] = player
        print(f"[+] {player_name} joined room {room.code}")

        await room.broadcast({
            "event": "player_joined",
            "player": player_name,
            "all_players": [p.name for p in room.connected_players.values()]
        })

        # Second message from the client: ready confirmation
        raw = await asyncio.wait_for(websocket.recv(), timeout=600.0)
        data = json.loads(raw)
        if data.get("action") == "ready":
            room.ready_players.add(websocket)
            await room.broadcast({
                "event": "player_ready",
                "player": player_name,
                "ready_count": len(room.ready_players),
                "total_players": len(room.connected_players)
            })
            # If all 4+ players are ready and no game is running, start one
            all_ready = len(room.ready_players) == len(room.connected_players)
            if all_ready and len(room.connected_players) >= 4 and room.game is None:
                room.game = "starting"
                asyncio.create_task(room.start_game())

        # Hold the connection open until the player disconnects
        await websocket.wait_closed()

    except websockets.ConnectionClosedOK:
        pass
    except websockets.ConnectionClosedError:
        pass
    except asyncio.TimeoutError:
        pass
    finally:
        # Clean up when a player leaves
        if room and websocket in room.connected_players:
            del room.connected_players[websocket]
            room.ready_players.discard(websocket)
            if player:
                if room.game and hasattr(room.game, 'players') and player in room.game.players:
                    player.folded = True
                await room.broadcast({
                    "event": "player_left",
                    "player": player.name,
                    "all_players": [p.name for p in room.connected_players.values()]
                })
            # If the room is now empty, remove it entirely
            if not room.connected_players:
                rooms.pop(room.code, None)
                print(f"[-] Room {room.code} closed.")


# -------------------------------------------------------
# MAIN
# Starts the WebSocket server on all interfaces (0.0.0.0)
# so both local and LAN connections are accepted on
# port 8765. Runs forever, calling handle_player() each
# time a new player connects.
# -------------------------------------------------------
async def main():
    import socket as _socket
    try:
        lan_ip = _socket.gethostbyname(_socket.gethostname())
    except Exception:
        lan_ip = "unknown"
    print("=" * 45)
    print(f"  Local            : http://localhost:8765")
    print(f"  Share with LAN   : http://{lan_ip}:8765")
    print(f"  For internet     : ngrok http 8765")
    print("=" * 45)
    async with websockets.serve(handle_player, "0.0.0.0", 8765,
                                process_request=http_handler):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
