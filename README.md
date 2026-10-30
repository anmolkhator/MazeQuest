# MazeQuest Online (pygame)

A maze game built on graph traversal and optimization algorithms. Play solo or race friends online in a pygame window.

## Run it
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
A window opens. If no game server is running on your computer, `main.py` starts one for you.

## Play with friends
**Host (one person):**
1. Run `python3 main.py`, leave the address box empty, sign up and log in.
2. Press **Create room**. The room panel shows the address friends should use and the 5-letter room code. Allow incoming connections if macOS asks.
3. Friends on your Wi-Fi use the address shown (for example `192.168.1.20:8000`). Friends elsewhere need a tunnel: run `ngrok http 8000` and give them the address it prints (without the https:// part).
4. When everyone has joined, press **Start race**.

**Friends:**
1. Run `python3 main.py`, type the host's address in the address box (no http:// needed), then sign up and log in.
2. Type the room code next to **Create room** and press **Join**. Or type the host's username in **Invite a friend** on the host's side and press Join on the invite that appears on your screen.

Race rules: 3-second countdown, everyone gets the same maze, you see friends' coloured dots move live. The race ends when all finish or 60 seconds after the first finisher. The host can press **Rematch**. The solver and hint are off during a race. The server replays every move, so scores and times cannot be faked.

## Controls
Hold arrow keys or WASD to move. Mud tiles cost 5 and slow you down.

## Structure
```
MazeQuest-Online/
├── main.py              Opens the pygame window
├── app.py               Game server (Flask): accounts, mazes, rooms, scores
├── requirements.txt     pygame, flask
├── mazequest/
│   ├── ui.py            pygame screens: login, solo, room, results
│   ├── widgets.py       Button, TextInput
│   ├── net.py           Talks to the server in background threads
│   ├── config.py, maze.py, generators.py, solvers.py, game.py   game logic and algorithms
│   ├── rooms.py         Rooms, invites and race state
│   └── auth.py          SQLite accounts (PBKDF2 hashing) and leaderboard
├── templates/, static/  Optional browser version of the same game (open the server address in a browser)
```

## Algorithms
Generators: recursive backtracker (DFS), Prim, Kruskal (union-find). Solvers: BFS, DFS, Dijkstra, Greedy best-first, A* using a priority queue (`heapq`). Dijkstra and A* find the cheapest route on mud tiles.

## Server only
To run the server without a window (for example on another computer): `python3 app.py`, or `HOST=0.0.0.0 python3 app.py` to accept friends on your network.
