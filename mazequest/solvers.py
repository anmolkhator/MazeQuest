"""Path finding. One priority-queue framework; the priority decides the algorithm:
BFS = arrival order, DFS = newest first, Dijkstra = cost so far, Greedy = heuristic, A* = both."""
import heapq, itertools, time
from collections import namedtuple

Result = namedtuple("Result", "order path steps cost ms")


def solve(maze, alg, start):
    t0, n, goal = time.perf_counter(), maze.n, maze.goal
    h = lambda i: abs(i // n - goal // n) + abs(i % n - goal % n)        # Manhattan distance
    tie = itertools.count()
    prio = {"bfs": lambda i, g: next(tie), "dfs": lambda i, g: -next(tie),
            "dijkstra": lambda i, g: g, "greedy": lambda i, g: h(i), "astar": lambda i, g: g + h(i)}[alg]
    relax = alg in ("dijkstra", "astar")          # these may improve a cell's cost later
    g, prev, order, seen = {start: 0}, {}, [], set()
    heap = [(0, 0, start)]
    while heap:
        _, _, u = heapq.heappop(heap)
        if u in seen:
            continue
        seen.add(u); order.append(u)
        if u == goal:
            break
        for v in maze.neighbors(u):
            if v in seen:
                continue
            ng = g[u] + maze.cost[v]
            if v not in g or (relax and ng < g[v]):
                g[v], prev[v] = ng, u
                heapq.heappush(heap, (prio(v, ng), next(tie), v))
    path, i = [goal], goal
    while i != start:
        i = prev[i]; path.append(i)
    path.reverse()
    cost = sum(maze.cost[i] for i in path[1:])
    return Result(order, path, len(path) - 1, cost, (time.perf_counter() - t0) * 1000)
