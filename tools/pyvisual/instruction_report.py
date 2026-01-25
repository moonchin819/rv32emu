import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Define categories and their color
INSN_GROUPS = {
    'Load': {'color': '#ff0088', 'insns': ['lb', 'lh', 'lw', 'lbu', 'lhu', 'clw', 'clwsp']},
    'Store': {'color': '#5555ff', 'insns': ['sb', 'sh', 'sw', 'csw', 'cswsp']},
    'Arithmetic': {'color': '#2ecc71', 'insns': ['and', 'or', 'andi', 'xori', 'srai', 'xor', 'add', 'addi', 'sub', 'sll', 'slli', 'lui', 'auipc', 'srli', 'sltu']},
    'Branch': {'color': '#f1c40f', 'insns': ['beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'cbeqz', 'cbnez']},
    'Jump': {'color': '#e67e22', 'insns': ['jal', 'jalr', 'cj', 'cjal', 'cjr', 'cjalr']},
    'Multiply': {'color': '#e74c3c', 'insns': ['mul', 'mulh', 'div', 'rem']},
    'System': {'color': '#95a5a6', 'insns': ['ecall', 'ebreak', 'csrrw', 'csrrs']},
    'FP-Mem': {'color': '#a29bfe', 'insns': ['flw', 'fsw', 'fld', 'fsd']},
}

""" Since the number is too large and the number on the bar chart with same height will overlap each other, 
    so I substitute 1,000,000 with M and 1,000 with K.
"""
def format_count(n):
    if n>= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    elif n >= 1_000:
        return f'{n / 1_000:.1f}K'
    return str(int(n))

"""
This function is used to handle instruction categories that have a small percentage but are greater than 0.
"""
def pct_format(pct):
    if 0 < pct < 1.0:
        return "<1.0%"
    return f"{pct:.1f}%"

def get_group_info(insn_name):
    for group, info in INSN_GROUPS.items():
        if insn_name in info['insns']:
            return group, info['color']
    return 'Other', '#bdc3c7'

def generate_png(prof_path, top_n):
    output_dir = "visualization"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory : {output_dir}")

    if not os.path.exists(prof_path):
        print(f"Error: {prof_path} not found.")
        return

    # Analyze the data
    data = []
    with open(prof_path, 'r') as f:
        start_parsing = False
        for line in f:
            if "Instruction" in line and "Count" in line:
                start_parsing = True
                continue
            if "===" in line and start_parsing: break
            if start_parsing and "|" in line:
                parts = line.split("|")
                name = parts[0].strip()
                count = int(parts[1].strip())
                group, color = get_group_info(name)
                data.append({'Instruction': name, 'Group': group, 'Count': count, 'Color': color})

    df = pd.DataFrame(data)
    

    # Plot settings
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 14))

    # Use a pie chart to show the proportion of each type of instruction.
    group_sums = df.groupby('Group')['Count'].sum()
    group_colors = [INSN_GROUPS[g]['color'] if g in INSN_GROUPS else '#bdc3c7' for g in group_sums.index]
    
    ax1.pie(group_sums, labels=group_sums.index, autopct=pct_format, startangle=140, colors=group_colors, explode=[0.05]*len(group_sums))
    ax1.set_title("Instruction Group Percentage", fontsize=16, fontweight='bold')

    # Use bar chart to show top N executed instruction
    topn = df.sort_values(by='Count', ascending=False).head(top_n)
    bars = ax2.bar(topn['Instruction'], topn['Count'], color=topn['Color'])
    ax2.set_title(f"Top {top_n} Executed Instructions", fontsize=16, fontweight='bold')
    ax2.set_ylabel("Execution Count")

    ax2.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax2.yaxis.get_major_formatter().set_scientific(False)
    ax2.yaxis.get_major_formatter().set_useOffset(False)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format_count(x)))
    ax2.tick_params(axis='x', rotation=45)

    # Add numerical labels above the bar chart
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height, format_count(height), ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    base_name = os.path.basename(prof_path).split('.')[0]
    output_png = os.path.join(output_dir, f"{base_name}_analysis.png")    
    plt.savefig(output_png, dpi=300)
    print(f"\nAnalysis PNG generated: {output_png}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input .prof file path.")
    parser.add_argument("--top", type=int, default=15,
                        help="Number of top instructions to show (default: 15).")
    args = parser.parse_args()
    generate_png(args.input, args.top)
