#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_gprof2dot() -> str:
    """Locate gprof2dot.py script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gprof2dot_path = os.path.join(script_dir, "gprof2dot", "gprof2dot.py")
    
    if not os.path.exists(gprof2dot_path):
        print(f"Error: gprof2dot.py not found at: {gprof2dot_path}", file=sys.stderr)
        print("Please ensure gprof2dot is installed in tools/gprof2dot/", file=sys.stderr)
        sys.exit(1)
    
    return gprof2dot_path


def run_command(cmd: list, description: str):
    """Execute a command and handle errors."""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error during {description}:", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        raise
    except FileNotFoundError as e:
        print(f"Error: Command not found - {cmd[0]}", file=sys.stderr)
        if cmd[0] == "dot":
            print("Please install Graphviz:", file=sys.stderr)
            print("  Ubuntu/Debian: sudo apt install graphviz", file=sys.stderr)
            print("  macOS: brew install graphviz", file=sys.stderr)
        raise


def generate_dot_file(input_file: str, output_file: str, gprof2dot_path: str):
    """Generate DOT file from folded callstack using gprof2dot."""
    cmd = [
        "python3",
        gprof2dot_path,
        "-f", "collapse",  # Input format: folded/collapsed stack
        "-o", output_file,
        input_file
    ]
    
    print(f"Generating DOT file: {output_file}")
    run_command(cmd, "gprof2dot execution")
    print(f"✓ DOT file created: {output_file}")


def render_graph(dot_file: str, output_format: str, output_file: str):
    """Render DOT file to specified format using Graphviz."""
    cmd = [
        "dot",
        f"-T{output_format}",
        dot_file,
        "-o", output_file
    ]
    
    print(f"Rendering {output_format.upper()}: {output_file}")
    run_command(cmd, f"dot rendering to {output_format}")
    print(f"✓ {output_format.upper()} created: {output_file}")


def auto_generate_output_path(input_path: str) -> str:
    """Generate output path based on input filename.
    
    Example:
        callstack_folded_inst.txt -> call_graph_inst.dot
        trace.txt -> call_graph_trace.dot
    """
    input_pathobj = Path(input_path)
    base_name = input_pathobj.stem
    
    # Try to extract type from "folded_XXX" pattern
    if "folded_" in base_name:
        parts = base_name.split("folded_", 1)
        if len(parts) == 2:
            stack_type = parts[1]
            output_name = f"call_graph_{stack_type}.dot"
        else:
            output_name = f"call_graph_{base_name}.dot"
    else:
        output_name = f"call_graph_{base_name}.dot"
    
    # Place in same directory as input
    output_path = input_pathobj.parent / output_name
    return str(output_path)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate call graphs from folded callstack traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate only .dot file
  %(prog)s callstack_folded_inst.txt
  
  # Generate .dot and .svg
  %(prog)s callstack_folded_inst.txt --svg
  
  # Generate all formats
  %(prog)s callstack_folded_inst.txt --svg --png --pdf
  
  # Specify custom output path
  %(prog)s trace.txt -o output/graph.dot --svg

Note:
  This script uses gprof2dot.py (LGPL v3) and Graphviz dot for rendering.
  Make sure both are available in your system.
        """
    )
    
    parser.add_argument(
        "input",
        help="Input file in folded callstack format"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output .dot file path (default: auto-generated based on input name)"
    )
    parser.add_argument(
        "--svg",
        action="store_true",
        help="Also generate SVG output"
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also generate PNG output"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also generate PDF output"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Locate gprof2dot
    gprof2dot_path = find_gprof2dot()
    
    # Determine output path
    if args.output:
        dot_output = args.output
    else:
        dot_output = auto_generate_output_path(args.input)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(dot_output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate DOT file using gprof2dot
    generate_dot_file(args.input, dot_output, gprof2dot_path)
    
    # Render to additional formats if requested
    dot_path_obj = Path(dot_output)
    formats_to_render = []
    
    for fmt in ["svg", "png", "pdf"]:
        if getattr(args, fmt):
            output_file = str(dot_path_obj.with_suffix(f".{fmt}"))
            render_graph(dot_output, fmt, output_file)
    
    print("\n✓ All done!")


if __name__ == "__main__":
    main()

