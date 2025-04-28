import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ASSET_USAGE_FILE = Path('assets-usage.json')
OUTPUT_FILE = Path('unreferenced-assets.json')

def main():
    logging.info(f"Reading asset usage data from {ASSET_USAGE_FILE}...")
    try:
        with open(ASSET_USAGE_FILE, 'r', encoding='utf-8') as f:
            usage_data = json.load(f)
            if not isinstance(usage_data, dict) or 'asset_usage' not in usage_data:
                 logging.error(f"Invalid format in {ASSET_USAGE_FILE}. Missing 'asset_usage' key.")
                 return
            asset_usage_map = usage_data['asset_usage']
            if not isinstance(asset_usage_map, dict):
                 logging.error(f"Invalid format in {ASSET_USAGE_FILE}. 'asset_usage' is not a dictionary.")
                 return

    except FileNotFoundError:
        logging.error(f"Asset usage file not found: {ASSET_USAGE_FILE}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {ASSET_USAGE_FILE}: {e}")
        return
    except Exception as e:
        logging.error(f"Error reading asset usage file {ASSET_USAGE_FILE}: {e}")
        return

    logging.info(f"Identifying assets with zero usage count...")
    unused_assets = []
    for asset_path, count in asset_usage_map.items():
        if count == 0:
            unused_assets.append(asset_path)

    logging.info(f"Found {len(unused_assets)} potentially unused assets.")

    # Prepare output data (implicitly covers Task 10)
    output_data = {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "asset_usage_source": str(ASSET_USAGE_FILE),
        "unreferenced_assets_count": len(unused_assets),
        "unreferenced_assets": sorted(unused_assets)
    }

    logging.info(f"Writing unreferenced assets list to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        logging.info("Unreferenced asset analysis complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")

if __name__ == "__main__":
    from datetime import datetime, timezone # Import locally
    main() 