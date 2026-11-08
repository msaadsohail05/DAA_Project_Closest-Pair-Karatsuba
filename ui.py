import os
import glob
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog
from closest_pair import read_points, closest_pair
from karatsuba import read_numbers, karatsuba

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
STEP_MAX = 1000

def input_size(path):
    with open(path) as f:
        first = f.readline().strip()
        second = f.readline().strip()
    if len(second.split()) == 2:
        return "cp", int(first)
    return "im", max(len(first), len(second))


def short(s, keep=40):
    return s if len(s) <= 2 * keep + 5 else f"{s[:keep]} ... {s[-keep:]}"

def set_text(widget, msg):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", msg)
    widget.configure(state="disabled")

def run_job(path, out_q):
    try:
        kind, _ = input_size(path)
        name = os.path.basename(path)
        lines = [f"File      : {name}"]
        if kind == "cp":
            t0 = time.perf_counter()
            pts = read_points(path)
            t1 = time.perf_counter()
            d, p, q = closest_pair(pts)
            t2 = time.perf_counter()
            lines += [
                "Algorithm : Closest pair of points (divide and conquer, O(n log n))",
                f"Points    : {len(pts):,}",
                f"Closest   : {p}",
                f"      and : {q}",
                f"Distance  : {d}",
                "",
                f"Read time      : {t1 - t0:.3f} s",
                f"Algorithm time : {t2 - t1:.3f} s",
            ]
        else:
            t0 = time.perf_counter()
            a, b = read_numbers(path)
            t1 = time.perf_counter()
            prod = karatsuba(a, b)
            t2 = time.perf_counter()
            s = str(prod)
            t3 = time.perf_counter()
            lines += [
                "Algorithm : Karatsuba integer multiplication",
                f"Digits    : {len(str(a)):,} x {len(str(b)):,}",
                f"Product   : {short(s)}",
                f"Product digits : {len(s):,}",
                "",
                f"Read + convert time : {t1 - t0:.3f} s",
                f"Multiply time       : {t2 - t1:.3f} s",
                f"To-string time      : {t3 - t2:.3f} s",
            ]
        out_q.put(("ok", "\n".join(lines)))
    except Exception as e:
        out_q.put(("error", f"Error: {e}"))

class StepNav:
    def build_bar(self):
        bar = ttk.Frame(self, padding=6)
        bar.pack()
        ttk.Button(bar, text="|< Reset", command=self.reset).pack(side="left", padx=3)
        ttk.Button(bar, text="< Back", command=lambda: self.go(-1)).pack(side="left", padx=3)
        self.pos = tk.StringVar()
        ttk.Label(bar, textvariable=self.pos, width=16, anchor="center").pack(side="left")
        ttk.Button(bar, text="Next >", command=lambda: self.go(1)).pack(side="left", padx=3)
        self.play_btn = ttk.Button(bar, text="Play", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=10)
        self.bind("<Left>", lambda e: self.go(-1))
        self.bind("<Right>", lambda e: self.go(1))
        self.protocol("WM_DELETE_WINDOW", self.close)

    def go(self, d):
        self.i = min(max(self.i + d, 0), len(self.steps) - 1)
        self.render()

    def reset(self):
        self.i = 0
        self.render()

    def toggle_play(self):
        self.playing = not self.playing
        self.play_btn.configure(text="Pause" if self.playing else "Play")
        if self.playing:
            if self.i >= len(self.steps) - 1:
                self.i = 0
                self.render()
            self.after(self.delay, self._tick)

    def _tick(self):
        if not self.playing:
            return
        if self.i < len(self.steps) - 1:
            self.go(1)
            self.after(self.delay, self._tick)
        else:
            self.playing = False
            self.play_btn.configure(text="Play")

    def close(self):
        self.playing = False
        self.destroy()

