"""Friend races: rooms, invites and live race state. Pure Python, no web code."""
import random, threading, time
from . import auth
from .game import Game
from .generators import make_maze

COLORS = ["#E07A1F", "#00ACC1", "#8E44AD", "#1E88E5", "#43A047", "#B8860B"]
MAX_PLAYERS, COUNTDOWN, GRACE = 6, 3, 60       # GRACE: seconds the others get after the first finisher
LOCK = threading.RLock()
ROOMS, INVITES = {}, {}                          # code -> Room, username (lower case) -> set of room codes


class Room:
    def __init__(self, code, host, opts):
        self.code, self.host, self.opts = code, host, opts
        self.players, self.maze, self.round = {}, None, 0
        self.state, self.t_start, self.first_done, self.made = "lobby", 0.0, None, time.time()
        self.join(host)

    def join(self, user):
        if user in self.players:
            return True
        if len(self.players) >= MAX_PLAYERS:
            return False
        used = {p["color"] for p in self.players.values()}
        self.players[user] = dict(color=next(c for c in COLORS if c not in used), pos=0, moves=0,
                                  done=False, finish=None, result=None)
        return True

    def start(self):                             # everyone gets the same maze (also used for rematches)
        o = self.opts
        self.maze = make_maze(o["size"], o["gen"], 0.04, o["mud"])
        self.round += 1
        self.state, self.t_start, self.first_done = "playing", time.time() + COUNTDOWN, None
        for p in self.players.values():
            p.update(pos=self.maze.start, moves=0, done=False, finish=None, result=None)

    def sync(self, user, dirs, rnd):
        p = self.players.get(user)
        if not p or self.state != "playing" or rnd != self.round or p["done"] or time.time() < self.t_start:
            return
        g = Game(self.maze)                      # replay the moves on the server: positions cannot be faked
        for d in dirs[:4000]:
            if isinstance(d, int) and d in range(4):
                g.move(d)
        p["pos"], p["moves"] = g.pos, g.moves
        if g.over:
            now = time.time()
            p["done"], p["finish"] = True, max(1.0, now - self.t_start)
            g.t0, g.t1 = 0, p["finish"]
            p["result"] = g.result()
            auth.record_win(user, p["result"]["score"], self.maze.n, p["result"]["eff"])
            self.first_done = self.first_done or now

    def tick(self):                              # the race ends when all finish, or GRACE seconds after the first
        if self.state == "playing":
            late = self.first_done and time.time() - self.first_done > GRACE
            if all(p["done"] for p in self.players.values()) or late:
                self.state = "done"

    def snapshot(self, rnd):
        self.tick()
        order = sorted((n for n, p in self.players.items() if p["done"]), key=lambda n: self.players[n]["finish"])
        out = dict(code=self.code, host=self.host, state=self.state, round=self.round, opts=self.opts,
                   starts_in=max(0.0, self.t_start - time.time()) if self.state == "playing" else 0, players=[])
        for n, p in self.players.items():
            out["players"].append(dict(name=n, color=p["color"], pos=p["pos"], moves=p["moves"], done=p["done"],
                rank=order.index(n) + 1 if p["done"] else None, time=p["finish"],
                score=p["result"]["score"] if p["result"] else None))
        if self.maze and rnd != self.round:
            m = self.maze
            out["maze"] = dict(n=m.n, walls=m.walls, cost=m.cost, start=m.start, goal=m.goal)
        return out


def create(host, opts):
    with LOCK:
        for c in [c for c, r in ROOMS.items() if time.time() - r.made > 7200]:
            ROOMS.pop(c)                         # drop rooms older than two hours
        while True:
            code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
            if code not in ROOMS:
                break
        ROOMS[code] = Room(code, host, opts)
        return ROOMS[code]


def get(code):
    return ROOMS.get(str(code).upper())


def leave(room, user):
    with LOCK:
        room.players.pop(user, None)
        if not room.players:
            ROOMS.pop(room.code, None)
        else:
            if room.host == user:
                room.host = next(iter(room.players))
            room.tick()


def leave_all(user, keep=None):
    for r in [r for r in ROOMS.values() if user in r.players and r.code != keep]:
        leave(r, user)


def invite(room, name):
    INVITES.setdefault(name.lower(), set()).add(room.code)


def invites_for(user):
    codes = INVITES.get(user.lower(), set())
    codes &= set(ROOMS)
    return [dict(code=c, host=ROOMS[c].host) for c in codes]


def racing(user):
    return any(r.state == "playing" and user in r.players for r in ROOMS.values())
