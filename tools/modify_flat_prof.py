#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FlatRow:
    symbol: str
    self_count: int     # counts that the symbol is the leaf
    total_count: int     # counts that the symbol appears
    percent: float     # self counts / all samples * 100
    cum_percent: float     # cumulative percent
    self_time: Optional[float] = None  # self counts * sample time
    total_time: Optional[float] = None  # total counts * sample time


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()
"""
callstack_folded_inst.txt:
_start; 4
_start;memset; 720
_start;main;Proc0; 80000018

return:
[
    "_start; 4\n",
    "_start;memset; 720\n", 
    "_start;main;Proc0; 80000018\n"
]
"""

def parse_folded_line(line: str) -> Optional[Tuple[List[str], int]]:
    s = line.strip()    #remove whitespace at the beginning and end
    if not s:
        return None #return None, if the line is empty

    # split off the count (last whitespace-separated token)
    parts = s.rsplit(None, 1)   #split the line into two parts from the right by the first whitespace
    if len(parts) != 2:
        raise ValueError(f"bad line (missing count): {line!r}")
    stack_str, count_str = parts

    try:
        count = int(count_str)   
    except ValueError as e:
        raise ValueError(f"bad count: {count_str!r} in line: {line!r}") from e

    frames = [f for f in stack_str.split(";") if f]
    if not frames:
        raise ValueError(f"bad line (no frames): {line!r}")
    return frames, count
    """
    input : "_start;memset; 720"
    output : (["_start", "memset"], 720)
    """    


def accumulate(lines: Iterable[str]) -> Tuple[Counter, Counter, int]:
    """
    Returns (self_counts, total_counts, total_samples)
    """
    self_counts: Dict[str, int] = {}
    total_counts: Dict[str, int] = {}
    total_samples = 0

    for line in lines:
        parsed = parse_folded_line(line)   
        if parsed is None:
            continue
        frames, count = parsed      # read the frame and count
        total_samples += count      # total samples

        leaf = frames[-1]
        if leaf in self_counts:
            self_counts[leaf] += count
        else:
            self_counts[leaf] = count

        for frame in frames:
            if frame in total_counts:
                total_counts[frame] += count
            else:
                total_counts[frame] = count

    return self_counts, total_counts, total_samples
    """
    frames = ['_start', 'main', 'Proc0']
    count = 100
    self_counts = {..., 'Proc0': +100, ...}
    total_counts = {..., '_start': +100, 'main': +100, 'Proc0': +100, ...}
    total_samples += 100
    """


def _unit_scale_seconds(x: float) -> Tuple[float, str]:
    """
    Pick a readable unit for a duration in seconds.
    Returns (scaled_value, unit).
    """
    if x < 1e-3:
        return x * 1e6, "us"
    if x < 1.0:
        return x * 1e3, "ms"
    return x, "s"


