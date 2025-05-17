# core.py
import csv, yaml, datetime
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.yaml"
JOURNAL = BASE / "journal.csv"

def load_config():
    with open(CONFIG) as f:
        return yaml.safe_load(f)

def ensure_journal():
    if not JOURNAL.exists():
        JOURNAL.write_text("date,ticker,direction,strike,expiry,contracts,entry_price,exit_price,p_l,setup,notes\n")

def add_trade(entry: dict):
    entry = {k: str(v) for k, v in entry.items()}  # ensure all strings
    entry.setdefault("date", datetime.date.today().isoformat())
    ensure_journal()
    with open(JOURNAL, "a", newline="") as f:
        # The fieldnames should be fixed to match the CSV header ensure_journal writes
        fieldnames = ["date","ticker","direction","strike","expiry","contracts","entry_price","exit_price","p_l","setup","notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        f.seek(0, 2) # go to end of file
        if f.tell() == 0: # check if file is empty
            writer.writeheader() # write header if file is empty
        # Filter entry to only include keys that are in fieldnames to avoid errors
        filtered_entry = {k: entry[k] for k in fieldnames if k in entry}
        writer.writerow(filtered_entry)

def summarize_trades():
    cfg = load_config()
    ensure_journal()

    trades = []
    with open(JOURNAL, newline="") as f:
        reader = csv.DictReader(f)
        trades = list(reader)

    today = datetime.date.today().isoformat()
    today_trades = [t for t in trades if t.get("date") == today] # use .get for safety
    
    # Ensure config values are present before using them
    risk_per_trade = cfg.get('risk_per_trade', 0)
    base_gain_pct = cfg.get('base_gain_pct', 0)
    dream_gain_pct = cfg.get('dream_gain_pct', 0)
    daily_target = cfg.get('daily_target', 0)

    base_thr = risk_per_trade * base_gain_pct / 100
    dream_thr = risk_per_trade * dream_gain_pct / 100
    
    pl_today = sum(float(t['p_l']) for t in today_trades if t.get('p_l'))

    summary_output = []
    summary_output.append(f"\n🧠 {today} Summary:")
    summary_output.append(f"Trades: {len(today_trades)}")
    summary_output.append(f"P/L: ${pl_today:.2f} / Goal: ${daily_target}")
    summary_output.append(f"Base hits: {sum(float(t['p_l']) >= base_thr for t in today_trades if t.get('p_l'))}")
    summary_output.append(f"Dream runs: {sum(float(t['p_l']) >= dream_thr for t in today_trades if t.get('p_l'))}")

    weekly = defaultdict(float)
    for t in trades:
        if not t.get('date') or not t.get('p_l'): 
            continue
        try:
            date_obj = datetime.date.fromisoformat(t["date"])
            year, week_num, _ = date_obj.isocalendar()
            wk_tuple = (year, week_num)
            weekly[wk_tuple] += float(t["p_l"] or 0)
        except ValueError:
            print(f"Skipping trade due to malformed date or P/L: {t}")
            continue

    summary_output.append("\n📅 Weekly P/L:")
    for wk, val in sorted(weekly.items()):
        y, w = wk
        summary_output.append(f"  Week {y}-W{w:02d}: ${val:.2f}")
    print("\n".join(summary_output))

def import_from_yaml(yaml_path: Path):
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    trades_to_add = data.get("trades", [])
    if not trades_to_add:
        print(f"No trades found in {yaml_path.name} to import.")
        return
    for trade_entry in trades_to_add:
        add_trade(trade_entry)
    print(f"✅ Imported {len(trades_to_add)} trades from {yaml_path.name}") 