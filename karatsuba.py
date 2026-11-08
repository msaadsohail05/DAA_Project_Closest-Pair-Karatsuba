import argparse
import random
import sys
import time

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


def read_numbers(path):
    with open(path) as f:
        a = f.readline().strip()
        b = f.readline().strip()
    if not a.isdigit() or not b.isdigit():
        raise ValueError(f"{path}: expected two lines of decimal digits")
    return int(a), int(b)

def _kara(x, y, trace, depth, role, decimal, cutoff):
    if decimal:
        nx, ny = len(str(x)), len(str(y))
    else:
        nx, ny = x.bit_length(), y.bit_length()
    n = max(nx, ny)
    if min(nx, ny) <= cutoff:
        p = x * y
        if trace is not None:
            trace.append({"event": "base", "depth": depth, "role": role,
                          "x": x, "y": y, "product": p})
        return p
    m = n // 2
    if decimal:
        base = 10 ** m
        xh, xl = divmod(x, base)      # x = xh * 10^m + xl
        yh, yl = divmod(y, base)
    else:
        mask = (1 << m) - 1
        xh, xl = x >> m, x & mask     # x = xh * 2^m + xl  (linear time, no division)
        yh, yl = y >> m, y & mask
    sx, sy = xh + xl, yh + yl

    if trace is not None:
        trace.append({"event": "split", "depth": depth, "role": role, "x": x, "y": y,
                      "n": n, "m": m, "xh": xh, "xl": xl, "yh": yh, "yl": yl,
                      "sx": sx, "sy": sy})

    # Conquer: only THREE recursive multiplications instead of four
    z2 = _kara(xh, yh, trace, depth + 1, "z2 = xh*yh", decimal, cutoff)
    z0 = _kara(xl, yl, trace, depth + 1, "z0 = xl*yl", decimal, cutoff)
    z3 = _kara(sx, sy, trace, depth + 1, "z3 = (xh+xl)*(yh+yl)", decimal, cutoff)

    # Combine: xh*yl + xl*yh = z3 - z2 - z0
    z1 = z3 - z2 - z0
    if decimal:
        p = z2 * base * base + z1 * base + z0
    else:
        p = (z2 << (2 * m)) + (z1 << m) + z0

    if trace is not None:
        trace.append({"event": "merge", "depth": depth, "role": role, "m": m,
                      "z2": z2, "z0": z0, "z3": z3, "z1": z1, "product": p})
    return p


def karatsuba(x, y, trace=None, decimal=None, cutoff=None):    
    if x < 0 or y < 0:
        raise ValueError("non-negative integers only")
    if decimal is None:
        decimal = trace is not None
    if cutoff is None:
        cutoff = 20 if decimal else 2000
    cutoff = max(cutoff, 3)
    if trace is not None and max(x.bit_length(), y.bit_length()) > 20000:
        raise ValueError("trace is only for small inputs")
    return _kara(x, y, trace, 0, "root", decimal, cutoff)

def _rand_num(rng, d):
    return int(str(rng.randrange(1, 10)) + "".join(rng.choices("0123456789", k=d - 1)))


def self_test():
    rng = random.Random(7)
    cases = [(_rand_num(rng, rng.randint(1, 300)), _rand_num(rng, rng.randint(1, 300)))
             for _ in range(300)]
    cases += [(0, 12345), (12345, 0), (0, 0), (1, 10 ** 200), (10 ** 150, 10 ** 199),
              (10 ** 400, 10 ** 400), (10 ** 300 - 1, _rand_num(rng, 300)),
              (_rand_num(rng, 5), _rand_num(rng, 2000))]
    for x, y in cases:
        want = x * y
        assert karatsuba(x, y, decimal=False, cutoff=16) == want, f"binary mismatch {x} {y}"
        assert karatsuba(x, y, decimal=True, cutoff=5) == want, f"decimal mismatch {x} {y}"
        assert karatsuba(x, y) == want, f"default mismatch {x} {y}"
    for d in (5000, 20000, 20000):
        x, y = _rand_num(rng, d), _rand_num(rng, d)
        assert karatsuba(x, y) == x * y
    print(f"self-test passed ({len(cases) + 3} cases match built-in multiplication)")


def _show(s):
    return s if len(s) <= 100 else f"{s[:30]} ... {s[-30:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="input file, e.g. data/im10.txt")
    ap.add_argument("--trace", action="store_true", help="record step-by-step events")
    ap.add_argument("--verify", action="store_true", help="compare with built-in a*b")
    ap.add_argument("--out", help="write the full product to this file")
    ap.add_argument("--test", action="store_true", help="run self test")
    args = ap.parse_args()

    if args.test:
        self_test()
    elif args.file:
        t0 = time.perf_counter()
        a, b = read_numbers(args.file)
        t1 = time.perf_counter()
        steps = [] if args.trace else None
        p = karatsuba(a, b, trace=steps)
        t2 = time.perf_counter()
        s = str(p)
        t3 = time.perf_counter()

        print(f"a digits : {len(str(a)):,}")
        print(f"b digits : {len(str(b)):,}")
        print(f"product  : {_show(s)}")
        print(f"prod digs: {len(s):,}")
        print(f"read+convert time : {t1 - t0:.3f}s")
        print(f"multiply time     : {t2 - t1:.3f}s   <- the algorithm")
        print(f"to-string time    : {t3 - t2:.3f}s")
        if steps is not None:
            print(f"trace    : {len(steps)} events recorded")
        if args.verify:
            t4 = time.perf_counter()
            ok = (a * b == p)
            t5 = time.perf_counter()
            print(f"verify   : {'OK' if ok else 'MISMATCH'}   (built-in a*b took {t5 - t4:.3f}s)")
        if args.out:
            with open(args.out, "w") as f:
                f.write(s + "\n")
            print(f"saved    : {args.out}")
    else:
        ap.print_help()