def build_flat(
    self_counts: Counter,   # sysbol self count
    total_counts: Counter,  # symbol total count
    total_samples: int,    # total samples
    *,
    clk_mhz: Optional[float] = None,  # clock frequency in MHz
) -> Tuple[List[FlatRow], Dict[str, object]]:
    if total_samples <= 0:
        raise ValueError("no samples")

    rows = []
    for sym, self_c in self_counts.items():
        total_c = int(total_counts.get(sym, 0))  # get the total count of the symbol
        rows.append((sym, int(self_c), total_c))  # construct tuple : [('symbol1', self count 1, total count 1), ...]

    # sort by self desc, then name asc
    rows.sort(key=lambda t: (-t[1], t[0]))  # sort the rows by self count descending, then symbol ascending

    out: List[FlatRow] = []
    cum = 0.0

    use_time = clk_mhz is not None and clk_mhz > 0.0
    # If this trace is "cycles", you can treat each count as one cycle.
    # With clk in MHz, cycles per second = clk * 1e6, so:
    # seconds = cycles / (clk*1e6)
    denom = (clk_mhz * 1e6) if use_time else None

    for sym, self_c, total_c in rows:
        pct = (float(self_c) / float(total_samples)) * 100.0 # self count / total samples
        cum += pct
        if denom:
            self_s = float(self_c) / denom
            total_s = float(total_c) / denom
            out.append(
                FlatRow(
                    symbol=sym,
                    self_count=self_c,
                    total_count=total_c,
                    percent=pct,
                    cum_percent=cum,
                    self_time=self_s,
                    total_time=total_s,
                )
            )
        else:
            out.append(
                FlatRow(
                    symbol=sym,
                    self_count=self_c,
                    total_count=total_c,
                    percent=pct,
                    cum_percent=cum,
                )
            )

    meta: Dict[str, object] = {"total_samples": total_samples}
    if use_time and denom:
        total_time_s = float(total_samples) / denom
        meta["clk_mhz"] = float(clk_mhz)
        meta["total_time_s"] = total_time_s
    return out, meta
    """
    self_counts = Counter({'Proc0': 80000018, 'memset': 720, 'main': 1})
    total_counts = Counter({'_start': 80000743, 'main': 80000019, 'Proc0': 80000018, 'memset': 720})
    total_samples = 80000743
    clk_mhz = 100.0
    out = [
        FlatRow(symbol='Proc0', self_count=80000018, total_count=80000018, percent=100.0, cum_percent=100.0, self_time=0.8, total_time=0.8),
        FlatRow(symbol='memset', self_count=720, total_count=720, percent=0.0, cum_percent=100.0, self_time=0.0, total_time=0.0),
        FlatRow(symbol='main', self_count=1, total_count=1, percent=0.0, cum_percent=100.0, self_time=0.0, total_time=0.0),
    ]
    meta = {'total_samples': 80000743, 'clk_mhz': 100.0, 'total_time_s': 800007.43}
    """

def filter_rows(
    rows: Sequence[FlatRow],
    *,
    top: Optional[int],  # for output top N rows
    thr_percent: Optional[float],  # for output rows with self% >= thr
) -> List[FlatRow]:
    out = list(rows) # copy the rows
    if thr_percent is not None:
        out = [r for r in out if r.percent >= thr_percent]
    if top is not None:
        out = out[: max(0, int(top))]
    return out


def print_flat(rows: Sequence[FlatRow], meta: Dict[str, object]) -> None:
    use_time = any((r.self_time is not None) for r in rows)
    if use_time:
        # pick a unit based on the max self_time
        max_self_s = max((r.self_time or 0.0) for r in rows) if rows else 0.0  # find the max self time
        _, unit = _unit_scale_seconds(max_self_s)  # use max self time to pick a unit
        scale = {"us": 1e6, "ms": 1e3, "s": 1.0}[unit]
        header = (
            f"{'%':>6} {'cum%':>8} {'self':>12} {'total':>12} "
            f"{'self['+unit+']':>12} {'total['+unit+']':>12}  symbol"
        )  # construct the header
        print(header)
        for r in rows:
            st = (r.self_time or 0.0) * scale 
            tt = (r.total_time or 0.0) * scale
            print(
                f"{r.percent:6.2f} {r.cum_percent:8.2f} "
                f"{r.self_count:12d} {r.total_count:12d} "
                f"{st:12.3f} {tt:12.3f}  {r.symbol}"
            )
    else:
        header = f"{'%':>6} {'cum%':>8} {'self':>12} {'total':>12}  symbol"
        print(header)
        for r in rows:
            print(
                f"{r.percent:6.2f} {r.cum_percent:8.2f} "
                f"{r.self_count:12d} {r.total_count:12d}  {r.symbol}"
            )

    for k in ("total_samples", "clk_mhz", "total_time_s"):
        if k in meta:
            print(f"{k}: {meta[k]}")