class ClosestPairSteps(StepNav, tk.Toplevel):
    W, H, PAD = 700, 440, 30

    def __init__(self, master, points, name):
        super().__init__(master)
        self.title(f"Closest pair, step by step: {name}")
        self.px = sorted(points)          # same order the algorithm uses
        self.steps = []
        closest_pair(points, trace=self.steps)
        self.ranges = self._compute_ranges()
        self.i = 0
        self.playing = False
        self.delay = 500

        self.x0, self.x1 = self.px[0][0], self.px[-1][0]
        ys = [p[1] for p in self.px]
        self.y0, self.y1 = min(ys), max(ys)

        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg="white",
                                highlightthickness=1, highlightbackground="#999")
        self.canvas.pack(padx=10, pady=(10, 4))
        ttk.Label(self, text="gray = all points   blue = current subproblem   "
                             "orange = strip   red dashed = dividing line   "
                             "green = best pair").pack()
        self.build_bar()
        self.desc = tk.Text(self, height=8, width=90, wrap="word",
                            font=("Consolas", 10), state="disabled")
        self.desc.pack(padx=10, pady=(0, 10), fill="x")
        self.render()

    def _compute_ranges(self):
        ranges = []
        pending = [(0, len(self.px))]
        open_nodes = []
        for ev in self.steps:
            if ev["event"] == "split":
                lo, hi = pending.pop()
                mid = lo + (hi - lo) // 2
                ranges.append((lo, hi))
                open_nodes.append((lo, hi))
                pending.append((mid, hi))  
                pending.append((lo, mid)) 
            elif ev["event"] == "base":
                ranges.append(pending.pop())
            else:  # merge
                ranges.append(open_nodes.pop())
        return ranges

    def sx(self, x):
        r = self.x1 - self.x0
        if r == 0:
            return self.W / 2
        return self.PAD + (x - self.x0) / r * (self.W - 2 * self.PAD)

    def sy(self, y):
        r = self.y1 - self.y0
        if r == 0:
            return self.H / 2
        return self.H - self.PAD - (y - self.y0) / r * (self.H - 2 * self.PAD)

    def dot(self, p, r, color):
        x, y = self.sx(p[0]), self.sy(p[1])
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")

    def ring(self, p):
        x, y = self.sx(p[0]), self.sy(p[1])
        self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7, outline="#1a9850", width=2)

    def render(self):
        c = self.canvas
        c.delete("all")
        ev = self.steps[self.i]
        lo, hi = self.ranges[self.i]
        sub = self.px[lo:hi]
        top, bot = self.PAD / 2, self.H - self.PAD / 2

        c.create_rectangle(self.sx(sub[0][0]) - 6, top, self.sx(sub[-1][0]) + 6, bot,
                           fill="#eef4ff", outline="#b9c8ee")
        # strip band
        if ev["event"] == "merge":
            d = ev["delta"]
            c.create_rectangle(self.sx(ev["mid_x"] - d), top, self.sx(ev["mid_x"] + d), bot,
                               fill="#fff0d0", outline="#f0c070")
        for p in self.px:
            self.dot(p, 2.5, "#aaaaaa")
        for p in sub:
            self.dot(p, 3.5, "#2b6cd4")
        if ev["event"] == "merge":
            for p in ev["strip"]:
                self.dot(p, 5, "#f08c00")
        if ev["event"] in ("split", "merge"):
            x = self.sx(ev["mid_x"])
            c.create_line(x, top, x, bot, fill="#d62828", dash=(5, 3), width=2)
        if ev["event"] in ("base", "merge"):
            d, p, q = ev["best"]
            c.create_line(self.sx(p[0]), self.sy(p[1]), self.sx(q[0]), self.sy(q[1]),
                          fill="#1a9850", width=3)
            self.ring(p)
            self.ring(q)

        self.pos.set(f"Step {self.i + 1} / {len(self.steps)}")
        set_text(self.desc, self.describe(ev))

    def describe(self, ev):
        N = len(self.steps)
        head = f"Step {self.i + 1} of {N}   (recursion depth {ev['depth']})\n\n"
        if ev["event"] == "split":
            n = ev["n"]
            body = (f"DIVIDE: {n} points, sorted by x. Split at the median x = "
                    f"{ev['mid_x']:.2f} into a left half of {n // 2} points and a right "
                    f"half of {n - n // 2} points, then solve each half recursively.")
        elif ev["event"] == "base":
            d, p, q = ev["best"]
            body = (f"BASE CASE: only {len(ev['points'])} points here, so brute force checks "
                    f"every pair. Closest pair in this group: {p} and {q}, distance {d:.4f}.")
        else:
            d, p, q = ev["best"]
            found = ("A closer pair across the line was found."
                     if ev["improved"] else "No closer pair across the line.")
            body = (f"COMBINE ({ev['n']} points): best in left half = "
                    f"{ev['left_best']:.4f}, best in right half = {ev['right_best']:.4f}, "
                    f"so delta = {ev['delta']:.4f}. Only points within delta of the red line "
                    f"(the orange strip, {len(ev['strip'])} points) can form a closer pair "
                    f"across the line; each is compared with the next few points above it in "
                    f"y. {found} Best for these {ev['n']} points: {p} and {q}, "
                    f"distance {d:.4f}.")
        if self.i == N - 1:
            d, p, q = ev["best"]
            body += f"\n\nDONE. Closest pair: {p} and {q}, distance {d:.6f}."
        return head + body

