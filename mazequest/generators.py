"""Maze generation. Each algorithm builds a spanning tree of the cell graph."""
import random
from .config import MUD_COST
from .maze import Maze


def dfs(m):                                     # recursive backtracker
    seen, stack = {0}, [0]
    while stack:
        u = stack[-1]
        ds = [d for d in random.sample(range(4), 4) if m.inb(u, d) and m.step(u, d) not in seen]
        if not ds:
            stack.pop()
            continue
        v = m.step(u, ds[0])
        m.carve(u, ds[0]); seen.add(v); stack.append(v)


def prim(m):                                    # randomized Prim
    seen, frontier = {0}, []
    add = lambda u: frontier.extend((u, d) for d in range(4) if m.inb(u, d) and m.step(u, d) not in seen)
    add(0)
    while frontier:
        u, d = frontier.pop(random.randrange(len(frontier)))
        v = m.step(u, d)
        if v not in seen:
            m.carve(u, d); seen.add(v); add(v)


def kruskal(m):                                 # randomized Kruskal with union-find
    parent = list(range(m.n * m.n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edges = [(i, d) for i in range(m.n * m.n) for d in (1, 2) if m.inb(i, d)]
    random.shuffle(edges)
    for i, d in edges:
        a, b = find(i), find(m.step(i, d))
        if a != b:
            parent[a] = b; m.carve(i, d)


GENERATORS = {"dfs": dfs, "prim": prim, "kruskal": kruskal}


def make_maze(size, gen="dfs", loops=0.04, mud=True):
    m = Maze(size)
    GENERATORS[gen](m)
    for _ in range(int(size * size * loops)):   # extra openings create alternative routes
        i, d = random.randrange(size * size), random.randrange(4)
        if m.inb(i, d):
            m.carve(i, d)
    if mud:
        m.cost = [MUD_COST if random.random() < 0.22 else 1 for _ in m.cost]
    m.cost[m.start] = m.cost[m.goal] = 1
    return m