"""
     %     cum%         self        total    self[ms]   total[ms]  symbol
100.00   100.00     80000018     80000018       0.800       0.800   Proc0
  0.00   100.00          720          720       0.000       0.000  memset
  0.00   100.00            1            1       0.000       0.000    main

total_samples: 80000743
clk_mhz: 100.0
total_time_s: 800007.43
"""

def write_csv(rows: Sequence[FlatRow], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "symbol",
                "percent",
                "cum_percent",
                "self_count",
                "total_count",
                "self_time_s",
                "total_time_s",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.symbol,
                    f"{r.percent:.6f}",
                    f"{r.cum_percent:.6f}",
                    r.self_count,
                    r.total_count,
                    "" if r.self_time is None else f"{r.self_time:.12g}",
                    "" if r.total_time is None else f"{r.total_time:.12g}",
                ]
            )


def maybe_plot(rows: Sequence[FlatRow], path: str, title: str) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "matplotlib not available; install it or skip --plot"
        ) from e

    labels = [r.symbol for r in rows][::-1]
    values = [r.percent for r in rows][::-1]

    fig_h = max(3.3, 0.33 * max(1, len(rows)))
    fig, ax = plt.subplots(1, 1, figsize=(7.5, fig_h), tight_layout=True)
    bars = ax.barh(labels, values, color="#7ed3ab")
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_xlabel("% of samples")
    ax.set_title(title)
    ax.margins(y=0.02)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def combine_inst_cycle(
    inst_rows: Sequence[FlatRow],
    inst_meta: Dict[str, object],
    cyc_rows: Sequence[FlatRow],
    cyc_meta: Dict[str, object],
    *,
    top: Optional[int],
    thr_percent_cycle: Optional[float],
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    inst_map = {r.symbol: r for r in inst_rows}
    cyc_map = {r.symbol: r for r in cyc_rows}
    syms = sorted(set(inst_map) | set(cyc_map))

    combined: List[Dict[str, object]] = []
    total_inst = int(inst_meta.get("total_samples", 0))
    total_cyc = int(cyc_meta.get("total_samples", 0))

    for sym in syms:
        ir = inst_map.get(sym)
        cr = cyc_map.get(sym)
        inst_total = int(ir.total_count) if ir else 0
        cyc_total = int(cr.total_count) if cr else 0
        cyc_pct = float(cr.percent) if cr else 0.0

        ipc = (float(inst_total) / float(cyc_total)) if cyc_total > 0 else None
        cpi = (float(cyc_total) / float(inst_total)) if inst_total > 0 else None

        combined.append(
            {
                "symbol": sym,
                "inst_self": int(ir.self_count) if ir else 0,
                "inst_total": inst_total,
                "inst_percent": float(ir.percent) if ir else 0.0,
                "cycle_self": int(cr.self_count) if cr else 0,
                "cycle_total": cyc_total,
                "cycle_percent": cyc_pct,
                "ipc": ipc,
                "cpi": cpi,
            }
        )

    # sort by cycle percent desc, then name asc
    combined.sort(key=lambda d: (-float(d["cycle_percent"]), str(d["symbol"])))
    if thr_percent_cycle is not None:
        combined = [d for d in combined if float(d["cycle_percent"]) >= thr_percent_cycle]
    if top is not None:
        combined = combined[: max(0, int(top))]

    meta = {
        "total_instructions": total_inst,
        "total_cycles": total_cyc,
        "CPI": (float(total_cyc) / float(total_inst)) if total_inst > 0 else None,
        "IPC": (float(total_inst) / float(total_cyc)) if total_cyc > 0 else None,
        "clk_mhz": cyc_meta.get("clk_mhz"),
        "total_time_s": cyc_meta.get("total_time_s"),
    }
    return combined, meta


def print_combined(rows: Sequence[Dict[str, object]], meta: Dict[str, object]) -> None:
    print(
        f"{'inst%':>7} {'cyc%':>7} {'inst_self':>10} {'inst_tot':>10} "
        f"{'cyc_self':>10} {'cyc_tot':>10} {'ipc':>8} {'cpi':>8}  symbol"
    )
    for r in rows:
        ipc = r["ipc"]
        cpi = r["cpi"]
        print(
            f"{float(r['inst_percent']):7.2f} {float(r['cycle_percent']):7.2f} "
            f"{int(r['inst_self']):10d} {int(r['inst_total']):10d} "
            f"{int(r['cycle_self']):10d} {int(r['cycle_total']):10d} "
            f"{'' if ipc is None else f'{ipc:.3f}':>8} "
            f"{'' if cpi is None else f'{cpi:.3f}':>8}  {r['symbol']}"
        )
    for k, v in meta.items():
        if v is not None:
            print(f"{k}: {v}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Summarize folded callstack samples into a flat profile (clean-room implementation)."
    )
    p.add_argument("-t", "--trace", required=True, help="Folded callstack trace path")
    p.add_argument(
        "-e",
        "--event",
        default="inst",
        help="Label only (e.g. inst/cycle/branch). Affects titles, not parsing.",
    )
    p.add_argument("-p", "--top", type=int, default=None, help="Keep only top N by self")
    p.add_argument(
        "--thr",
        type=float,
        default=None,
        help="Keep only rows with self%% >= thr (in percent, e.g. 1.0)",
    )
    p.add_argument(
        "--clk-mhz",
        type=float,
        default=None,
        help="If set, compute time assuming counts are cycles and clk is MHz",
    )
    p.add_argument("--csv", default=None, help="Write flat summary as CSV to this path")
    p.add_argument("--plot", action="store_true", help="Save a bar chart PNG (requires matplotlib)")
    p.add_argument(
        "--png",
        default=None,
        help="PNG output path (used only when --plot is set). Default: alongside trace",
    )
    p.add_argument(
        "-s",
        "--second-trace",
        default=None,
        help="Optional second trace to combine (typically cycles).",
    )
    p.add_argument(
        "--second-clk-mhz",
        type=float,
        default=None,
        help="Clock MHz for second trace (if you want time numbers there).",
    )
    p.add_argument(
        "--thr-cycle",
        type=float,
        default=None,
        help="When combining, filter by cycle%% threshold (percent).",
    )

    args = p.parse_args(argv)

    if not os.path.isfile(args.trace):
        print(f"trace not found: {args.trace}", file=sys.stderr)
        return 2

    t_self, t_total, t_sum = accumulate(_read_lines(args.trace))
    t_rows, t_meta = build_flat(t_self, t_total, t_sum, clk_mhz=args.clk_mhz)
    t_rows = filter_rows(t_rows, top=args.top, thr_percent=args.thr)

    if args.second_trace:
        if not os.path.isfile(args.second_trace):
            print(f"second trace not found: {args.second_trace}", file=sys.stderr)
            return 2

        s_self, s_total, s_sum = accumulate(_read_lines(args.second_trace))
        s_rows, s_meta = build_flat(
            s_self, s_total, s_sum, clk_mhz=args.second_clk_mhz
        )
        # For combining, we want full symbol set; apply filtering after combine.
        combined, meta = combine_inst_cycle(
            t_rows, t_meta, s_rows, s_meta, top=args.top, thr_percent_cycle=args.thr_cycle
        )
        print("Profile - combined (inst + second trace)")
        print_combined(combined, meta)
        return 0

    title = f"Profile - {args.event}"
    print(title)
    print_flat(t_rows, t_meta)

    if args.csv:
        write_csv(t_rows, args.csv)

    if args.plot:
        png = args.png
        if not png:
            base, _ = os.path.splitext(args.trace)
            png = base + f"_flat_{args.event}.png"
        maybe_plot(t_rows, png, title=title)
        print(f"plot saved: {png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