class KaratsubaSteps(StepNav, tk.Toplevel):
    def __init__(self, master, a, b, name):
        super().__init__(master)
        self.title(f"Karatsuba, step by step: {name}")
        self.a, self.b = a, b
        self.steps = []
        self.result = karatsuba(a, b, trace=self.steps)
        self.ok = (self.result == a * b)
        self.lines = [self.line(ev) for ev in self.steps]
        self.i = 0
        self.playing = False
        self.delay = 400

        ttk.Label(self, text="Recursion log (indentation = recursion depth). "
                             "The highlighted line is the current step.").pack(
                                 anchor="w", padx=10, pady=(10, 2))
        self.log = tk.Text(self, height=13, width=100, wrap="none",
                           font=("Consolas", 9), state="disabled")
        self.log.tag_configure("cur", background="#cfe3ff")
        self.log.pack(padx=10, fill="x")
        self.build_bar()

        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        self.detail = tk.Text(frame, height=17, width=100, wrap="char",
                              font=("Consolas", 9), state="disabled")
        sb = ttk.Scrollbar(frame, command=self.detail.yview)
        self.detail.configure(yscrollcommand=sb.set)
        self.detail.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.render()

    def line(self, ev):
        ind = "    " * ev["depth"]
        tag = ev["role"].split(" ")[0]          # root, z2, z0, z3
        if ev["event"] == "split":
            return (f"{ind}[{tag}] split: {len(str(ev['x']))}-digit x "
                    f"{len(str(ev['y']))}-digit, m = {ev['m']}")
        if ev["event"] == "base":
            return (f"{ind}[{tag}] base: {short(str(ev['x']), 8)} * {short(str(ev['y']), 8)} "
                    f"= {short(str(ev['product']), 8)}")
        return f"{ind}[{tag}] combine -> {short(str(ev['product']), 10)}"

    def render(self):
        ev = self.steps[self.i]
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        for k in range(self.i + 1):
            if k == self.i:
                self.log.insert("end", self.lines[k] + "\n", "cur")
            else:
                self.log.insert("end", self.lines[k] + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.pos.set(f"Step {self.i + 1} / {len(self.steps)}")
        set_text(self.detail, self.describe(ev))

    def describe(self, ev):
        N = len(self.steps)
        head = f"Step {self.i + 1} of {N}   depth {ev['depth']}   [{ev['role']}]\n\n"
        if ev["event"] == "split":
            body = (
                "DIVIDE\n"
                f"  x = {ev['x']}\n"
                f"  y = {ev['y']}\n\n"
                f"The longer number has n = {ev['n']} digits, so split both at m = {ev['m']} "
                f"digits from the right:\n"
                f"  x = xh*10^m + xl\n    xh = {ev['xh']}\n    xl = {ev['xl']}\n"
                f"  y = yh*10^m + yl\n    yh = {ev['yh']}\n    yl = {ev['yl']}\n\n"
                "Only 3 recursive multiplications are needed instead of 4:\n"
                "  z2 = xh*yh\n"
                "  z0 = xl*yl\n"
                f"  z3 = (xh+xl)*(yh+yl)\n    xh+xl = {ev['sx']}\n    yh+yl = {ev['sy']}")
        elif ev["event"] == "base":
            body = (
                "BASE CASE: the smaller number has at most 20 digits, so ordinary "
                "(schoolbook) multiplication is used.\n"
                f"  x = {ev['x']}\n"
                f"  y = {ev['y']}\n"
                f"  x * y = {ev['product']}")
        else:
            body = (
                "COMBINE\n"
                f"  z2 = {ev['z2']}\n"
                f"  z0 = {ev['z0']}\n"
                f"  z3 = {ev['z3']}\n\n"
                "The middle term xh*yl + xl*yh equals z3 - z2 - z0:\n"
                f"  z1 = {ev['z1']}\n\n"
                f"product = z2*10^(2m) + z1*10^m + z0   (m = {ev['m']})\n"
                f"        = {ev['product']}")
        if self.i == N - 1:
            body += (f"\n\nDONE. Final product = {self.result}\n"
                     f"Check against Python's built-in a*b: {'OK' if self.ok else 'MISMATCH'}")
        return head + body

class App:
    def __init__(self, root):
        self.root = root
        root.title("Divide and Conquer: Closest Pair and Karatsuba")
        root.geometry("820x540")

        self.paths = {}          
        self.out_q = queue.Queue()
        self.busy = False
        self.ran_path = None     
        self.job_path = None

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Input file:").pack(side="left")
        self.file_var = tk.StringVar()
        self.combo = ttk.Combobox(top, textvariable=self.file_var, width=22, state="readonly")
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.on_select())
        ttk.Button(top, text="Browse...", command=self.browse).pack(side="left")
        self.run_btn = ttk.Button(top, text="Run", command=self.run)
        self.run_btn.pack(side="left", padx=10)
        self.step_btn = ttk.Button(top, text="Show step by step", command=self.show_steps,
                                   state="disabled")
        self.step_btn.pack(side="left")

        self.status = tk.StringVar(value="Pick a file and press Run.")
        ttk.Label(root, textvariable=self.status, padding=(10, 0)).pack(anchor="w")
        self.hint = tk.StringVar()
        ttk.Label(root, textvariable=self.hint, foreground="#666666",
                  padding=(10, 0)).pack(anchor="w")
        self.bar = ttk.Progressbar(root, mode="indeterminate")
        self.bar.pack(fill="x", padx=10, pady=6)

        frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, font=("Consolas", 10), wrap="word", state="disabled")
        sb = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.load_files()

    def load_files(self):
        files = sorted(glob.glob(os.path.join(DATA_DIR, "cp[0-9][0-9].txt")) +
                       glob.glob(os.path.join(DATA_DIR, "im[0-9][0-9].txt")))
        for f in files:
            self.paths[os.path.basename(f)] = f
        self.combo["values"] = list(self.paths)
        if self.paths:
            self.combo.current(0)
        else:
            set_text(self.text, "No files found in the data folder.\n"
                                "Run  python generator.py  first, or use Browse...")
        self.update_step_button()

    def browse(self):
        f = filedialog.askopenfilename(initialdir=DATA_DIR, filetypes=[("Text files", "*.txt")])
        if f:
            name = os.path.basename(f)
            self.paths[name] = f
            self.combo["values"] = list(self.paths)
            self.file_var.set(name)
            self.on_select()

    def on_select(self):
        self.ran_path = None
        set_text(self.text, "")
        self.status.set("Press Run.")
        self.update_step_button()

    def update_step_button(self):
        if self.busy:
            self.step_btn.configure(state="disabled")
            return
        state, hint = "disabled", ""
        path = self.paths.get(self.file_var.get())
        if path:
            try:
                kind, size = input_size(path)
            except Exception:
                kind, size = None, None
            unit = "points" if kind == "cp" else "digits"
            if size is None:
                hint = "Could not read this file."
            elif size > STEP_MAX:
                hint = (f"Large input ({size:,} {unit}): only the final result and the "
                        f"running time are shown. Step by step is for inputs of up to "
                        f"{STEP_MAX:,} {unit}.")
            elif self.ran_path != path:
                hint = "Run the algorithm first, then press 'Show step by step'."
            else:
                state = "normal"
                hint = "Done. Press 'Show step by step' to watch how the algorithm worked."
        self.step_btn.configure(state=state)
        self.hint.set(hint)

    def run(self):
        name = self.file_var.get()
        if self.busy or not name:
            return
        path = self.paths[name]
        self.busy = True
        self.job_path = path
        self.ran_path = None
        self.run_btn.configure(state="disabled")
        self.step_btn.configure(state="disabled")
        set_text(self.text, "")
        self.status.set(f"Running {name} ... (the biggest files take 10-20 seconds)")
        self.bar.start(12)
        self.started = time.perf_counter()
        threading.Thread(target=run_job, args=(path, self.out_q), daemon=True).start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            kind, msg = self.out_q.get_nowait()
        except queue.Empty:
            self.root.after(100, self.poll)
            return
        self.bar.stop()
        self.busy = False
        self.run_btn.configure(state="normal")
        total = time.perf_counter() - self.started
        if kind == "ok":
            self.ran_path = self.job_path
            self.status.set(f"Finished in {total:.2f} s (including reading the file)")
        else:
            self.status.set("Failed")
        set_text(self.text, msg)
        self.update_step_button()

    def show_steps(self):
        name = self.file_var.get()
        path = self.paths.get(name)
        if self.busy or not path:
            return
        try:
            kind, _ = input_size(path)
            if kind == "cp":
                ClosestPairSteps(self.root, read_points(path), name)
            else:
                a, b = read_numbers(path)
                KaratsubaSteps(self.root, a, b, name)
            self.status.set("Step-by-step window opened.")
        except Exception as e:
            self.status.set("Failed")
            set_text(self.text, f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

