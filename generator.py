import argparse
import os
import random

SEEDS = {f"cp{i:02d}": 1000 + i for i in range(1, 11)}
SEEDS.update({f"im{i:02d}": 2000 + i for i in range(1, 11)})

LIMIT = 10 ** 6                
SUBMIT_LIMIT_BYTES = 1_000_000  

def uniform_points(rng, n):
    return [(rng.uniform(0, LIMIT), rng.uniform(0, LIMIT)) for _ in range(n)]

def clustered_points(rng, n, k=10, sigma=5000):
    centers = [(rng.uniform(0, LIMIT), rng.uniform(0, LIMIT)) for _ in range(k)]
    pts = []
    for _ in range(n):
        cx, cy = centers[rng.randrange(k)]
        x = min(max(rng.gauss(cx, sigma), 0), LIMIT)
        y = min(max(rng.gauss(cy, sigma), 0), LIMIT)
        pts.append((x, y))
    return pts


def duplicate_points(rng, n, side=500):
    return [(rng.randrange(side), rng.randrange(side)) for _ in range(n)]


def vertical_line_points(rng, n, x=500000):
    return [(x, rng.uniform(0, LIMIT)) for _ in range(n)]


def grid_points(rng, rows=250, cols=400, spacing=1000):
    pts = [(c * spacing, r * spacing) for r in range(rows) for c in range(cols)]
    rng.shuffle(pts)  # many tied closest pairs (all at distance = spacing)
    return pts

def across_middle_points(rng, side=1000, cell=1000, jitter=300):    
    mid_col = side // 2       
    row = rng.randrange(side)
    skip = {(mid_col - 1, row), (mid_col, row)}
    pts = []
    for i in range(side):
        for j in range(side):
            if (i, j) in skip:
                continue
            x = i * cell + cell / 2 + (rng.random() * 2 - 1) * jitter
            y = j * cell + cell / 2 + (rng.random() * 2 - 1) * jitter
            pts.append((x, y))
    y0 = row * cell + cell / 2
    pts.append((mid_col * cell - 0.5, y0))
    pts.append((mid_col * cell + 0.5, y0))
    rng.shuffle(pts)
    return pts


def small_points(rng, n=101):
    return [(round(rng.uniform(0, 1000), 2), round(rng.uniform(0, 1000), 2))
            for _ in range(n)]


def write_points(path, pts):
    with open(path, "w") as f:
        f.write(f"{len(pts)}\n")
        lines = []
        for x, y in pts:
            if isinstance(x, float) or isinstance(y, float):
                lines.append(f"{x:.6f} {y:.6f}")
            else:
                lines.append(f"{x} {y}")
        f.write("\n".join(lines))
        f.write("\n")

def random_digits(rng, d): 
    if d == 1:
        return str(rng.randrange(1, 10))
    return str(rng.randrange(1, 10)) + "".join(rng.choices("0123456789", k=d - 1))


def zero_heavy_digits(rng, d, p_zero=0.9):
    digits = ["0" if rng.random() < p_zero else str(rng.randrange(1, 10))
              for _ in range(d - 1)]
    return str(rng.randrange(1, 10)) + "".join(digits)


def write_numbers(path, a, b):
    with open(path, "w") as f:
        f.write(a + "\n" + b + "\n")

def build(name, out_dir):
    rng = random.Random(SEEDS[name])
    path = os.path.join(out_dir, name + ".txt")
    k = int(name[2:])

    if name.startswith("cp"):
        if k <= 4:
            pts = uniform_points(rng, 10 ** (2 + k))      
        elif k == 5:
            pts = clustered_points(rng, 1_000_000)
        elif k == 6:
            pts = duplicate_points(rng, 1_000_000)
        elif k == 7:
            pts = vertical_line_points(rng, 100_000)
        elif k == 8:
            pts = grid_points(rng)                          
        elif k == 9:
            pts = across_middle_points(rng)
        else:
            pts = small_points(rng, 101)
        write_points(path, pts)
    else:
        if k <= 4:
            d = 10 ** (2 + k)                             
            a, b = random_digits(rng, d), random_digits(rng, d)
        elif k == 5:
            a, b = random_digits(rng, 1_000_000), random_digits(rng, 10)
        elif k == 6:
            a, b = "9" * 100_000, random_digits(rng, 100_000)
        elif k == 7:
            a, b = zero_heavy_digits(rng, 99_999), zero_heavy_digits(rng, 99_999)
        elif k == 8:
            a = b = "1" + "0" * 999_999
        elif k == 9:
            a, b = "0", random_digits(rng, 1_000_000)
        else:
            a, b = random_digits(rng, 101), random_digits(rng, 101)
        write_numbers(path, a, b)
    return path


def generate_all(out_dir="data", names=None):
    os.makedirs(out_dir, exist_ok=True)
    names = names or sorted(SEEDS)
    for name in names:
        path = build(name, out_dir)
        size = os.path.getsize(path)
        tag = "submit" if size < SUBMIT_LIMIT_BYTES else "regenerate only"
        print(f"{name}: {size:>10,} bytes  ({tag})")

    with open(os.path.join(out_dir, "seeds.txt"), "w") as f:
        for name in sorted(SEEDS):
            f.write(f"{name} seed={SEEDS[name]}\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="e.g. cp05 im08 (default: all 20)")
    ap.add_argument("--out", default="data", help="output folder (default: data)")
    args = ap.parse_args()
    generate_all(args.out, args.names or None)