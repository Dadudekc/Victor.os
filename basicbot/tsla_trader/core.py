# core.py
import csv, yaml, datetime
from pathlib import Path
from collections import defaultdict
import traceback # For debugging

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.yaml"
JOURNAL = BASE / "journal.csv"

def load_config():
    # print(f"[DEBUG] Loading config from: {CONFIG}")
    with open(CONFIG) as f:
        return yaml.safe_load(f)

def ensure_journal():
    if not JOURNAL.exists():
        print(f"[DEBUG] ensure_journal: {JOURNAL} does not exist. Creating and writing header.")
        JOURNAL.write_text("date,ticker,direction,strike,expiry,contracts,entry_price,exit_price,p_l,setup,notes\\n")
    else:
        # print(f"[DEBUG] ensure_journal: {JOURNAL} already exists.")
        pass

def add_trade(entry: dict):
    print(f"[DEBUG] add_trade called with entry: {entry}")
    try:
        processed_entry = {k: str(v) for k, v in entry.items()}

        if "date" not in processed_entry or not processed_entry["date"]:
            processed_entry["date"] = datetime.date.today().isoformat()
            print(f"[DEBUG] add_trade: Date was missing or empty, set to today: {processed_entry['date']}")
        else:
            processed_entry["date"] = str(processed_entry["date"])
            print(f"[DEBUG] add_trade: Date provided in entry: {processed_entry['date']}")
        
        ensure_journal()
        
        print(f"[DEBUG] add_trade: Processed entry for CSV: {processed_entry}")

        with open(JOURNAL, "a", newline="") as f:
            fieldnames = ["date","ticker","direction","strike","expiry","contracts","entry_price","exit_price","p_l","setup","notes"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            f.seek(0, 2)
            if f.tell() == 0:
                 print(f"[DEBUG] add_trade: {JOURNAL} is empty. Writing header.")
                 writer.writeheader()
            
            row_to_write = {fn: processed_entry.get(fn, "") for fn in fieldnames}

            print(f"[DEBUG] add_trade: Writing row: {row_to_write}")
            writer.writerow(row_to_write)
            print(f"[DEBUG] add_trade: Row written to {JOURNAL}.")
            
    except Exception as e:
        print(f"[ERROR] Error during add_trade: {e}")
        traceback.print_exc()

def import_from_yaml(yaml_path: Path):
    print(f"[DEBUG] import_from_yaml: Attempting to import from: {yaml_path}")
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        trades_to_add = data.get("trades", [])
        if not trades_to_add:
            print(f"[DEBUG] import_from_yaml: No trades found in {yaml_path.name} to import.")
            return
            
        print(f"[DEBUG] import_from_yaml: Found {len(trades_to_add)} trades to add from {yaml_path.name}.")
        for i, trade_entry in enumerate(trades_to_add):
            print(f"[DEBUG] import_from_yaml: Processing trade {i+1}/{len(trades_to_add)}: {trade_entry}")
            add_trade(trade_entry)
            print(f"[DEBUG] import_from_yaml: Trade {i+1}/{len(trades_to_add)} processing finished by add_trade.")
        print(f"✅ Imported {len(trades_to_add)} trades from {yaml_path.name}")
    except Exception as e:
        print(f"[ERROR] Error during import_from_yaml: {e}")
        traceback.print_exc()

def summarize_trades():
    print(f"[DEBUG] summarize_trades: Starting summary.")
    cfg = load_config()
    ensure_journal() # Ensures journal.csv exists

    trades = []
    print(f"[DEBUG] summarize_trades: Reading trades from {JOURNAL}")
    try:
        with open(JOURNAL, "r", newline='') as f_read_content: # Use newline='' for reading CSVs
            journal_content = f_read_content.read()
            print(f"[DEBUG] summarize_trades: Current raw journal content:\n--START JOURNAL CONTENT--\n{journal_content}--END JOURNAL CONTENT--")
    except Exception as e_read:
        print(f"[ERROR] summarize_trades: Could not read journal for debug: {e_read}")

    # Re-open for DictReader, as the previous read consumed the file pointer if not careful
    # It's safer to read content then parse, or open fresh for DictReader
    with open(JOURNAL, "r", newline='') as f_csv: # Use newline='' for reading CSVs
        reader = csv.DictReader(f_csv)
        try:
            trades = list(reader)
            print(f"[DEBUG] summarize_trades: Trades read by DictReader (first 3 if many): {trades[:3]}")
            if not trades:
                print(f"[DEBUG] summarize_trades: No trades were parsed by DictReader. Check header and CSV format.")
        except Exception as e_csv_read:
            print(f"[ERROR] summarize_trades: Error reading CSV with DictReader: {e_csv_read}")
            traceback.print_exc()
            trades = []

    today = datetime.date.today().isoformat()
    print(f"[DEBUG] summarize_trades: Today's date for filtering: {today}")

    today_trades = [t for t in trades if t.get("date") == today]
    print(f"[DEBUG] summarize_trades: Found {len(today_trades)} trades for date {today}.")
    if len(today_trades) > 0:
        print(f"[DEBUG] summarize_trades: First trade for today: {today_trades[0]}")
    
    risk_per_trade = cfg.get('risk_per_trade', 0)
    base_gain_pct = cfg.get('base_gain_pct', 0)
    dream_gain_pct = cfg.get('dream_gain_pct', 0)
    daily_target = cfg.get('daily_target', 0)

    base_thr = risk_per_trade * base_gain_pct / 100
    dream_thr = risk_per_trade * dream_gain_pct / 100
    
    pl_today = 0
    for t in today_trades:
        p_l_val = t.get('p_l')
        if p_l_val: 
            try:
                pl_today += float(p_l_val)
            except ValueError:
                print(f"[WARNING] summarize_trades: Could not convert P/L '{p_l_val}' to float for trade: {t}")
    print(f"[DEBUG] summarize_trades: Calculated P/L for today: {pl_today}")

    summary_output = []
    summary_output.append(f"\\n🧠 {today} Summary:")
    summary_output.append(f"Trades: {len(today_trades)}")
    summary_output.append(f"P/L: ${pl_today:.2f} / Goal: ${daily_target}")

    base_hits_count = 0
    dream_runs_count = 0
    for t in today_trades:
        p_l_val = t.get('p_l')
        if p_l_val:
            try:
                p_l_float = float(p_l_val)
                if p_l_float >= base_thr:
                    base_hits_count += 1
                if p_l_float >= dream_thr:
                    dream_runs_count +=1
            except ValueError:
                pass 

    summary_output.append(f"Base hits: {base_hits_count}")
    summary_output.append(f"Dream runs: {dream_runs_count}")

    weekly = defaultdict(float)
    print(f"[DEBUG] summarize_trades: Calculating weekly P/L from {len(trades)} total trades in journal.")
    for t_idx, t in enumerate(trades):
        trade_date_str = t.get('date')
        trade_pl_str = t.get('p_l')
        if not trade_date_str or not trade_pl_str: 
            # print(f"[DEBUG] summarize_trades: Skipping weekly calc for trade #{t_idx} due to missing date/pl: {t}")
            continue
        try:
            date_obj = datetime.date.fromisoformat(trade_date_str)
            year, week_num, _ = date_obj.isocalendar()
            wk_tuple = (year, week_num)
            weekly[wk_tuple] += float(trade_pl_str or 0)
        except ValueError:
            # print(f"[WARNING] summarize_trades: Skipping weekly calculation for trade #{t_idx} due to malformed date or P/L: {t}")
            continue
    print(f"[DEBUG] summarize_trades: Weekly P/L data: {dict(weekly)}")

    summary_output.append("\\n📅 Weekly P/L:")
    for wk, val in sorted(weekly.items()):
        y, w = wk
        summary_output.append(f"  Week {y}-W{w:02d}: ${val:.2f}")
    
    print("\n".join(summary_output))
    print(f"[DEBUG] summarize_trades: Summary display finished.") 