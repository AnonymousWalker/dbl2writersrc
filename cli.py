#!/usr/bin/env python3
"""
Command-line interface for DBL to Writer Source converter
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our module
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbl2writersrc.usx_splitter import USXSplitter


def main():
    """Main CLI function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert DBL USX file to chunked files for Writer applications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert REV.usx using toc.yml to output directory
  python -m dbl2writersrc.cli REV.usx toc.yml output/
  
  # Convert with custom book code
  python -m dbl2writersrc.cli GEN.usx toc.yml output/ --book-code GEN
  
  # Convert with custom book title
  python -m dbl2writersrc.cli REV.usx toc.yml output/ --book-title "Book of Revelation"
        """
    )
    
    parser.add_argument('usx_file', help='Path to the input USX file')
    parser.add_argument('toc_file', help='Path to the TOC YAML file')
    parser.add_argument('output_dir', help='Path to the output directory')
    parser.add_argument('--book-code', default='REV', help='Book code for the USX file (default: REV)')
    parser.add_argument('--book-title', 
                       default='- Biblica® Open Vietnamese Contemporary Bible 2015 (Biblica® Thiên Ban Kinh Thánh Hiện Đại)', 
                       help='Book title for the USX file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not os.path.exists(args.usx_file):
        print(f"Error: USX file '{args.usx_file}' not found")
        sys.exit(1)
        
    if not os.path.exists(args.toc_file):
        print(f"Error: TOC file '{args.toc_file}' not found")
        sys.exit(1)
    
    # Create splitter and run
    try:
        splitter = USXSplitter(args.usx_file, args.toc_file, args.output_dir)
        splitter.run()
        print(f"\nConversion completed successfully!")
        print(f"Output files created in: {args.output_dir}")
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
