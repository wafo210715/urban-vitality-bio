"""
Phase 1 Complete Automation Runner

Step 1: Download photos (automate_phase1.py)
Step 2: Analyze with MCP (Claude Code)
Step 3: Compile report (mcp_analyze_photos.py)

Usage:
    python run_phase1.py --download          # Step 1 only
    python run_phase1.py --analyze           # Show pending for analysis
    python run_phase1.py --report            # Step 3 only
    python run_phase1.py --all               # Run all steps
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import subprocess
import argparse


def step1_download():
    """Download photos for Phase 1 restaurants"""
    print("\n" + "=" * 60)
    print("STEP 1: DOWNLOADING PHOTOS")
    print("=" * 60)

    from automate_phase1 import Phase1Automation

    # Set API key via environment variable: export GOOGLE_PLACES_API_KEY=your_key
    if not os.environ.get('GOOGLE_PLACES_API_KEY'):
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable not set")
        return

    automation = Phase1Automation(
        budget_limit=385.0,
        max_photos_per_restaurant=5
    )

    automation.run(limit=None)


def step2_analyze():
    """Show pending restaurants for MCP analysis"""
    print("\n" + "=" * 60)
    print("STEP 2: MCP ANALYSIS")
    print("=" * 60)

    subprocess.run([sys.executable, "batch_analyze_photos.py"])


def step3_report():
    """Compile final linked report"""
    print("\n" + "=" * 60)
    print("STEP 3: COMPILING REPORT")
    print("=" * 60)

    subprocess.run([sys.executable, "mcp_analyze_photos.py"])


def main():
    parser = argparse.ArgumentParser(description='Phase 1 Automation')
    parser.add_argument('--download', action='store_true', help='Step 1: Download photos')
    parser.add_argument('--analyze', action='store_true', help='Step 2: Show pending for MCP analysis')
    parser.add_argument('--report', action='store_true', help='Step 3: Compile report')
    parser.add_argument('--all', action='store_true', help='Run all steps')

    args = parser.parse_args()

    if args.all:
        step1_download()
        step2_analyze()
        step3_report()
    elif args.download:
        step1_download()
    elif args.analyze:
        step2_analyze()
    elif args.report:
        step3_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
