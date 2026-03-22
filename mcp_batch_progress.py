"""
MCP Batch Analysis with Progress Tracking
- 记录分析进度到 progress.json
- 支持断点续传
- 记录失败项便于重试

Usage:
    python mcp_batch_progress.py status           # 查看进度
    python mcp_batch_progress.py next             # 获取下一批待分析
    python mcp_batch_progress.py mark-done <name> # 标记完成
    python mcp_batch_progress.py mark-fail <name> # 标记失败
    python mcp_batch_progress.py retry-failed     # 重试失败的
    python mcp_batch_progress.py reset            # 重置进度
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


PROGRESS_FILE = "cache/restaurant_photos/analysis_progress.json"
PHOTOS_DIR = "cache/restaurant_photos/photos"


def load_progress() -> Dict:
    """Load progress from file, create if not exists"""
    progress_path = Path(PROGRESS_FILE)
    if progress_path.exists():
        with open(progress_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'created': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat(),
        'completed': {},      # {restaurant_key: {timestamp, farm_id, photo_count}}
        'in_progress': {},    # {restaurant_key: {started_at, farm_id}}
        'failed': {},         # {restaurant_key: {error, timestamp, farm_id}}
        'skipped': {}         # {restaurant_key: {reason, farm_id}}
    }


def save_progress(progress: Dict):
    """Save progress to file"""
    progress_path = Path(PROGRESS_FILE)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress['last_updated'] = datetime.now().isoformat()
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def get_restaurant_key(farm_id: int, restaurant_name: str) -> str:
    """Generate unique key for restaurant"""
    return f"farm_{farm_id}/{restaurant_name}"


def get_all_restaurants() -> List[Dict]:
    """Get all restaurants with photos"""
    photos_dir = Path(PHOTOS_DIR)
    restaurants = []

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        try:
            farm_id = int(farm_dir.name.replace("farm_", ""))
        except ValueError:
            continue

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            restaurant_name = restaurant_dir.name
            photo_files = sorted(restaurant_dir.glob("photo_*.jpg"))

            if photo_files:
                restaurants.append({
                    'farm_id': farm_id,
                    'restaurant_name': restaurant_name,
                    'photo_count': len(photo_files),
                    'photo_files': [str(p) for p in photo_files],
                    'dir': str(restaurant_dir),
                    'key': get_restaurant_key(farm_id, restaurant_name)
                })

    return restaurants


def get_pending_restaurants(progress: Dict, restaurants: List[Dict]) -> List[Dict]:
    """Get restaurants not yet processed"""
    processed = set(progress['completed'].keys()) | \
                set(progress['in_progress'].keys()) | \
                set(progress['failed'].keys())

    return [r for r in restaurants if r['key'] not in processed]


def get_next_batch(progress: Dict, restaurants: List[Dict], batch_size: int = 5) -> List[Dict]:
    """Get next batch of restaurants to analyze"""
    pending = get_pending_restaurants(progress, restaurants)
    return pending[:batch_size]


def mark_in_progress(progress: Dict, restaurant: Dict):
    """Mark restaurant as in progress"""
    key = restaurant['key']
    progress['in_progress'][key] = {
        'started_at': datetime.now().isoformat(),
        'farm_id': restaurant['farm_id'],
        'restaurant_name': restaurant['restaurant_name'],
        'photo_count': restaurant['photo_count']
    }
    save_progress(progress)


def mark_completed(progress: Dict, restaurant: Dict, result: Optional[Dict] = None):
    """Mark restaurant as completed"""
    key = restaurant['key']

    # Remove from in_progress if exists
    if key in progress['in_progress']:
        del progress['in_progress'][key]

    # Remove from failed if exists (retry success)
    if key in progress['failed']:
        del progress['failed'][key]

    progress['completed'][key] = {
        'completed_at': datetime.now().isoformat(),
        'farm_id': restaurant['farm_id'],
        'restaurant_name': restaurant['restaurant_name'],
        'photo_count': restaurant['photo_count'],
        'result_summary': result
    }
    save_progress(progress)


def mark_failed(progress: Dict, restaurant: Dict, error: str):
    """Mark restaurant as failed"""
    key = restaurant['key']

    # Remove from in_progress
    if key in progress['in_progress']:
        del progress['in_progress'][key]

    progress['failed'][key] = {
        'failed_at': datetime.now().isoformat(),
        'farm_id': restaurant['farm_id'],
        'restaurant_name': restaurant['restaurant_name'],
        'error': error
    }
    save_progress(progress)


def mark_skipped(progress: Dict, restaurant: Dict, reason: str):
    """Mark restaurant as skipped"""
    key = restaurant['key']

    # Remove from in_progress
    if key in progress['in_progress']:
        del progress['in_progress'][key]

    progress['skipped'][key] = {
        'skipped_at': datetime.now().isoformat(),
        'farm_id': restaurant['farm_id'],
        'restaurant_name': restaurant['restaurant_name'],
        'reason': reason
    }
    save_progress(progress)


def reset_progress(progress: Dict, keep_completed: bool = True):
    """Reset progress, optionally keeping completed items"""
    if keep_completed:
        completed = progress.get('completed', {})
        progress = {
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'completed': completed,
            'in_progress': {},
            'failed': {},
            'skipped': {}
        }
    else:
        progress = {
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'completed': {},
            'in_progress': {},
            'failed': {},
            'skipped': {}
        }
    save_progress(progress)
    return progress


def sync_with_actual_files(progress: Dict, restaurants: List[Dict]) -> Dict:
    """Sync progress with actual files on disk"""
    # Check if completed restaurants still have analysis files
    actual_completed = set()
    for r in restaurants:
        analysis_path = Path(r['dir']) / "analysis_report.json"
        if analysis_path.exists():
            actual_completed.add(r['key'])

    # Add to completed if analysis file exists but not in progress
    for key in actual_completed:
        if key not in progress['completed']:
            # Find restaurant info
            for r in restaurants:
                if r['key'] == key:
                    progress['completed'][key] = {
                        'completed_at': 'synced_from_file',
                        'farm_id': r['farm_id'],
                        'restaurant_name': r['restaurant_name'],
                        'photo_count': r['photo_count']
                    }
                    break

    # Remove from failed/skipped if now completed
    for key in actual_completed:
        if key in progress['failed']:
            del progress['failed'][key]
        if key in progress['skipped']:
            del progress['skipped'][key]

    save_progress(progress)
    return progress


def get_status(progress: Dict, restaurants: List[Dict]) -> Dict:
    """Get detailed status"""
    pending = get_pending_restaurants(progress, restaurants)
    total_photos = sum(r['photo_count'] for r in restaurants)
    completed_photos = sum(
        progress['completed'][k].get('photo_count', 0)
        for k in progress['completed']
    )

    return {
        'total_restaurants': len(restaurants),
        'total_photos': total_photos,
        'completed': len(progress['completed']),
        'completed_photos': completed_photos,
        'in_progress': len(progress['in_progress']),
        'failed': len(progress['failed']),
        'skipped': len(progress['skipped']),
        'pending': len(pending),
        'progress_pct': round(len(progress['completed']) / len(restaurants) * 100, 1) if restaurants else 0
    }


def print_status(progress: Dict, restaurants: List[Dict]):
    """Print status summary"""
    status = get_status(progress, restaurants)

    print("=" * 60)
    print("MCP BATCH ANALYSIS PROGRESS")
    print("=" * 60)
    print(f"\nOverall Progress: {status['progress_pct']}%")
    print(f"  Total restaurants: {status['total_restaurants']}")
    print(f"  Total photos: {status['total_photos']}")
    print()
    print(f"  ✅ Completed: {status['completed']} ({status['completed_photos']} photos)")
    print(f"  ⏳ In Progress: {status['in_progress']}")
    print(f"  ❌ Failed: {status['failed']}")
    print(f"  ⏭️  Skipped: {status['skipped']}")
    print(f"  📋 Pending: {status['pending']}")
    print()

    # Show by farm
    print("By Farm:")
    by_farm = {}
    for r in restaurants:
        fid = r['farm_id']
        if fid not in by_farm:
            by_farm[fid] = {'total': 0, 'completed': 0, 'pending': 0}
        by_farm[fid]['total'] += 1
        if r['key'] in progress['completed']:
            by_farm[fid]['completed'] += 1
        elif r['key'] not in progress['failed'] and r['key'] not in progress['skipped']:
            by_farm[fid]['pending'] += 1

    for fid in sorted(by_farm.keys())[:15]:
        f = by_farm[fid]
        print(f"  Farm {fid}: {f['completed']}/{f['total']} done, {f['pending']} pending")

    if len(by_farm) > 15:
        print(f"  ... and {len(by_farm) - 15} more farms")

    # Show failed items
    if progress['failed']:
        print(f"\n❌ Failed items ({len(progress['failed'])}):")
        for key, info in list(progress['failed'].items())[:5]:
            print(f"  - {key}: {info.get('error', 'unknown error')}")
        if len(progress['failed']) > 5:
            print(f"  ... and {len(progress['failed']) - 5} more")


def print_next_batch(progress: Dict, restaurants: List[Dict], batch_size: int = 5):
    """Print next batch to analyze"""
    batch = get_next_batch(progress, restaurants, batch_size)

    if not batch:
        print("No pending restaurants!")
        return

    print("=" * 60)
    print(f"NEXT BATCH ({len(batch)} restaurants)")
    print("=" * 60)

    for i, r in enumerate(batch, 1):
        print(f"\n{i}. {r['restaurant_name']} (Farm {r['farm_id']})")
        print(f"   Photos: {r['photo_count']}")
        print(f"   Key: {r['key']}")
        print(f"   Dir: {r['dir']}")


def generate_mcp_prompt(batch: List[Dict]) -> str:
    """Generate prompt for MCP analysis"""
    prompt = "Analyze the following restaurant photos using MCP tools.\n\n"

    for r in batch:
        prompt += f"## {r['restaurant_name']} (Farm {r['farm_id']})\n"
        prompt += f"Directory: {r['dir']}\n"
        prompt += f"Photos ({r['photo_count']}):\n"
        for photo in r['photo_files']:
            prompt += f"- {photo}\n"
        prompt += "\n"

    prompt += """
