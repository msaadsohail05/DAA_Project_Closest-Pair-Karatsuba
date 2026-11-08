import argparse
import math
import random
import time
from operator import itemgetter

Y = itemgetter(1)

def read_points(path):
    with open(path) as f:
        n = int(f.readline())
        pts = []
        for line in f:
            parts = line.split()
            if parts:
                pts.append((float(parts[0]), float(parts[1])))
    if len(pts) != n:
        raise ValueError(f"{path}: header says {n} points but found {len(pts)}")
    return pts

def _dist2(p, q):
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return dx * dx + dy * dy


def _brute(pts):
    """Returns (squared distance, p, q)."""
    best = (math.inf, None, None)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = _dist2(pts[i], pts[j])
            if d < best[0]:
                best = (d, pts[i], pts[j])
    return best


def brute_force_closest(pts):
    d, p, q = _brute(pts)
    return math.sqrt(d), p, q

def _solve(px, trace, depth, base):   
    n = len(px)
    if n <= base:
        d, p, q = _brute(px)
        if trace is not None:
            trace.append({"event": "base", "depth": depth, "points": list(px),
                          "best": (math.sqrt(d), p, q)})
        return d, p, q, sorted(px, key=Y)

    mid = n // 2
    mid_x = px[mid][0]
    if trace is not None:
        trace.append({"event": "split", "depth": depth, "n": n, "mid_x": mid_x})
    dl, pl, ql, ly = _solve(px[:mid], trace, depth + 1, base)
    dr, pr, qr, ry = _solve(px[mid:], trace, depth + 1, base)

    best = (dl, pl, ql) if dl <= dr else (dr, pr, qr)
    d = best[0]

    py = sorted(ly + ry, key=Y)

    strip = []
    improved = False
    if d > 0:  # if d == 0 nothing can beat it
        strip = [p for p in py if (p[0] - mid_x) ** 2 < d]
        for i in range(len(strip)):
            pi = strip[i]
            yi = pi[1]
            for j in range(i + 1, len(strip)):
                pj = strip[j]
                dy = pj[1] - yi
                if dy * dy >= d:
                    break
                dd = _dist2(pi, pj)
                if dd < d:
                    d = dd
                    best = (dd, pi, pj)
                    improved = True

    if trace is not None:
        trace.append({"event": "merge", "depth": depth, "n": n, "mid_x": mid_x,
                      "left_best": math.sqrt(dl), "right_best": math.sqrt(dr),
                      "delta": math.sqrt(min(dl, dr)),
                      "strip": list(strip), "improved": improved,
                      "best": (math.sqrt(best[0]), best[1], best[2])})

    return best[0], best[1], best[2], py


def closest_pair(points, trace=None, base=8):
    if len(points) < 2:
        raise ValueError("need at least 2 points")
    base = max(base, 3)
    px = sorted(points)  # sort by x once; y order is built by merging
    d, p, q, _ = _solve(px, trace, 0, base)
    return math.sqrt(d), p, q

def self_test(trials=300):
    rng = random.Random(1)
    for t in range(trials):
        n = rng.randint(2, 200)
        kind = t % 4
        if kind == 0:    # random reals
            pts = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
        elif kind == 1:  # tiny integer range -> duplicates and ties
            pts = [(rng.randrange(8), rng.randrange(8)) for _ in range(n)]
        elif kind == 2:  # vertical line
            pts = [(5, rng.uniform(0, 100)) for _ in range(n)]
        else:            # horizontal line
            pts = [(rng.uniform(0, 100), 5) for _ in range(n)]
        fast = closest_pair(pts)[0]
        slow = brute_force_closest(pts)[0]
        assert abs(fast - slow) < 1e-9, f"MISMATCH trial {t}: {fast} vs {slow}"
    print(f"self-test passed ({trials} random cases match brute force)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="input file, e.g. data/cp10.txt")
    ap.add_argument("--trace", action="store_true", help="record step-by-step events")
    ap.add_argument("--test", action="store_true", help="run self test vs brute force")
    args = ap.parse_args()

    if args.test:
        self_test()
    elif args.file:
        t0 = time.perf_counter()
        pts = read_points(args.file)
        t1 = time.perf_counter()
        steps = [] if args.trace else None
        d, p, q = closest_pair(pts, trace=steps)
        t2 = time.perf_counter()
        print(f"points   : {len(pts):,}")
        print(f"closest  : {p}  and  {q}")
        print(f"distance : {d}")
        print(f"read time: {t1 - t0:.3f}s   algorithm time: {t2 - t1:.3f}s")
        if steps is not None:
            print(f"trace    : {len(steps)} events recorded")
    else:
        ap.print_help()