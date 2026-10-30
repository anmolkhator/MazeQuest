"""MazeQuest web server (Flask). Python does the real work: maze generation, path finding,
score checking, accounts and the leaderboard. The browser only draws and sends key presses."""
import os, secrets
from flask import Flask, jsonify, render_template, request, session
from mazequest import auth, rooms
from mazequest.config import ALGOS, SIZES
from mazequest.game import Game
from mazequest.generators import GENERATORS, make_maze
from mazequest.solvers import solve

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))
MAZES = {}                                       # one current maze per browser session
ALG_NAMES = dict(ALGOS)


def fail(msg, code=400):
    return jsonify(error=msg), code


def current():
    user, maze = session.get("user"), MAZES.get(session.get("sid"))
    return user, maze


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/me")
def me():
    user = session.get("user")
    if not user:
        return jsonify(user=None)
    wins, best = auth.stats(user)
    board = [dict(user=u, score=s, size=n, eff=e) for u, s, n, e in auth.leaderboard()]
    return jsonify(user=user, wins=wins, best=best, board=board, invites=rooms.invites_for(user))


@app.post("/api/register")
@app.post("/api/login")
def sign_in():
    j = request.get_json(silent=True) or {}
    user, pw = str(j.get("user", "")), str(j.get("pw", ""))
    if request.path.endswith("register"):
        ok, msg = auth.register(user, pw)
        if not ok:
            return fail(msg)
    ok, name = auth.login(user, pw)
    if not ok:
        return fail(name, 401)
    session["user"], session["sid"] = name, secrets.token_hex(8)
    return jsonify(user=name)


@app.post("/api/logout")
def logout():
    MAZES.pop(session.get("sid"), None)
    session.clear()
    return jsonify(ok=True)


@app.get("/api/maze")
def new_maze():
    if not session.get("user"):
        return fail("Log in first", 401)
    size, gen = request.args.get("size", 25, int), request.args.get("gen", "dfs")
    if size not in SIZES or gen not in GENERATORS:
        return fail("Bad options")
    loops = min(max(request.args.get("loops", 0.04, float), 0), 0.2)
    m = make_maze(size, gen, loops, request.args.get("mud", 1, int) == 1)
    if len(MAZES) > 200:
        MAZES.clear()
    MAZES[session["sid"]] = m
    return jsonify(n=m.n, walls=m.walls, cost=m.cost, start=m.start, goal=m.goal)


def pack(r):
    return dict(order=r.order, path=r.path, steps=r.steps, cost=r.cost, ms=r.ms)


@app.post("/api/solve")
def solve_one():
    user, m = current()
    j = request.get_json(silent=True) or {}
    pos = j.get("pos")
    if not (user and m):
        return fail("No maze", 401)
    if j.get("alg") not in ALG_NAMES or not isinstance(pos, int) or not 0 <= pos < m.n * m.n:
        return fail("Bad request")
    return jsonify(pack(solve(m, j["alg"], pos)))


@app.post("/api/compare")
def compare():
    user, m = current()
    pos = (request.get_json(silent=True) or {}).get("pos")
    if not (user and m):
        return fail("No maze", 401)
    if not isinstance(pos, int) or not 0 <= pos < m.n * m.n:
        return fail("Bad request")
    rows = []
    for alg, name in ALGOS:
        r = solve(m, alg, pos)
        rows.append(dict(name=name, explored=len(r.order), steps=r.steps, cost=r.cost, ms=r.ms))
    return jsonify(rows)


@app.post("/api/finish")
def finish():
    user, m = current()
    j = request.get_json(silent=True) or {}
    if not (user and m):
        return fail("No maze", 401)
    g = Game(m)                                  # the server replays the moves, so scores cannot be faked
    for d in j.get("dirs", []):
        if isinstance(d, int) and d in range(4):
            g.move(d)
    if not g.over:
        return fail("That route does not reach the flag")
    g.t0, g.t1 = 0, max(1.0, min(float(j.get("seconds", 1)), 3600))
    res = g.result()
    res["pb"] = res["score"] > auth.stats(user)[1]
    auth.record_win(user, res["score"], m.n, res["eff"])
    return jsonify(res)


@app.before_request
def no_solver_in_race():                         # no hints or solvers while a race is running
    if request.path in ("/api/solve", "/api/compare") and rooms.racing(session.get("user")):
        return fail("The solver is switched off during a race", 403)


@app.get("/r/<code>")
def room_page(code):                             # invite link: the page joins the room after login
    return render_template("index.html")


def member(code):
    user, r = session.get("user"), rooms.get(code)
    return (user, r) if user and r and user in r.players else (user, None)


@app.post("/api/room/create")
def room_create():
    user, j = session.get("user"), request.get_json(silent=True) or {}
    if not user:
        return fail("Log in first", 401)
    size, gen = j.get("size", 25), j.get("gen", "dfs")
    if size not in SIZES or gen not in GENERATORS:
        return fail("Bad options")
    with rooms.LOCK:
        rooms.leave_all(user)
        r = rooms.create(user, dict(size=size, gen=gen, mud=bool(j.get("mud", True))))
    return jsonify(code=r.code)


@app.post("/api/room/join")
def room_join():
    user, j = session.get("user"), request.get_json(silent=True) or {}
    if not user:
        return fail("Log in first", 401)
    with rooms.LOCK:
        r = rooms.get(j.get("code", ""))
        if not r:
            return fail("Room not found", 404)
        if user not in r.players and r.state == "playing":
            return fail("That race has already started")
        rooms.leave_all(user, keep=r.code)
        if not r.join(user):
            return fail("Room is full")
        rooms.INVITES.get(user.lower(), set()).discard(r.code)
    return jsonify(code=r.code)


@app.post("/api/room/<code>/sync")
def room_sync(code):
    user, r = member(code)
    j = request.get_json(silent=True) or {}
    if not r:
        return fail("You are not in this room", 404)
    with rooms.LOCK:
        r.sync(user, j.get("dirs", []) if isinstance(j.get("dirs"), list) else [], j.get("round"))
        return jsonify(r.snapshot(j.get("round")))


@app.post("/api/room/<code>/start")
def room_start(code):
    user, r = member(code)
    if not r:
        return fail("You are not in this room", 404)
    if r.host != user:
        return fail("Only the host can start the race", 403)
    with rooms.LOCK:
        if r.state == "playing":
            return fail("The race is already running")
        r.start()
    return jsonify(ok=True)


@app.post("/api/room/<code>/invite")
def room_invite(code):
    user, r = member(code)
    if not r:
        return fail("You are not in this room", 404)
    name = auth.canon(str((request.get_json(silent=True) or {}).get("user", "")).strip())
    if not name or name == user:
        return fail("No player with that username")
    rooms.invite(r, name)
    return jsonify(ok=True)


@app.post("/api/room/<code>/leave")
def room_leave(code):
    user, r = member(code)
    if r:
        rooms.leave(r, user)
    return jsonify(ok=True)


if __name__ == "__main__":
    # HOST=0.0.0.0 lets friends on the same Wi-Fi join; PORT changes the port
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8000)), threaded=True)
