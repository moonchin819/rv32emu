#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List, Dict


class FlameGraphConfig:
    """Configuration for flame graph generation."""
    
    # Color schemes
    COLOR_SCHEMES = ['hot', 'mem', 'io', 'wakeup', 'chain', 'java', 
                     'js', 'perl', 'red', 'green', 'blue', 'aqua', 
                     'yellow', 'purple', 'orange']
    
    def __init__(self):
        self.title: Optional[str] = None
        self.subtitle: Optional[str] = None
        self.width: int = 1500
        self.height: int = 16
        self.color: str = 'hot'
        self.minwidth: str = '0.1'
        self.reverse: bool = False
        self.inverted: bool = False
    
    def to_args(self) -> List[str]:
        """Convert config to flamegraph.pl command line arguments."""
        args = []
        
        if self.title:
            args.extend(['--title', self.title])
        if self.subtitle:
            args.extend(['--subtitle', self.subtitle])
        
        args.extend(['--width', str(self.width)])
        args.extend(['--height', str(self.height)])
        args.extend(['--colors', self.color])
        args.extend(['--minwidth', self.minwidth])
        
        if self.reverse:
            args.append('--reverse')
        if self.inverted:
            args.append('--inverted')
        
        return args


class FlameGraphWrapper:
    """Wrapper for flamegraph.pl with enhanced features."""
    
    def __init__(self, flamegraph_pl_path: str):
        self.flamegraph_pl = flamegraph_pl_path
        if not os.path.exists(self.flamegraph_pl):
            raise FileNotFoundError(
                f"flamegraph.pl not found at: {self.flamegraph_pl}")
    
    def auto_detect_metadata(self, input_path: str) -> Dict[str, str]:
        """Auto-detect benchmark name and type from path."""
        path = Path(input_path)
        stem = path.stem  # filename without extension
        parent = path.parent.name
        
        metadata = {
            'benchmark': 'unknown',
            'trace_type': 'unknown'
        }
        
        # Try to extract benchmark name from directory
        if parent.startswith('out_'):
            # e.g., out_dhrystone_dhrystone -> dhrystone
            parts = parent.split('_')
            if len(parts) >= 2:
                metadata['benchmark'] = '_'.join(parts[1:])
        
        # Try to extract trace type from filename
        if 'folded' in stem:
            # e.g., callstack_folded_inst -> inst
            parts = stem.split('_')
            if 'folded' in parts:
                idx = parts.index('folded')
                if idx + 1 < len(parts):
                    metadata['trace_type'] = parts[idx + 1]
        
        return metadata
    
    def determine_output_path(self, input_path: str, 
                             output_path: Optional[str] = None) -> str:
        """Determine output file path."""
        if output_path:
            return output_path
        
        # Auto-generate output path
        path = Path(input_path)
        metadata = self.auto_detect_metadata(input_path)
        
        output_name = f"flamegraph_{metadata['trace_type']}.svg"
        return str(path.parent / output_name)
    
    def generate(self, input_path: str, output_path: Optional[str] = None,
                config: Optional[FlameGraphConfig] = None) -> bool:
        """Generate flame graph from folded callstack."""
        if not os.path.exists(input_path):
            print(f"Error: Input file not found: {input_path}", 
                  file=sys.stderr)
            return False
        
        # Setup config
        if config is None:
            config = FlameGraphConfig()
        
        # Auto-detect metadata for title/subtitle if not set
        if not config.title or not config.subtitle:
            metadata = self.auto_detect_metadata(input_path)
            if not config.title:
                config.title = metadata['benchmark']
            if not config.subtitle:
                config.subtitle = metadata['trace_type']
        
        # Determine output path
        output = self.determine_output_path(input_path, output_path)
        
        # Build command
        cmd = ['perl', self.flamegraph_pl, input_path]
        cmd.extend(config.to_args())
        
        # Execute
        try:
            print(f"Generating flame graph...")
            print(f"  Input:  {input_path}")
            print(f"  Output: {output}")
            print(f"  Title:  {config.title} - {config.subtitle}")
            
            with open(output, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE,
                                       text=True)
            
            if result.returncode != 0:
                print(f"Error: flamegraph.pl failed:", file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                return False
            
            # Get file size
            size = os.path.getsize(output)
            print(f"✓ Success! Generated {output} ({size:,} bytes)")
            return True
            
        except Exception as e:
            print(f"Error during generation: {e}", file=sys.stderr)
            return False
    
    def batch_generate(self, input_files: List[str], 
                      config: Optional[FlameGraphConfig] = None) -> int:
        """Generate flame graphs for multiple input files."""
        success_count = 0
        
        for i, input_file in enumerate(input_files, 1):
            print(f"\n[{i}/{len(input_files)}] Processing {input_file}")
            if self.generate(input_file, config=config):
                success_count += 1
        
        return success_count


def find_flamegraph_pl() -> Optional[str]:
    """Find flamegraph.pl in common locations."""
    script_dir = Path(__file__).parent
    
    # Search paths
    candidates = [
        script_dir / 'flamegraph.pl',
        script_dir / 'FlameGraph' / 'flamegraph.pl',
        Path.cwd() / 'tools' / 'flamegraph.pl',
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Generate flame graphs with automatic metadata detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with auto-detection
  %(prog)s callstack_folded_inst.txt
  
  # Custom output path
  %(prog)s input.txt -o custom_output.svg
  
  # Custom title and color scheme
  %(prog)s input.txt --title "My Benchmark" --color blue
  
  # Batch process multiple files
  %(prog)s out_*/callstack_folded_*.txt
  
  # Inverted (icicle) graph
  %(prog)s input.txt --inverted
        """)
    
    parser.add_argument('input', nargs='+', 
                       help='Input folded callstack file(s)')
    parser.add_argument('-o', '--output', 
                       help='Output SVG file (only for single input)')
    parser.add_argument('--flamegraph-pl', 
                       help='Path to flamegraph.pl (auto-detected if not specified)')
    
    # Graph customization
    parser.add_argument('--title', help='Graph title')
    parser.add_argument('--subtitle', help='Graph subtitle')
    parser.add_argument('--width', type=int, default=1200,
                       help='Image width (default: 1200)')
    parser.add_argument('--height', type=int, default=16,
                       help='Frame height (default: 16)')
    parser.add_argument('--color', choices=FlameGraphConfig.COLOR_SCHEMES,
                       default='hot', help='Color scheme (default: hot)')
    parser.add_argument('--minwidth', default='0.1',
                       help='Minimum frame width (default: 0.1)')
    
    # Graph options
    parser.add_argument('--reverse', action='store_true',
                       help='Generate reversed flame graph')
    parser.add_argument('--inverted', action='store_true',
                       help='Generate inverted (icicle) graph')
    
    args = parser.parse_args()
    
    # Find flamegraph.pl
    flamegraph_pl = args.flamegraph_pl or find_flamegraph_pl()
    if not flamegraph_pl:
        print("Error: Cannot find flamegraph.pl", file=sys.stderr)
        print("Please specify path with --flamegraph-pl", file=sys.stderr)
        sys.exit(1)
    
    # Create wrapper
    wrapper = FlameGraphWrapper(flamegraph_pl)
    
    # Setup config
    config = FlameGraphConfig()
    if args.title:
        config.title = args.title
    if args.subtitle:
        config.subtitle = args.subtitle
    config.width = args.width
    config.height = args.height
    config.color = args.color
    config.minwidth = args.minwidth
    config.reverse = args.reverse
    config.inverted = args.inverted
    
    # Check output option
    if args.output and len(args.input) > 1:
        print("Error: --output can only be used with single input file",
              file=sys.stderr)
        sys.exit(1)
    
    # Generate
    if len(args.input) == 1:
        success = wrapper.generate(args.input[0], args.output, config)
        sys.exit(0 if success else 1)
    else:
        # Batch mode
        print(f"Batch processing {len(args.input)} file(s)...")
        success_count = wrapper.batch_generate(args.input, config)
        print(f"\n{'='*60}")
        print(f"Completed: {success_count}/{len(args.input)} successful")
        sys.exit(0 if success_count == len(args.input) else 1)


if __name__ == '__main__':
    main()

