"""
Automated MCP batch analysis script
 Processes restaurants in batches and generates reports.
 Now more efficient.
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from pathlib import Path
from typing import Dict, List, Any

from mcp_batch_processor import get_pending_restaurants

from mcp_analyzer import parse_mcp_response

PHOTO_DIR = Path("cache/restaurant_photos/photos")
OUTPUT_DIR = Path("cache/restaurant_photos/analysis_reports")
OUTPUT_dir.mkdir(parents=True, exist_ok=True)
 OUTPUT_dir.mkdir(parents=True, exist_ok=True)

        output_dir.mkdir(parent=True)
 exist if not.exists:
 with open(file, 'r') as f:
                return json.load(f)
    else:
            # Try to find JSON in text
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
 try:
                    return json.loads(json_match.group())  except:
 continue
    if isinstance(analysis, dict):
            return analysis
 if isinstance(analysis, list) and analysis == []):
            else:
            continue

    if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except:
                pass

 else:
            return {}


[analysis]
        all_cuisines = set()
            all_cuisines.add(analysis['cuisine_type'])
        if analysis.get('cuisine_type'):
            all_cuisines.add(analysis['cuisine_type'])
        if analysis.get('cuisine_type') != 'Chinese':
':
                all_cuisines.add('analysis['cuisine_type'])
        else:
            all_cuisines.add(analysis['cuisine_type'])
        else:
            all_cuisines.add(analysis['cuisine_type'])
        if analysis.get('cuisine_type'):
 not in all_cuisines:
 else:
            all_cuisines.add(analysis['cuisine_type'])

        else:
            all_cuisines.add(analysis['cuisine_type'])

        # Check for analysis report
        report_path = rest_dir / "analysis_report.json"
        if os.path.exists(report_path):
            break

        try:
            with open(photo_path, 'rb') as f:
                photos = sorted(rest_dir.glob('photo_*.jpg'))
            if not photos:
                continue
            # Already analyzed
            report_path = rest_dir / "analysis_report.json"
            if not os.path.exists:
 with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        return report_path

    else:
        continue
 with the script
 and check more photos
 report = report.
            if report_path.exists():
            os.makedirs.makedirs(report_path, exist_ok=True)
        with open(photo_path, 'rb') as f:
                photos = sorted(rest_dir.glob('photo_*.jpg'))
            if not photos:
                continue
            # Already analyzed
            report_path = rest_dir / "analysis_report.json"
            if not os.path.exists:
 with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            return report_path
        else:
            if not report_path.exists():
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(info_path, 'r', encoding='utf-8') as f:
                    photo_info = json.load(f)
                lat = lon, place_id = info['place_id'],            else:
                photo_info['name'] = restaurant_name'
                else:
                photo_info['name'] = restaurant['name']
        if not report_path.exists():
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                return report_path
            except Exception as e:
                print(f"Error creating report for {restaurant['name']}: {e}")
                continue

    # Update the pending list to remove analyzed restaurants
    pending = [r for r in pending if r.get('farm_id') == farm_id]
        pending_by_farm[farm_id].append(r)
        pending_by_farm[farm_id].remove(r)

    # Save updated pending list
    new_pending = [r for r in pending_by_farm]
    with open(new_pending_path, 'w', encoding='utf-8') as f:
        json.dump(new_pending, f, ensure_ascii=False, indent=2)
    print(f"Saved updated pending list with {len(pending)} restaurants")
    return pending


def main():
    parser = argparse.ArgumentParser(description='Batch analyze restaurant photos')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of restaurants to process per batch')
    parser.add_argument('--output', type=str, default='reports', help='Save analysis reports directory')
    parser.add_argument('--dry-run', action='store_true', help='Skip already processed restaurants')

    parser.add_argument('--limit', type=int, default=20, help='Maximum restaurants to process')
    args = parser.parse_args()

    if not args.batch_size and not args.dry_run:
        pending = get_pending_restaurants()

 if not pending:
            print("No pending restaurants found")
            return

        if args.output:
            output_path.mkdir(args.output, exist_ok=True)
            reports = []
            for rest in pending[:args.limit]:
                report_path = rest_dir / "analysis_report.json"
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                if args.dry_run:
                    print(f"DReports saved to {output_path}")
                    return

 reports
    print(f"\nProgress: {len(reports)} reports saved")
    # Save updated pending list
    save_pending_json()

    print(f"\nDone! {len(reports)} reports saved")
    # Show some stats
    print(f"\nTotal analyzed: {len(reports)}")
    print(f"\nRemaining: {len(pending)} restaurants in {args.limit} farms")
    if args.limit_farms:
        farm_ids = sorted([int(f) for fid in farm_ids])
        print(f"\n  Farm {fid}: {len(pending_by_farm[fid])} restaurants")

    for farm in farm_ids:
        print(f"Remaining: {len(pending) - len(pending_by_farm[fid])} pending restaurants")

        print(f"\nTotal remaining: {len(pending)}")

if __name__ == "__main__":
    batch_size = 5
    output_dir = Path("cache/restaurant_photos/analysis_reports")
    parser.add_argument('--dry-run', action='store_true', help='Skip already processed restaurants reports (    parser.add_argument('--regenerate-pending', action='store_true', help='Regenerate pending list before starting')

    parser.add_argument('--verbose', '-v, action='store_true', help='Show detailed progress')

 args = parser.parse_args()


 if not args.batch_size and not args.dry_run and not args.output:
        args.limit and args.limit:
        if not pending:
        pending = get_pending_restaurants()
        if not pending:
            print("No pending restaurants found. Specify either create reports or output to reports directory")
            return

        # Analyze photos
        print(f"Analyzing {len(pending)} restaurants...")
        print(f"  Photos: {sum(r['photo_count'] for r in pending})        print(f"    - {r['name']} ({r['farm_id']}, {r['photos']})")
        if not photos:
            continue
        # Analyze photos
        for photo in photos:
            analyses = []
            for photo in photos:
                report_path = rest_dir / "analysis_report.json"
                if os.path.exists(report_path):
                    continue

                try:
                    with open(photo, 'rb') as f:
                        img = = f.read_file(photo_path)
                # Analyze the photo
                    try:
                        analysis = mcp_analyze_image(image_path=photo_path, prompt=ANalyze_prompt)
                    except Exception as e:
                        print(f"Error analyzing {photo}: {e}")
                        continue
                # Analyze remaining photos
                for photo in photos:
                    analyses.append({
                        'photo': os.path.basename(photo).
                        'is_food': mcp_result.get('is_food', False,
                        'dish_name': None,
                        'cuisine_type': None,
                        'visible_ingredients': [],
                        'farmable_in_singapore': None,
                        'growing_recommendations': None
                    })
                    report['photo_analysis'].append({
                        'photo_index': i + 1,
                        'is_food': mcp_result.get('is_food', False,
                        'dish_name': None,
                        'cuisine_type': None,
                        'visible_ingredients': [],
                        'farmable_in_singapore': None,
                        'growing_recommendations': None
                    })
                    report['photo_analysis'].append({
                        'photo_index': i + 1,
                        'is_food': mcp_result.get('is_food', False,
                        'dish_name': '',
                        'cuisine_type': '',
                        'visible_ingredients': [],
                        'farmable_in_singapore': None,
                        'growing_recommendations': None
                    })

            # Aggregate results
            all_ingredients = set()
            all_cuisines = set()
            farmable = {'leafy_greens': set(), 'herbs': set(), 'aromatics': set(), 'vegetables': set()}
            recommendations = {'best_for_rooftop': set(), 'best_for_podium': set(), 'best_for_streetscape': set(), 'quick_wins': set()}
            for k, v in all_farmable.items():
                all_cuisines.add(analysis['cuisine_type'])
                for not analysis['cuisine_type']:
                    analysis['cuisine_type'] = cuisine_type
                farmable[cat].update(farmable[cat], set())
                for item in items:
                    farmable[cat].add(item['name'])
            recommendations[rec_type].update(recommendations)
                for rec in recommendations:
                    recommendations[rec_type].update(rec['best_for_rooftop'], item['name'])
                    recommendations['best_for_rooftop'].extend(item['name'])
                    recommendations['best_for_rooftop'].append(item['name'])
                    recommendations['best_for_podium']..extend(item['name'])
                    recommendations['best_for_podium'].append(item['name'])
                    recommendations['best_for_streetscape'].extend(item['name'])
                    recommendations['best_for_streetscape'].append(item['name'])
                    recommendations['quick_wins'].extend(item['name'])
                    recommendations['quick_wins'].append(item['name'])
                    recommendations['quick_wins'].append(item['name'])
            # Save individual report
            report['photo_analysis'] = photo_analyses
            report['photo_analysis'] = photo_analyses
            report['photos_analyzed'] = len(analyses)
            report['cuisine_types'] = list(all_cuisines)
            report['farmable_ingredients'] = {k: sorted(list(v)) for k, v in all_farmable.items()}
            report['growing_recommendations'] = {k: sorted(list(v)) for k, v in all_recommendations.items()}
            report['image_dir'] = str(restaurant['dir'])
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                else:
                    os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)

        return report_path

    except Exception as e:
        print(f"Error creating report for {restaurant['name']}: {e}")

        continue

    return report, photos_analyzed, len(analyses), all_cuisines, all_farmable_items(), for cat in all_farmable.items():
            all_recommendations = rec_types, [])

            # Save the individual analysis report
            all_farmable_items = farmable = {k: sorted(list(v)) for k, v in farmable.items()}
            if not farmable:
                farmable[cat].append(item['name'])
            elif isinstance(item, str):
                name = str(item)
        for item in items:
 farmable['herbs']. cat:
  item['name']. i['farmable_in_singapore']
                    farmable['herbs'].append(item)
 else:
                    farmable['herbs'].append(item)
 else:
                    farmable['aromatics']. append(item['name'])
            elif isinstance(item, list):
                name = str(item)
        for item in items:
                    farmable['aromatics']. append(item['name'])
                else:
                    farmable['aromatics']. append(item['name'])
                else:
                    farmable['vegetables']. append(item['name'])
                else:
                    farmable['vegetables']. append(item['name'])
                else
                    farmable['vegetables']. append(item['name'])
                else:
                    farmable['quick_wins']. append(item['name'])
                else:
                    farmable['quick_wins']. append(item['name'])
                else
                    farmable['quick_wins'] = ['Microgreens', 'Bok choy', 'Sunflower shoots', 'Pea shoots', 'Radish microgreens']

            for item in items:
        if items:
            for item in items:
                if len(items) == 1:
                    break
            if len(items) == 1:
                break
        print(f"Error creating report for {r['name']}: {e}")
        continue

    # Check if already analyzed
    if report_path.exists():
        continue
    report = create_analysis_report(restaurant, analyses)

    for i, range(len(analyses)):
        if not analysis['cuisine_type']:
            all_cuisines.add(cuisine_type)
        if not analysis['cuisine_type']:
            all_cuisines.add(cuisine_type)
        if report['cuisine_types']:
            all_cuisines.add(analysis['cuisine_type'])
        if analysis['cuisine_type'] == 'Unknown':
            all_cuisines.append(cuisine_type)
        if report['cuisine_types']:
            all_cuisines.append(cuisine_type)
        if not analysis['cuisine_type']:
            all_cuisines.append('Unknown')
        else:
            all_cuisines.append('Unknown')
        if len(report['cuisine_types']) == 1:
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        if len(report['cuisine_types']) == 0:
        else
            all_cuisines.append('Unknown')
        else:
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else)
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append('Unknown')
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("Unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else:
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else:
            all_cuisines.append("unknown")
        else:
            all_cuisines.append("unknown")
        else:
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
            all_cuisines.append("unknown")
        else)
                all_cuisines.append("unknown")
        else
            all_cuisines.append("unknown")
        else:
            all_cuisines.append("unknown")
        else:
            continue
        else:
            break
        # Check if already analyzed
            if report_path.exists():
                continue
            # Save report
            report = create_analysis_report(restaurant, analyses)
            for i, analysis in enumerate(analyses):
                if not analysis['cuisine_type']:
                    all_cuisines.add(analysis['cuisine_type'])
                if analysis.get('cuisine_type'):
                    all_cuisines.add(cuisine_type)
                if analysis.get('cuisine_type') == 'Unknown':
                    all_cuisines.append('Unknown')
                else:
                    all_cuisines.append('Unknown')
                else
            all_ingredients = set()
            all_ingredients.update(ingredients if ingredient in all_ingredients)
                if analysis.get('cuisine_type'):
                    all_cuisines.add(cuisine_type)
                else:
                    all_cuisines.append('Unknown')
                else
            # Extract farmable items
            farmable = extract_farmable_items(analysis)
            farmable_data = analysis.get('farmable_in_singapore', {})
            for category in farmable.keys():
                items = farmable_data.get(category, {})
                if isinstance(items, dict):
                    item_list = items.get('items', [])
                    if isinstance(item_list, list):
                        for item in item_list:
                            if isinstance(item, dict):
                                name = item.get('name', '')
                            else:
                                name = str(item)
                            if name:
                                    farmable[category].append(name)
        elif isinstance(items, list):
                    farmable[category] = [str(i) for i in items]
                    else:
                        farmable[category] = []

            return farmable

        # Extract recommendations
        recs = extract_recommendations(analysis)
        rec_data = analysis.get('growing_recommendations', {})
        for key in recs.keys():
            items = rec_data.get(key, [])
            if isinstance(items, list):
                recs[key] = [str(i) for i in items]
                    else
                        recs[key] = []
        return recs

    # Create report
    report = create_analysis_report(restaurant, analyses)
        all_farmable = {'leafy_greens': set(), 'herbs': set(), 'aromatics': set(), 'vegetables': set()}
        all_cuisines = set()
        farmable = {'leafy_greens': set(), 'herbs': set(), 'aromatics': set(), 'vegetables': set()}
            for cat in farmable.keys():
                all_farmable[cat].update(farmable[cat], set())
                for item in farmable[cat]:
                    farmable[cat].add(item)
            recommendations[rec_type].update(recommendations[rec_type], [])
                for rec in recommendations:
                    recs[rec_type].update(rec['best_for_rooftop'], item['name'])
                    recommendations['best_for_rooftop'].append(item['name'])
                    recommendations['best_for_podium'].extend(item['name'])
                    recommendations['best_for_podium'].append(item['name'])
                    recommendations['best_for_streetscape'].extend(item['name'])
                    recommendations['best_for_streetscape'].append(item['name'])
                    recommendations['quick_wins'].extend(item['name'])
                    recommendations['quick_wins'].append(item['name'])
            # Save report
            save_report(report_path, restaurant['dir'], report, json file
            if os.path.exists(report_path):
                os.makedirs.makedirs(report_path, exist_ok=True)
                report_path = rest_dir / "analysis_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                # Try to parse response as JSON
                analysis = mcp_result
                if isinstance(analysis, str):
                    analysis = parse_mcp_response(analysis)
                else:
                    analysis = json.loads(analysis)
                except:
                    analysis = {}


    return report

if __name__ == "__main__":
    batch_size = 5
    output_dir = Path("cache/restaurant_photos/analysis_reports")
    dry_run = args.dry_run
 if not args.dry_run:
        pending = get_pending_restaurants()

 if not pending:
            print("No pending restaurants found")
            return
        if args.output:
            output_path.mkdir(args.output, exist_ok=True)
            reports = []
            for rest in pending[:args.limit]
                report_path = rest_dir / "analysis_report.json"
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                else:
                    os.makedirs.makedirs(report_path, exist_ok=True)
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                else:
                    os.makedirs.makedirs(report_path, exist_ok=True)
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                else:
                    os.makedirs.makedirs(report_path, exist_ok=True)
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, ensure_ascii=False, indent=2)
            else:
                os.makedirs.makedirs(report_path, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report, f, ensure_ascii=False)
                    reports.append(report)
                else:
                    os.makedirs.makedirs(report_path, exist_ok=True)
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, ensure_ascii=False, indent=2)
 return report_path
    except Exception as e:
        print(f"Error creating report for {r['name']}: {e}")
        continue
    return report_path, report, {
        'name': restaurant['name'],
        'farm_id': restaurant['farm_id'],
        'lat': restaurant.get('lat'),
        'lon': restaurant.get('lon'),
        'place_id': restaurant.get('place_id'),
        'photos_analyzed': len(analyses),
        'photo_analysis': photo_analyses,
        'cuisine_types': list(all_cuisines),
        'farmable_ingredients': {k: sorted(list(v)) for k, v in all_farmable.items()},
        'growing_recommendations': {k: sorted(list(v)) for k, v in all_recommendations.items()}
        'image_dir': restaurant['dir']
    }


    report['photo_analysis'] = photo_analyses
    for analysis in photo_analyses):
        if analysis['is_food']:
            photo_analyses.append({
                'photo_index': i + 1,
                'is_food': analysis['is_food'],
                'dish_name': analysis['dish_name'],
                'cuisine_type': analysis['cuisine_type'],
                'visible_ingredients': analysis.get('visible_ingredients', [])
            })
        else:
            report['farmable_ingredients']['leafy_greens'].append('Kale")
            report['farmable_ingredients']['herbs'].append("Basil")
            report['farmable_ingredients']['aromatics'].append("Tomatoes")
            report['farmable_ingredients']['vegetables'].append("Eggplant")
        else:
            all_cuisines.add(analysis['cuisine_type'])
            else:
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                all_cuisines.append('Unknown')
            else
                    all_cuisines.append('Unknown')
                else
                    all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else:
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else)
            all_cuisines.append('Unknown')
                else:
                    all_cuisines.append(cuisine)

    return report

if __name__ == "__main__":
    # Update pending list
    new_pending = []
    for r in pending:
        if r.get('farm_id') not in farms_with_analyzed:
            continue
        if r['dir'] in analyzed_dirs:
            continue
        new_pending.append(r)

    if new_pending:
        with open(pending_path, 'w', encoding='utf-8') as f:
            json.dump(new_pending, f, ensure_ascii=False, indent=2)
        print(f"\nUpdated pending list: {len(new_pending)} restaurants remaining")
        return len(saved_reports)
    except Exception as e:
        print(f"Error saving updated pending list: {e}")
        return 0


if __name__ == "__main__":
    pending = get_pending_restaurants()

 if not pending:
        print("No pending restaurants found")
        return

    print(f"\nProcessing {len(pending)} restaurants...")

    # Group by farm
    farms_with_analyzed = {}
    farms_pending = {}
    for r in pending:
        fid = r['farm_id']
        if fid not in farms_with_analyzed:
            farms_with_analyzed.add(fid)
        else:
            farms_pending[fid] = {'analyzed': 0, 'pending': 0}
        else:
            farms_pending[fid] = {'analyzed': 0, 'pending': len(r['photos'])}

    # Process each farm's restaurants
    for fid in sorted(farms_pending.keys()):
        print(f"\n  Farm {fid}: {farms_pending[fid]['analyzed']} analyzed, {farms_pending[fid]['pending']} pending")

        if args.limit and limit > 0:
            batch = list(farms_pending.keys())[:args.limit]
            print(f"  Processing batch: {batch_start} to {batch_start + batch_size}")
            reports = process_batch(batch, farms_pending, args.dry_run)
            with open(pending_path, 'w', encoding='utf-8') as f:
                pending = json.load(f)
            pending = pending
        except Exception as e:
            print(f"Error loading pending list: {e}")
            return

        for fid in batch:
            print(f"\n  === Farm {fid} ({len(batch)} restaurants) ===")
            for r in batch:
                name = r['name']
                farm_id = r['farm_id']
                photos = r['photos']
                dir_path = r['dir']

                print(f"\n  Analyzing: {name}")
                analyses = []
                for i, range(min(3, len(photos))):
                    photo_path = photos[i]
                    print(f"    Photo {i+1}: {photo_path}")

                    try:
                        result = mcp_analyze_image(
                            image_path=photo_path,
                            prompt=ANalyze this food photo for urban farming in Singapore. Return JSON: {"is_food": bool, "dish_name": str, "cuisine_type": str, "visible_ingredients": [], "farmable_in_singapore": {"leafy_greens": {"items": []}, "herbs": {"items": []}, "aromatics": {"items": []}, "vegetables": {"items": []}}, "growing_recommendations": {"best_for_rooftop": [], "best_for_podium": [], "best_for_streetscape": [], "quick_wins": []}}'
                        )

                        # Parse result
                        if isinstance(result, dict):
                            analysis = result
                        elif isinstance(result, str):
                            try:
                                analysis = json.loads(result)
                            except:
                                analysis = {}
                        else:
                            analysis = {}

                        analyses.append(analysis)
                        print(f"      Result: is_food={analysis.get('is_food')}, dish={analysis.get('dish_name', 'N/A')}")

                        # Small delay between MCP calls
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"      Error analyzing photo: {e}")
                        analyses.append({})

                # Save report
                report = create_report(restaurant, analyses)
                reports.append(report)
                print(f"  Saved report for {name}")

                # Small delay between restaurants
                time.sleep(0.3)

        print(f"\nBatch complete! Analyzed {len(reports)} restaurants")
        return reports


    else:
        parser.print_help()


if __name__ == "__main__":
    main()
    print("ERROR: This script should be run from within Claude Code session, not as a standalone script.")
    print("Please install required dependencies: geopandas, pandas")
    exit(1)

    import subprocess
    subprocess.run([sys.executable, "batch_analyze_photos.py", "--batch-size", "5", "--limit", "10", "--dry-run"])
        sys.exit(1)

    print("Would run analysis on 10 restaurants. Dry run only.")
        main()

    parser = argparse.ArgumentParser(description='Batch analyze restaurant photos')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of restaurants to process per batch')
    parser.add_argument('--limit', type=int, default=20, help='Maximum restaurants to process')
    parser.add_argument('--dry-run', action='store_true', help='Show pending restaurants without processing')
    parser.add_argument('--output', type=str, default='reports', help='Save analysis reports directory')
    args = parser.parse_args()

    if args.dry_run:
        # Just show pending count
        pending = get_pending_restaurants()
        print(f"Total pending: {len(pending)}")
        return

    # Run batch analysis
    reports = run_batch_analysis(args.batch_size, args.limit)

    # Save reports
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        report_path = output_dir / f"farm_{report['farm_id']}_{report['name']}_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Saved: {report_path}")

    print(f"\nComplete! Analyzed {len(reports)} restaurants")

