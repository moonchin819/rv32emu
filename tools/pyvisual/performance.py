import matplotlib.pyplot as plt
import numpy as np
import re
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

def parse_prof_files():
    directory = os.path.abspath(os.path.join(script_dir, "..", "..", "build"))
    data = []

    if not os.path.exists(directory):
        print(f"Error : Directory '{directory}' not found.")
        return data

    # Search for all the files ending with '.prof' 
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and (filename.endswith(".prof") or "." not in filename):            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    cycles = re.search(r"Total Cycles:\s+(\d+)", content)
                    instrs = re.search(r"Total Instructions:\s+(\d+)", content)
                    cpi = re.search(r"Average CPI:\s+([\d.]+)", content)
                    
                    if cycles and instrs and cpi:
                        data.append({
                            'name': filename.replace('.prof', ''),
                            'cycles': int(cycles.group(1)),
                            'instructions': int(instrs.group(1)),
                            'cpi': float(cpi.group(1))
                        })
            except (IsADirectoryError, UnicodeDecodeError):
                continue
    return data

output_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "visualization"))

def plot_performance(data):
    if not data:
        print("No valid .prof files found.")
        return

    names = [d['name'] for d in data]
    instructions = [d['instructions'] for d in data]
    cycles = [d['cycles'] for d in data]
    cpi = [d['cpi'] for d in data]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left one shows the workload comparison
    x = np.arange(len(names))
    width = 0.35
    ax1.bar(x - width/2, instructions, width, label='Instructions', color='#3498db')
    ax1.bar(x + width/2, cycles, width, label='Cycles', color='#e74c3c')
    ax1.set_yscale('log')
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax1.set_title('Workload Scale (Log Scale)')
    ax1.legend()

    # Left one represents "Average CPI" comparison
    bars = ax2.bar(names, cpi, color=['#f1c40f', '#2ecc71', '#9b59b6', '#e67e22'][:len(names)])
    ax2.set_title('Average CPI (Efficiency)')
    ax2.set_ylim(0, max(cpi) * 1.2)
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height, f'{height:.3f}', 
                 ha='center', va='bottom', fontweight='bold')

    output_path = os.path.join(output_dir, "performance_summary.png")
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Successfully generated report from {len(names)} files.")

if __name__ == "__main__":
    prof_data = parse_prof_files()
    plot_performance(prof_data)