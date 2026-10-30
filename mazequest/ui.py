"""pygame client: login (with server address), solo play, friend rooms and live races."""
import math, textwrap, threading, time
import pygame
from .config import ALGOS, BOARD, C, GENS, SIZES, WINDOW
from .game import Game
from .maze import Maze
from urllib.parse import urlparse
from .net import ApiError, Net, ensure_server, lan_ip, normalize, split
from .solvers import solve
from .widgets import Button, TextInput

KEYS = [(pygame.K_UP, 0), (pygame.K_w, 0), (pygame.K_RIGHT, 1), (pygame.K_d, 1),
        (pygame.K_DOWN, 2), (pygame.K_s, 2), (pygame.K_LEFT, 3), (pygame.K_a, 3)]
PX = 690                                         # x of the right-hand panel
STATES = {"lobby": "waiting for players", "playing": "race in progress", "done": "race finished"}


class App:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode(WINDOW)
        pygame.display.set_caption("MazeQuest")
        f = lambda s, b=False: pygame.font.SysFont("helvetica,arial", s, bold=b)
        self.font, self.small, self.big, self.huge = f(17), f(14), f(26, True), f(44, True)
        self.clock = pygame.time.Clock()
        self.net, self.user, self.err, self.busy, self.login_out = None, None, "", False, None
        self.opt = dict(size=1, gen=0, mud=True, alg=4)
        self.bg = pygame.Surface(WINDOW)             # colourful gradient background, drawn once
        for y in range(WINDOW[1]):
            t = y / WINDOW[1]
            pygame.draw.line(self.bg, tuple(int(a + (b - a) * t) for a, b in zip(C["g1"], C["g2"])), (0, y), (WINDOW[0], y))
        self.sin = TextInput((340, 208, 300, 42), "Leave empty if you are the host", maxlen=60)
        self.uin, self.pin = TextInput((340, 262, 300, 42), "Username"), TextInput((340, 316, 300, 42), "Password", True)
        self.uin.active = True
        self.login_btns = [Button((340, 374, 145, 42), "Log in", lambda: self.auth(False), C["accent"]),
                           Button((495, 374, 145, 42), "Sign up", lambda: self.auth(True))]
        self.code_in = TextInput((830, 522, 76, 34), "Code", maxlen=5, upper=True)
        self.inv_in = TextInput((PX, 456, 176, 34), "Friend's username")
        self.reset_state()
        self.build_buttons()

    def reset_state(self):
        self.maze = self.game = self.run = self.modal = self.rs = None
        self.dirs, self.hint, self.rows, self.others, self.inv_btns = [], [], [], [], []
        self.fx = self.fy = 0.0
        self.shown, self.info, self.msg, self.msg_err = 0, "", "", False
        self.rc, self.live, self.syncing, self.finishing = None, False, False, False
        self.round_seen, self.flags, self.last_sync, self.last_me, self.me = 0, set(), 0, 0, {}

    def say(self, text, err=False):
        self.msg, self.msg_err = text, err

    # ---------- login ----------
    def auth(self, new):
        if self.busy:
            return
        url, u, p = normalize(self.sin.text), self.uin.text.strip(), self.pin.text
        self.busy, self.err = True, "Connecting…"

        def work():
            try:
                ensure_server(url)
                net = Net(url)
                self.login_out = (net, net.request("/api/register" if new else "/api/login", {"user": u, "pw": p})["user"], url, "")
            except ApiError as e:
                self.login_out = (None, None, url, str(e))
        threading.Thread(target=work, daemon=True).start()

    def logged_in(self, net, user, url):
        host, port = split(url)
        self.net, self.user, self.err, self.pin.text = net, user, "", ""
        self.public = urlparse(net.base).netloc if host not in ("127.0.0.1", "localhost") else f"{lan_ip()}:{port}"
        self.refresh_me()
        self.new_solo()

    def logout(self):
        if self.net:
            if self.rc:
                self.net.call(f"/api/room/{self.rc}/leave", {})
            self.net.call("/api/logout", {})
        self.user, self.net = None, None
        self.reset_state()

    def refresh_me(self):
        self.last_me = time.time()
        self.net.call("/api/me", cb=lambda r, e: setattr(self, "me", r) if r else None)

    # ---------- solo game ----------
    def new_solo(self):
        if self.rc:
            return
        o = self.opt
        self.net.call(f"/api/maze?size={SIZES[o['size']]}&gen={GENS[o['gen']][0]}&loops=0.04&mud={int(o['mud'])}",
                      cb=lambda r, e: self.load_maze(r) if r else self.say(e, True))

    def load_maze(self, j):
        m = Maze(j["n"])
        m.walls, m.cost, m.start, m.goal = j["walls"], j["cost"], j["start"], j["goal"]
        self.maze, self.game = m, Game(m)
        self.dirs, self.fx, self.fy, self.run, self.shown, self.hint = [], 0.0, 0.0, None, 0, []
        self.modal, self.info, self.rows, self.finishing = None, "", [], False
        if not self.rc:
            self.say("Reach the green flag. Hold WASD or the arrow keys.")

    def finish_solo(self):
        self.finishing = True
        g = self.game

        def done(r, e):
            if e:
                return self.say("Could not save your score: " + e, True)
            rows = [("Score", r["score"]), ("Moves", r["moves"]), ("Path cost", f"{r['cost']} (best {r['best']})"),
                    ("Efficiency", f"{r['eff']}%"), ("Time", f"{r['sec']:.1f} s")]
            self.modal = dict(title=f"{self.user} won!", sub="New personal best!" if r["pb"] else "You reached the flag.",
                              rows=rows, solo=True)
            self.refresh_me()
        self.net.call("/api/finish", {"dirs": self.dirs, "seconds": g.seconds}, done)

    def cycle(self, key, n):
        self.opt[key] = (self.opt[key] + 1) % n
        self.new_solo()

    def toggle_mud(self):
        self.opt["mud"] = not self.opt["mud"]
        self.new_solo()

    def run_solver(self):
        if self.game.over:
            return
        alg, name = ALGOS[self.opt["alg"]]
        self.run, self.shown, self.hint = solve(self.maze, alg, self.game.pos), 0, []
        r = self.run
        self.info = f"{name}: {len(r.order)} explored, {r.steps} steps, cost {r.cost}, {r.ms:.1f} ms"

    def show_hint(self):
        if not self.game.over:
            self.run, self.hint = None, solve(self.maze, "astar", self.game.pos).path[:9]

    def compare(self):
        rs = [(n, solve(self.maze, a, self.game.pos)) for a, n in ALGOS]
        best = min(r.cost for _, r in rs)
        self.rows = [(f"{n[:11]:11} {len(r.order):4} {r.steps:3} {r.cost:3}", r.cost == best) for n, r in rs]

    # ---------- friends ----------
    def create_room(self):
        o = self.opt
        self.net.call("/api/room/create", {"size": SIZES[o["size"]], "gen": GENS[o["gen"]][0], "mud": o["mud"]},
                      lambda r, e: self.enter_room(r["code"]) if r else self.say(e, True))

    def join(self, code=None):
        code = (code or self.code_in.text).strip().upper()
        if code:
            self.net.call("/api/room/join", {"code": code}, lambda r, e: self.enter_room(r["code"]) if r else self.say(e, True))

    def enter_room(self, code):
        self.rc, self.round_seen, self.live, self.flags, self.others, self.rs = code, 0, False, set(), [], None
        self.last_sync, self.modal = 0, None
        self.say("You are in the room. Wait for the host to start the race.")

    def leave_room(self):
        if self.rc:
            self.net.call(f"/api/room/{self.rc}/leave", {})
        self.rc, self.live, self.others, self.rs, self.modal = None, False, [], None, None
        self.new_solo()

    def start_race(self):
        self.net.call(f"/api/room/{self.rc}/start", {}, lambda r, e: self.say(e, True) if e else self.say(""))

    def invite(self):
        name = self.inv_in.text.strip()
        if name:
            self.net.call(f"/api/room/{self.rc}/invite", {"user": name},
                          lambda r, e: self.say(e, True) if e else (self.say("Invite sent. They will see it on screen."),
                                                                   setattr(self.inv_in, "text", "")))

    def poll_room(self):                         # every 0.4 s: send my moves, get everyone's positions
        if self.syncing or time.time() - self.last_sync < 0.4:
            return
        self.syncing, self.last_sync = True, time.time()
        self.net.call(f"/api/room/{self.rc}/sync", {"dirs": self.dirs if self.live else [], "round": self.round_seen},
                      self.on_sync)

    def on_sync(self, s, err):
        self.syncing = False
        if not self.rc:
            return
        if err:
            if "not in this room" in err:
                self.rc, self.rs = None, None
                self.new_solo()
            return self.say(err, True)
        if "maze" in s:
            self.load_maze(s["maze"])
            self.round_seen, self.live, self.flags = s["round"], False, set()
        me = next((p for p in s["players"] if p["name"] == self.user), {})
        self.others = [(p["pos"], p["color"]) for p in s["players"] if p["name"] != self.user]
        self.rs = s
        if s["state"] == "playing" and s["starts_in"] > 0:
            self.live = False
            self.say(f"Get ready… {math.ceil(s['starts_in'])}")
        elif s["state"] == "playing" and not self.live and self.game and not self.game.over and self.round_seen == s["round"]:
            self.live = True
            self.game.t0 = time.time()
            self.say("Go! First to the flag wins.")
        if me.get("done") and self.game:
            self.game.over = True
        if me.get("done") and "a" not in self.flags:
            self.flags.add("a")
            self.show_results(s, me)
        elif s["state"] == "done" and not self.flags:
            self.flags.add("b")
            self.show_results(s, me)
        elif s["state"] == "done" and self.modal:
            self.show_results(s, me)

    def show_results(self, s, me):
        ranked = sorted((p for p in s["players"] if p["done"]), key=lambda p: p["rank"])
        rows = [(f"#{p['rank']} {p['name']}", f"{p['time']:.1f} s  {p['score']} pts") for p in ranked]
        rows += [(p["name"], "did not finish" if s["state"] == "done" else "racing…") for p in s["players"] if not p["done"]]
        title = ("You won the race!" if me.get("rank") == 1 else f"You finished #{me['rank']}") if me.get("done") else "Race over"
        sub = f"{ranked[0]['name']} won in {ranked[0]['time']:.1f} s" if ranked else "Nobody reached the flag."
        self.modal = dict(title=title, sub=sub, rows=rows, solo=False)

    # ---------- buttons ----------
    def build_buttons(self):
        o, w, x2 = self.opt, 130, PX + 140
        host = lambda: bool(self.rs) and self.rs["host"] == self.user and self.rs["state"] != "playing"
        self.solo_btns = [
            Button((PX, 130, 270, 34), "New maze", self.new_solo, C["accent"]),
            Button((PX, 172, w, 34), lambda: f"Size {SIZES[o['size']]}", lambda: self.cycle("size", 3)),
            Button((x2, 172, w, 34), lambda: GENS[o["gen"]][1].split()[0], lambda: self.cycle("gen", 3)),
            Button((PX, 214, w, 34), lambda: "Mud on" if o["mud"] else "Mud off", self.toggle_mud),
            Button((x2, 214, w, 34), lambda: ALGOS[o["alg"]][1].split()[0], lambda: o.update(alg=(o["alg"] + 1) % 5)),
            Button((PX, 256, w, 34), "Run solver", self.run_solver, C["teal"]),
            Button((x2, 256, w, 34), "Hint", self.show_hint),
            Button((PX, 298, w, 34), "Compare all", self.compare),
            Button((x2, 298, w, 34), "Log out", self.logout),
            Button((PX, 522, w, 34), "Create room", self.create_room, C["accent"]),
            Button((910, 522, 50, 34), "Join", self.join),
        ]
        self.room_btns = [
            Button((PX, 410, w, 34), lambda: "Start race" if self.rs and self.rs["state"] == "lobby" else "Rematch", self.start_race, C["accent"], host),
            Button((x2, 410, w, 34), "Leave room", self.leave_room, C["red"]),
            Button((PX + 184, 456, 86, 34), "Invite", self.invite),
            Button((PX, 600, 270, 34), "Log out", self.logout),
        ]

    def inputs(self):
        return [self.sin, self.uin, self.pin] if self.user is None else [self.inv_in] if self.rc else [self.code_in]

    # ---------- events and update ----------
    def on_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            if self.user is None:
                for t in self.inputs():
                    t.active = t.rect.collidepoint(e.pos)
                any(b.click(e.pos) for b in self.login_btns)
            elif self.modal:
                if self.modal["solo"]:
                    if self.mbtns[0].rect.collidepoint(e.pos):
                        self.modal = None
                        self.new_solo()
                    elif self.mbtns[1].rect.collidepoint(e.pos):
                        self.logout()
                elif self.mbtns[0].rect.collidepoint(e.pos):
                    self.modal = None
            else:
                for t in self.inputs():
                    t.active = t.rect.collidepoint(e.pos)
                btns = self.room_btns if self.rc else self.solo_btns + self.inv_btns
                any(b.click(e.pos) for b in btns)
        elif e.type == pygame.KEYDOWN:
            box = next((t for t in self.inputs() if t.active), None)
            if self.user is None:
                if e.key == pygame.K_TAB:
                    order = self.inputs()
                    k = next((i for i, t in enumerate(order) if t.active), -1)
                    for t in order:
                        t.active = False
                    order[(k + 1) % 3].active = True
                elif e.key == pygame.K_RETURN:
                    self.auth(False)
                elif box:
                    box.key(e)
            elif box and e.key == pygame.K_RETURN:
                self.invite() if self.rc else self.join()
            elif box:
                box.key(e)

    def update(self, dt):
        g = self.game
        if not g:
            return
        r, c = divmod(g.pos, g.maze.n)
        dx, dy = c - self.fx, r - self.fy
        d = math.hypot(dx, dy)
        if d > 1e-3:                               # glide toward the target cell, slower on mud
            k = min(1, (7 if g.maze.cost[g.pos] > 1 else 16) * dt / d)
            self.fx, self.fy = self.fx + dx * k, self.fy + dy * k
            return
        self.fx, self.fy = c, r
        if self.run and self.shown < len(self.run.order):
            self.shown += max(1, len(self.run.order) // 80)
        if g.over:
            if not self.rc and not self.finishing and not self.modal:
                self.finish_solo()
            return
        if (self.rc and not self.live) or self.modal or any(t.active for t in self.inputs()):
            return
        keys = pygame.key.get_pressed()
        for key, dr in KEYS:
            if keys[key]:
                if g.move(dr):
                    self.dirs.append(dr)
                    self.hint, self.run = [], None
                break

    # ---------- drawing ----------
    def text(self, s, pos, font=None, col=None):
        self.scr.blit((font or self.font).render(str(s), True, col or C["ink"]), pos)

    def wrap(self, s, pos, col=None, width=38, lines=3):
        for k, ln in enumerate(textwrap.wrap(s, width)[:lines]):
            self.text(ln, (pos[0], pos[1] + k * 18), self.small, col or C["mute"])

    def rainbow(self, s, pos, font, center=False, col=None):   # the title, drawn in one calm colour
        x = pos[0] - (font.size(s)[0] // 2 if center else 0)
        self.text(s, (x, pos[1]), font, col or C["accent"])

    def ctext(self, s, y, font, col):
        self.text(s, ((WINDOW[0] - font.size(s)[0]) // 2, y), font, col)

    def draw_login(self):
        self.rainbow("MazeQuest", (WINDOW[0] // 2, 56), self.huge, True, C["white"])
        self.ctext("Race your friends through the maze", 124, self.font, C["white"])
        pygame.draw.rect(self.scr, C["panel"], (310, 170, 360, 290), border_radius=16)
        self.text("Joining a friend? Type their address.", (340, 186), self.small, C["mute"])
        for w in (self.sin, self.uin, self.pin, *self.login_btns):
            w.draw(self.scr, self.font)
        self.text(self.err, (340, 428), self.small, C["mute"] if self.busy else C["err"])

    def draw_board(self):
        m = self.maze
        cs, ox, oy = BOARD // m.n, 20, 20
        pygame.draw.rect(self.scr, C["panel"], (ox - 10, oy - 10, cs * m.n + 20, cs * m.n + 20), border_radius=14)
        pygame.draw.rect(self.scr, C["floor"], (ox, oy, cs * m.n, cs * m.n))
        cell = lambda i: (ox + i % m.n * cs, oy + i // m.n * cs)
        mid = lambda i: (cell(i)[0] + cs // 2, cell(i)[1] + cs // 2)
        for i, k in enumerate(m.cost):
            if k > 1:
                pygame.draw.rect(self.scr, C["mud"], (*cell(i), cs, cs))
        if self.run:
            veil = pygame.Surface((cs, cs), pygame.SRCALPHA)
            veil.fill((*C["seen"], 110))
            for i in self.run.order[:self.shown]:
                self.scr.blit(veil, cell(i))
            if self.shown >= len(self.run.order) and len(self.run.path) > 1:
                pygame.draw.lines(self.scr, C["path"], False, [mid(i) for i in self.run.path], max(3, cs // 4))
        if len(self.hint) > 1:
            pygame.draw.lines(self.scr, C["path"], False, [mid(i) for i in self.hint], max(2, cs // 6))
        for i, w in enumerate(m.walls):
            x, y = cell(i)
            for bit, a, b in ((1, (x, y), (x + cs, y)), (2, (x + cs, y), (x + cs, y + cs)),
                              (4, (x, y + cs), (x + cs, y + cs)), (8, (x, y), (x, y + cs))):
                if w & bit:
                    pygame.draw.line(self.scr, C["wall"], a, b, max(2, cs // 9))
        gx, gy = cell(m.goal)
        pygame.draw.rect(self.scr, C["goal"], (gx + cs // 5, gy + cs // 5, cs * 3 // 5, cs * 3 // 5), border_radius=4)
        for pos, col in self.others:                # friends' dots
            at = (ox + (pos % m.n + .5) * cs, oy + (pos // m.n + .5) * cs)
            pygame.draw.circle(self.scr, C["white"], at, cs * .31)
            pygame.draw.circle(self.scr, pygame.Color(col), at, cs * .24)
        at = (ox + (self.fx + .5) * cs, oy + (self.fy + .5) * cs)
        pygame.draw.circle(self.scr, C["white"], at, cs * .34)
        pygame.draw.circle(self.scr, C["me"], at, cs * .28)

    def draw_solo(self):
        for b in self.solo_btns:
            b.draw(self.scr, self.font)
        self.text(self.info[:42], (PX, 342), self.small, C["mute"])
        if self.rows:
            self.text("Algorithm   Expl Stp Cost", (PX, 366), self.small, C["mute"])
        for k, (row, best) in enumerate(self.rows):
            self.text(row, (PX, 386 + k * 20), self.small, C["path"] if best else C["ink"])
        self.text("Play with friends", (PX, 494), self.font, C["ink"])
        self.code_in.draw(self.scr, self.font)
        invs = self.me.get("invites", [])[:2]
        self.inv_btns = [Button((PX, 566 + k * 30, 270, 26), f"{i['host']} invited you: Join", lambda c=i["code"]: self.join(c))
                         for k, i in enumerate(invs)]
        for b in self.inv_btns:
            b.draw(self.scr, self.small)
        self.wrap(self.msg, (PX, 566 + len(invs) * 30), C["err"] if self.msg_err else C["mute"], lines=2)
        self.text(f"Your wins {self.me.get('wins', 0)}   Best {self.me.get('best', 0)}", (PX, 650), self.small, C["mute"])
        for k, b in enumerate(self.me.get("board", [])[:3]):
            self.text(f"{k + 1}. {b['user'][:10]}  {b['score']} pts  {b['size']}x{b['size']}", (PX, 672 + k * 18), self.small)

    def draw_room(self):
        s = self.rs or {}
        self.text(self.rc, (PX, 124), self.huge, C["accent"])
        self.text("room code  -  " + STATES.get(s.get("state"), "joining…"), (PX, 176), self.small, C["mute"])
        self.text("Friends type this address:", (PX, 200), self.small, C["mute"])
        self.text(self.public, (PX, 218), self.font, C["accent"])
        for k, p in enumerate(s.get("players", [])):
            y = 250 + k * 22
            pygame.draw.circle(self.scr, pygame.Color(p["color"]), (PX + 7, y + 9), 7)
            tag = (" (host)" if p["name"] == s["host"] else "") + (" (you)" if p["name"] == self.user else "")
            self.text(p["name"] + tag, (PX + 22, y), self.small)
            st = f"#{p['rank']}  {p['time']:.1f}s" if p["done"] else "racing" if s["state"] == "playing" else "ready"
            self.text(st, (PX + 190, y), self.small, C["goal"] if p["done"] else C["mute"])
        for b in self.room_btns:
            b.draw(self.scr, self.font)
        self.inv_in.draw(self.scr, self.font)
        self.wrap(self.msg, (PX, 500), C["err"] if self.msg_err else C["mute"])

    def draw_modal(self):
        veil = pygame.Surface(WINDOW, pygame.SRCALPHA)
        veil.fill((20, 10, 50, 190))
        self.scr.blit(veil, (0, 0))
        mo = self.modal
        h = 230 + 30 * len(mo["rows"])
        top = (WINDOW[1] - h) // 2
        band = C["accent"]
        pygame.draw.rect(self.scr, C["panel"], (300, top, 380, h), border_radius=16)
        pygame.draw.rect(self.scr, band, (300, top, 380, 76), border_top_left_radius=16, border_top_right_radius=16)
        self.text(mo["title"][:18], (330, top + 22), self.big, C["white"])
        self.text(mo["sub"][:34], (330, top + 92), self.font, C["path"])
        for k, (a, b) in enumerate(mo["rows"]):
            self.text(a, (330, top + 130 + k * 30), self.font, C["mute"])
            self.text(b, (480, top + 130 + k * 30), self.font, C["ink"])
        y = top + h - 62
        self.mbtns = [Button((330, y, 150, 42), "Play again", None, C["accent"]), Button((500, y, 150, 42), "Log out", None)] \
            if mo["solo"] else [Button((415, y, 150, 42), "Close", None, C["accent"])]
        for b in self.mbtns:
            b.draw(self.scr, self.font)

    def draw_legend(self):
        x = 24
        for col, name in ((C["me"], "You"), (C["mud"], "Mud (cost 5)"), (C["seen"], "Explored"), (C["path"], "Route"), (C["goal"], "Flag")):
            pygame.draw.rect(self.scr, col, (x, 703, 14, 14), border_radius=4)
            self.text(name, (x + 20, 700), self.small, C["white"])
            x += 24 + self.small.size(name)[0] + 14

    def draw_play(self):
        g = self.game
        pygame.draw.rect(self.scr, C["panel"], (PX - 14, 14, 298, WINDOW[1] - 28), border_radius=16)
        if g:
            self.draw_board()
            self.draw_legend()
            for k, (lab, val, col) in enumerate((("Moves", g.moves, C["ink"]), ("Cost", g.spent, C["ink"]),
                                                 ("Time", f"{g.seconds:.1f}s", C["ink"]))):
                self.text(lab, (PX + k * 95, 62), self.small, C["mute"])
                self.text(val, (PX + k * 95, 80), self.big, col)
        self.rainbow("MazeQuest", (PX, 20), self.big)
        self.text(f"Player: {self.user}   (WASD or arrow keys)", (PX, 113), self.small, C["mute"])
        self.draw_room() if self.rc else self.draw_solo()
        if self.modal:
            self.draw_modal()

    def step(self, events, dt=1 / 60):
        if self.login_out:
            net, user, url, err = self.login_out
            self.login_out, self.busy = None, False
            self.logged_in(net, user, url) if net else setattr(self, "err", err)
        if self.net:
            self.net.pump()
        for e in events:
            self.on_event(e)
        self.scr.blit(self.bg, (0, 0))
        if self.user is None:
            self.draw_login()
        else:
            self.update(dt)
            if self.rc:
                self.poll_room()
            elif time.time() - self.last_me > 5:
                self.refresh_me()
            self.draw_play()
        pygame.display.flip()

    def run_loop(self):
        while True:
            events = pygame.event.get()
            if any(e.type == pygame.QUIT for e in events):
                break
            self.step(events, self.clock.tick(60) / 1000)
        pygame.quit()


def run():
    App().run_loop()
