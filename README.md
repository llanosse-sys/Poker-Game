# Multiplayer Texas Hold'em Poker

A real-time multiplayer Texas Hold'em poker game playable over a local network (or the internet via ngrok), built with Python and WebSockets.

---

## Features

- Real-time multiplayer gameplay (up to 6 players)
- Lobby system with room codes — share a 4-digit code to invite friends
- Full Texas Hold'em rules — preflop, flop, turn, river, and showdown
- Configurable starting chips, small blind, and big blind
- Accurate hand evaluation — pairs, straights, flushes, full houses, and more
- Side pot support for all-in situations
- No extra HTTP server needed — everything runs on a single port
- LAN support — play with anyone on the same network

---

## Tech Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Backend  | Python, asyncio, websockets       |
| Frontend | HTML, CSS, Vanilla JavaScript     |
| Protocol | WebSockets (ws://)                |

---

## Project Structure

```
Poker-Game/
│
├── server.py               # WebSocket server + HTTP file serving
│
├── engine/                 # Core game logic
│   ├── game.py             # Main game loop (preflop -> showdown)
│   ├── player.py           # Player state and actions
│   ├── card.py             # Card representation
│   ├── deck.py             # Deck creation and shuffling
│   ├── hand.py             # Player hand (hole cards)
│   ├── hand_evaluator.py   # Hand ranking and comparison
│   ├── betting_manager.py  # Betting rounds and blind posting
│   ├── pot_manager.py      # Main pot and side pot logic
│   └── position_manager.py # Dealer button and position assignment
│
├── index.html              # Lobby page (create or join a game)
├── game.html               # Game table UI
├── main.js                 # Frontend WebSocket logic
└── style.css               # Styling
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- `websockets` library

### Installation

```bash
# Clone the repository
git clone https://github.com/llanosse-sys/Poker-Game.git
cd Poker-Game

# Install dependencies
pip install websockets
```

### Running the Server

```bash
python server.py
```

The server will start and print connection info:

```
=============================================
  Local            : http://localhost:8765
  Share with LAN   : http://192.168.x.x:8765
  For internet     : ngrok http 8765
=============================================
```

### Playing the Game

1. Open `http://localhost:8765` in your browser
2. Enter your name and click **Create Game** — a 4-digit room code will be generated
3. Share the code with friends so they can join at the same address
4. Once all players (minimum 4) have joined and clicked **Ready Up**, the game begins

---

## How It Works

- The server handles both HTTP requests (serving the frontend files) and WebSocket connections on the same port — no separate web server needed.
- Each game room is isolated by a unique 4-digit code. Multiple rooms can run simultaneously.
- The game engine runs entirely on the server. The frontend receives game state updates via WebSocket events and renders them in real time.
- Hand evaluation uses all 7 cards (2 hole cards + 5 community cards) to find the best 5-card hand.

---

## Gameplay

| Stage    | Description                                            |
|----------|--------------------------------------------------------|
| Preflop  | 2 hole cards dealt, blinds posted, first betting round |
| Flop     | 3 community cards revealed, betting round              |
| Turn     | 1 community card revealed, betting round               |
| River    | 1 final community card revealed, betting round         |
| Showdown | Best hand wins, side pots distributed if needed        |

---

## Future Improvements

- [ ] Reconnection support if a player disconnects mid-game
- [ ] Spectator mode
- [ ] Player avatars and chat
- [ ] Mobile-friendly UI improvements
- [ ] Persistent chip counts across sessions

---
