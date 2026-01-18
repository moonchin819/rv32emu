import argparse
import os
import struct

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

def hex_to_int(x):
    try:
        x_str = str(x).strip()
        if x_str.lower().startswith('0x') or any(c in x_str.upper() for c in 'ABCDEF'):
            return int(x_str, 16)
        return int(float(x_str))
    except ValueError:
        try:
            return int(x_str, 16)
        except:
            return 0

def read_trace_bin(bin_path):
    with open(bin_path, 'rb') as f:
        header = f.read(12)
        if len(header) != 12 or header[:4] != b'RVTR':
            raise ValueError("Invalid trace header.")
        version, record_size = struct.unpack('<II', header[4:12])
        if version != 1 or record_size not in (20, 24):
            raise ValueError("Unsupported trace version or record size.")

        records = []
        while True:
            chunk = f.read(record_size)
            if not chunk:
                break
            if len(chunk) != record_size:
                raise ValueError("Truncated trace record.")
            if record_size == 20:
                cycle, pc, rec_type, addr = struct.unpack('<QIII', chunk)
            else:
                cycle, pc, rec_type, addr, _ = struct.unpack('<QIIII', chunk)
            type_char = 'I' if rec_type == 1 else 'M' if rec_type == 2 else 'U'
            records.append((cycle, pc, type_char, addr))

    return pd.DataFrame(records, columns=['cycle', 'pc', 'type', 'addr'])


def plot_behavior(input_path):
    if not os.path.exists(input_path):
        print(f"Error : Can't find file '{input_path}', please check if the path is correct.")
        return
    # read data from file and automatically process the hexadecimal number and the scientific notation
    print(f"Reading data from {input_path}...")

    try:
        if input_path.endswith('.bin'):
            df = read_trace_bin(input_path)
        else:
            df = pd.read_csv(input_path, converters={
                'pc': hex_to_int,
                'addr': hex_to_int
            })
    except Exception as e:
        print(f'Read Failed : {e}')
        return

    max_points = 500000

    def downsample(df_in, limit):
        if len(df_in) > limit:
            step = max(1, len(df_in) // limit)
            return df_in.iloc[::step].copy()
        return df_in

    insn_all = df[df['type'] == 'I']
    mem_all = df[df['type'] == 'M']
    insn_df = downsample(insn_all, max_points)
    segments = []
    if not mem_all.empty:
        low_max = 0x100000
        high_min = 0xFFFF0000
        addr_min = int(mem_all['addr'].min())
        addr_max = int(mem_all['addr'].max())

        if addr_min <= low_max:
            segments.append(("Low (0x00000000-0x00100000)", 0, low_max))
        if addr_max >= high_min:
            segments.append(("High (0xFFFF0000-0xFFFFFFFF)", high_min, 0xFFFFFFFF))

        low_mask = mem_all['addr'] <= low_max
        high_mask = mem_all['addr'] >= high_min
        mid_mask = ~(low_mask | high_mask)
        if mid_mask.any():
            mid_min = int(mem_all.loc[mid_mask, 'addr'].min())
            mid_max = int(mem_all.loc[mid_mask, 'addr'].max())
            segments.append((f"Mid (0x{mid_min:08X}-0x{mid_max:08X})", mid_min, mid_max))

        if not segments:
            segments.append((f"All (0x{addr_min:08X}-0x{addr_max:08X})", addr_min, addr_max))

    # Create a diagram panel
    rows = 1 + max(len(segments), 1)
    fig, axes = plt.subplots(rows, 1, figsize=(12, 4 + 3 * (rows - 1)), sharex=True)
    if rows == 1:
        axes = [axes]
    ax1 = axes[0]
    mem_axes = axes[1:]

    hex_formatter = ticker.FuncFormatter(lambda x, p: f'0x{int(x):08X}')

    # Plotting PC-over-time
    ax1.scatter(insn_df['cycle'], insn_df['pc'], s=1, c='blue', alpha=0.6)
    ax1.set_ylabel("Program Counter (Hex)")
    ax1.set_title("PC-over-time Visualization")
    ax1.yaxis.set_major_formatter(hex_formatter)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # Plotting Memory Access
    if not mem_all.empty:
        for ax, (label, lo, hi) in zip(mem_axes, segments):
            seg_all = mem_all[(mem_all['addr'] >= lo) & (mem_all['addr'] <= hi)]
            seg_df = downsample(seg_all, max_points)
            if seg_df.empty:
                continue
            ax.scatter(seg_df['cycle'], seg_df['addr'], s=2, c='red', marker='x')
            ax.set_ylabel("Memory Address (Hex)")
            ax.set_title(f"Memory Access Patterns ({label})")
            ax.yaxis.set_major_formatter(hex_formatter)
            ax.set_ylim(lo, hi)
            ax.grid(True, linestyle=':', alpha=0.5)
        if len(mem_axes) > 0:
            mem_axes[-1].set_xlabel("Execution Time (Cycles)")

    # Manage the layout and save it as png.
    plt.tight_layout()
    output_name = input_path.replace('.csv', '_zoom.png').replace('.bin', '_zoom.png')
    plt.savefig(output_name, dpi=300)
    print(f"Done ! Please check {output_name}")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="history.bin", help="Default input path for trace file.")
    args = parser.parse_args()
    plot_behavior(args.input)
