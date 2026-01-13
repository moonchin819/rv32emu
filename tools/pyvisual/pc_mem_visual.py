import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import argparse
import os

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

def plot_behavior(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error : Can't find file '{csv_path}', please check if the path is correct.")
        return
    # read data from csv file and automatically process the hexadecimal number and the scientific notation
    print(f"Reading data from {csv_path}...")

    try:
        df = pd.read_csv(csv_path, converters={
            'pc': hex_to_int,
            'addr': hex_to_int
        })
    except Exception as e:
        print(f'Read Failed : {e}')
        return

    df_zoom = df.head(50000)

    # Create a diagram panel
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    hex_formatter = ticker.FuncFormatter(lambda x, p: f'0x{int(x):08X}')

    # Plotting PC-over-time
    insn_df = df_zoom[df_zoom['type'] == 'I']
    ax1.scatter(insn_df['cycle'], insn_df['pc'], s=1, c='blue', alpha=0.6)
    ax1.set_ylabel("Program Counter (Hex)")
    ax1.set_title("PC-over-time Visualization (Dynamic Behavior for first 50k records)")
    ax1.yaxis.set_major_formatter(hex_formatter)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # Plotting Memory Access
    mem_df = df_zoom[df_zoom['type'] == 'M']
    if not mem_df.empty:
        ax2.scatter(mem_df['cycle'], mem_df['addr'], s=2, c='red', marker='x')
        ax2.set_ylabel("Memory Address (Hex)")
        ax2.set_xlabel("Execution Time (Cycles)")
        ax2.set_title("Memory Access Patterns (Spatial Distribution for first 50k records)")
        # if we want to look into data section
        # ax2.set_ylim(0, 0x100000) 
        # or look into stack section
        # choose only one
        ax2.yaxis.set_major_formatter(hex_formatter)

        ax2.set_ylim(0, 0x100000)
        ax2.grid(True, linestyle=':', alpha=0.5)

    # Manage the layout and save it as png.
    plt.tight_layout()
    output_name = csv_path.replace('.csv', '_zoom.png')
    plt.savefig(output_name, dpi=300)
    print(f"Done ! Please check {output_name}")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="history.csv", help="Default input path for CSV file.")
    args = parser.parse_args()
    plot_behavior(args.input)