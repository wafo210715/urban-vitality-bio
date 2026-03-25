"""
Batch MCP Analyzer - Coordinator Script
Outputs pending photos for Claude Code to analyze with MCP tools
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import argparse
from pathlib import Path
from typing import List, Dict

from mcp_batch_processor import get_pending_restaurants, save_analysis_report

PHOTO_DIR = Path("cache/restaurant_photos/photos")


def main():
    parser = argparse.ArgumentParser(description='Batch photo analysis coordinator')
    parser.add_argument('--limit', type=int, default=10, help='Max restaurants')
    parser.add_argument('--farm', type=int, help='Filter by farm ID')
    parser.add_argument('--output', type=str, default='pending_batch.json', help='Output file')
    parser.add_argument('--save-report', action='store_true', help='Save report from stdin')

    args = parser.parse_args()

    # Save report mode - read analysis from stdin
    if args.save_report:
        import sys
        data = json.load(sys.stdin)
        restaurant = data['restaurant']
        analyses = data['analyses']
        report = save_analysis_report(restaurant, analyses)
        print(f"Saved report for: {report['name']}")
        return

    # Get pending restaurants
    pending = get_pending_restaurants()

    if not pending:
        print("No pending restaurants found!")
        return

    # Filter by farm
    if args.farm:
        pending = [r for r in pending if r['farm_id'] == args.farm]

    # Limit
    batch = pending[:args.limit]

    # Output batch info
    output = {
        'total_pending': len(pending),
        'batch_size': len(batch),
        'restaurants': []
    }

    for r in batch:
        rest_info = {
            'name': r['name'],
            'farm_id': r['farm_id'],
            'dir': r['dir'],
            'photos': r['photos'][:3],  # Max 3 photos
            'lat': r.get('lat'),
            'lon': r.get('lon'),
            'place_id': r.get('place_id')
        }
        output['restaurants'].append(rest_info)

    # Save batch file
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Batch saved to: {output_path}")
    print(f"Total pending: {len(pending)}")
    print(f"Batch size: {len(batch)}")

    # Print summary
    for r in batch:
        print(f"\n  Farm {r['farm_id']}: {r['name']}")
        for p in r['photos'][:3]:
            print(f"    - {Path(p).name}")


if __name__ == "__main__":
    main()