For each photo, use the mcp__zai-mcp-server__analyze_image tool with this prompt:
"Analyze this food photo for an urban farming project in Singapore. Return JSON with:
- is_food: boolean
- dish_name: string
- cuisine_type: string
- visible_ingredients: list of strings
- farmable_in_singapore: {leafy_greens: [], herbs: [], aromatics: [], vegetables: []}
- growing_recommendations: {best_for_rooftop: [], best_for_podium: [], best_for_streetscape: [], quick_wins: []}"

After analyzing all photos for a restaurant, create an analysis_report.json in the restaurant directory.
"""
    return prompt


def main():
    # Load data
    progress = load_progress()
    restaurants = get_all_restaurants()

    # Sync with actual files
    progress = sync_with_actual_files(progress, restaurants)

    if len(sys.argv) < 2:
        command = 'status'
    else:
        command = sys.argv[1]

    if command == 'status':
        print_status(progress, restaurants)

    elif command == 'next':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print_next_batch(progress, restaurants, batch_size)

    elif command == 'prompt':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        batch = get_next_batch(progress, restaurants, batch_size)
        if batch:
            print(generate_mcp_prompt(batch))

    elif command == 'mark-done':
        if len(sys.argv) < 3:
            print("Usage: python mcp_batch_progress.py mark-done <restaurant_key>")
            return
        key = sys.argv[2]
        for r in restaurants:
            if r['key'] == key:
                mark_completed(progress, r)
                print(f"Marked as completed: {key}")
                break
        else:
            print(f"Restaurant not found: {key}")

    elif command == 'mark-fail':
        if len(sys.argv) < 3:
            print("Usage: python mcp_batch_progress.py mark-fail <restaurant_key> [error]")
            return
        key = sys.argv[2]
        error = sys.argv[3] if len(sys.argv) > 3 else "manual mark"
        for r in restaurants:
            if r['key'] == key:
                mark_failed(progress, r, error)
                print(f"Marked as failed: {key}")
                break
        else:
            print(f"Restaurant not found: {key}")

    elif command == 'retry-failed':
        # Move failed back to pending
        for key in list(progress['failed'].keys()):
            del progress['failed'][key]
        save_progress(progress)
        print(f"Cleared {len(progress['failed'])} failed items. They will be retried.")

    elif command == 'reset':
        keep = '--all' not in sys.argv
        progress = reset_progress(progress, keep_completed=keep)
        print("Progress reset." if not keep else "Progress reset (kept completed).")

    elif command == 'export':
        # Export to CSV
        rows = []
        for r in restaurants:
            key = r['key']
            status = 'pending'
            if key in progress['completed']:
                status = 'completed'
            elif key in progress['failed']:
                status = 'failed'
            elif key in progress['skipped']:
                status = 'skipped'
            elif key in progress['in_progress']:
                status = 'in_progress'

            rows.append({
                'farm_id': r['farm_id'],
                'restaurant_name': r['restaurant_name'],
                'photo_count': r['photo_count'],
                'status': status,
                'key': key
            })

        df = pd.DataFrame(rows)
        output = 'analysis_progress.csv'
        df.to_csv(output, index=False)
        print(f"Exported to {output}")

    else:
        print(f"Unknown command: {command}")
        print("Commands: status, next, prompt, mark-done, mark-fail, retry-failed, reset, export")


if __name__ == "__main__":
    main()
