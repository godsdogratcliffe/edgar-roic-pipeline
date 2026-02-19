"""
ROIC Calculation Engine
═══════════════════════════════════════════════════════
Replaces the Excel formula logic. Reads EDGAR CSV output,
applies Tier 1-2 adjustments, and generates two JSON files:

  public_data.json   — Index-level charts + current company scores
  internal_data.json — Full 26-company detail, all quarters

Run by GitHub Actions after EDGAR data pull.
"""

import csv
import json
import os
import math
from collections import defaultdict
from datetime import datetime

# ── Configuration ──
INPUT_DIR = os.environ.get("INPUT_DIR", "output")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "docs")  # GitHub Pages serves from /docs

COMPANIES = {
    # Tier 1: AI Layoff
    "MSFT": {"name": "Microsoft", "sector": "Technology", "tier": 1},
    "AMZN": {"name": "Amazon", "sector": "Tech/Retail", "tier": 1},
    "GOOGL": {"name": "Alphabet", "sector": "Technology", "tier": 1},
    "META": {"name": "Meta Platforms", "sector": "Technology", "tier": 1},
    "IBM": {"name": "IBM", "sector": "Technology", "tier": 1},
    "CRM": {"name": "Salesforce", "sector": "Technology", "tier": 1},
    "WDAY": {"name": "Workday", "sector": "Technology", "tier": 1},
    "SAP": {"name": "SAP SE", "sector": "Technology", "tier": 1},
    "CRWD": {"name": "CrowdStrike", "sector": "Cybersecurity", "tier": 1},
    "HPQ": {"name": "HP Inc", "sector": "Technology", "tier": 1},
    "CHGG": {"name": "Chegg", "sector": "EdTech", "tier": 1},
    "DBX": {"name": "Dropbox", "sector": "Technology", "tier": 1},
    "CHRW": {"name": "C.H. Robinson", "sector": "Logistics", "tier": 1},
    "PYPL": {"name": "PayPal", "sector": "Fintech", "tier": 1},
    "DUOL": {"name": "Duolingo", "sector": "EdTech", "tier": 1},
    "FVRR": {"name": "Fiverr", "sector": "Marketplace", "tier": 1},
    # Tier 2: Control
    "JPM": {"name": "JPMorgan Chase", "sector": "Financials", "tier": 2},
    "UNH": {"name": "UnitedHealth", "sector": "Healthcare", "tier": 2},
    "WMT": {"name": "Walmart", "sector": "Retail", "tier": 2},
    "CAT": {"name": "Caterpillar", "sector": "Industrials", "tier": 2},
    "AAPL": {"name": "Apple", "sector": "Technology", "tier": 2},
    "NVDA": {"name": "NVIDIA", "sector": "Technology", "tier": 2},
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare", "tier": 2},
    "COST": {"name": "Costco", "sector": "Retail", "tier": 2},
    "XOM": {"name": "ExxonMobil", "sector": "Energy", "tier": 2},
    "UPS": {"name": "UPS", "sector": "Logistics", "tier": 2},
}

AI_EVENTS = [
    {"ticker": "IBM",   "quarter": "Q2 2023", "jobs": 7800,  "type": "direct"},
    {"ticker": "CHGG",  "quarter": "Q2 2023", "jobs": 80,    "type": "disrupted"},
    {"ticker": "DBX",   "quarter": "Q2 2023", "jobs": 500,   "type": "direct"},
    {"ticker": "META",  "quarter": "Q1 2023", "jobs": 10000, "type": "partial"},
    {"ticker": "GOOGL", "quarter": "Q1 2023", "jobs": 12000, "type": "partial"},
    {"ticker": "DUOL",  "quarter": "Q1 2024", "jobs": 100,   "type": "direct"},
    {"ticker": "CHGG",  "quarter": "Q2 2024", "jobs": 248,   "type": "disrupted"},
    {"ticker": "GOOGL", "quarter": "Q2 2024", "jobs": 6000,  "type": "partial"},
    {"ticker": "CRM",   "quarter": "Q1 2024", "jobs": 700,   "type": "partial"},
    {"ticker": "PYPL",  "quarter": "Q1 2024", "jobs": 2500,  "type": "partial"},
    {"ticker": "DBX",   "quarter": "Q4 2024", "jobs": 528,   "type": "direct"},
    {"ticker": "SAP",   "quarter": "Q1 2024", "jobs": 8000,  "type": "direct"},
    {"ticker": "WDAY",  "quarter": "Q1 2025", "jobs": 1750,  "type": "direct"},
    {"ticker": "MSFT",  "quarter": "Q1 2025", "jobs": 6000,  "type": "direct"},
    {"ticker": "CRWD",  "quarter": "Q2 2025", "jobs": 500,   "type": "direct"},
    {"ticker": "MSFT",  "quarter": "Q3 2025", "jobs": 9000,  "type": "direct"},
    {"ticker": "CHGG",  "quarter": "Q4 2025", "jobs": 388,   "type": "disrupted"},
    {"ticker": "FVRR",  "quarter": "Q3 2025", "jobs": 250,   "type": "direct"},
    {"ticker": "IBM",   "quarter": "Q4 2025", "jobs": 2700,  "type": "direct"},
    {"ticker": "CRM",   "quarter": "Q3 2025", "jobs": 4000,  "type": "direct"},
    {"ticker": "HPQ",   "quarter": "Q4 2025", "jobs": 6000,  "type": "direct"},
    {"ticker": "CHRW",  "quarter": "Q4 2025", "jobs": 1400,  "type": "direct"},
    {"ticker": "AMZN",  "quarter": "Q4 2025", "jobs": 14000, "type": "direct"},
    {"ticker": "SAP",   "quarter": "Q2 2025", "jobs": 3000,  "type": "direct"},
    {"ticker": "UPS",   "quarter": "Q3 2025", "jobs": 14000, "type": "partial"},
]

# ── CSV Ingestion ──

def load_combined_csv(filepath):
    """Load the all_companies_quarterly.csv from EDGAR agent."""
    data = defaultdict(lambda: defaultdict(dict))  # ticker -> item -> quarter -> value
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row['Ticker']
            item = row['Line Item']
            for key, val in row.items():
                if key.startswith('Q') and val != '':
                    try:
                        data[ticker][item][key] = float(val)
                    except ValueError:
                        pass
    return data


# ── Adjustment Logic ──

def safe_div(a, b, default=None):
    if b is None or b == 0 or a is None:
        return default
    return a / b


def calculate_adjustments(data, quarters):
    """Apply Tier 1-2 ROIC adjustments. Same logic as Excel formulas."""
    results = {}
    
    for ticker, items in data.items():
        if ticker not in COMPANIES:
            continue
        
        co_result = {
            "info": COMPANIES[ticker],
            "quarters": {},
        }
        
        for qi, q in enumerate(quarters):
            rev = items.get("Revenue ($mm)", {}).get(q)
            opinc = items.get("Operating Income ($mm)", {}).get(q)
            tax_rate = items.get("Effective Tax Rate", {}).get(q)
            sbc = items.get("Stock-Based Comp ($mm)", {}).get(q, 0)
            
            # Restructuring: 4-quarter rolling average
            restruct_vals = []
            for back in range(min(4, qi + 1)):
                bq = quarters[qi - back]
                rv = items.get("Restructuring Charges ($mm)", {}).get(bq, 0)
                restruct_vals.append(rv or 0)
            restruct_avg = sum(restruct_vals) / len(restruct_vals) if restruct_vals else 0
            
            debt = items.get("Total Debt ($mm)", {}).get(q)
            equity = items.get("Total Shareholders' Equity ($mm)", {}).get(q)
            cash = items.get("Cash & Equivalents ($mm)", {}).get(q)
            goodwill = items.get("Goodwill ($mm)", {}).get(q, 0)
            intang = items.get("Acquired Intangibles ($mm)", {}).get(q, 0)
            leases = items.get("Op Lease Liabilities ($mm)", {}).get(q, 0)
            buybacks = items.get("Share Buybacks ($mm)", {}).get(q, 0)
            headcount = items.get("Headcount", {}).get(q)
            capex = items.get("Capital Expenditures ($mm)", {}).get(q)
            fcf = items.get("Free Cash Flow ($mm)", {}).get(q)
            mktcap = items.get("Market Cap ($mm)", {}).get(q)
            
            # Skip if core data missing
            if opinc is None or tax_rate is None or debt is None or equity is None:
                continue
            
            # Reported metrics
            nopat = opinc * (1 - tax_rate)
            invested_capital = (debt or 0) + (equity or 0) - (cash or 0)
            reported_roic = safe_div(nopat, invested_capital, 0) * 4  # Annualized
            
            # Tier 1: Denominator adjustments
            adj_ic = invested_capital - (goodwill or 0) - (intang or 0) + (leases or 0)
            
            # Tier 2: Numerator adjustments
            adj_nopat = (opinc - restruct_avg) * (1 - tax_rate)
            
            # Adjusted ROIC
            adj_roic = safe_div(adj_nopat, adj_ic, 0) * 4  # Annualized
            
            # Companion metrics
            rev_per_emp = safe_div(rev, headcount, 0) * 4 * 1000 if headcount else None  # $K ann.
            capex_intensity = safe_div(capex, rev, 0) if rev else None
            fcf_conversion = safe_div(fcf, adj_nopat, 0) if adj_nopat and adj_nopat != 0 else None
            buyback_flag = (buybacks or 0) > (adj_nopat * 0.3) if adj_nopat else False
            
            co_result["quarters"][q] = {
                "revenue": rev,
                "operating_income": opinc,
                "nopat": round(nopat, 1),
                "invested_capital": round(invested_capital, 1),
                "reported_roic": round(reported_roic, 4),
                "goodwill": goodwill,
                "intangibles": intang,
                "leases": leases,
                "adj_invested_capital": round(adj_ic, 1),
                "restruct_avg": round(restruct_avg, 1),
                "adj_nopat": round(adj_nopat, 1),
                "adj_roic": round(adj_roic, 4),
                "spread": round(adj_roic - reported_roic, 4),
                "rev_per_employee": round(rev_per_emp, 1) if rev_per_emp else None,
                "capex_intensity": round(capex_intensity, 4) if capex_intensity else None,
                "fcf_conversion": round(fcf_conversion, 4) if fcf_conversion else None,
                "buyback_flag": buyback_flag,
                "market_cap": mktcap,
                "headcount": headcount,
            }
        
        results[ticker] = co_result
    
    return results


def calculate_indices(results, quarters):
    """Calculate market-cap-weighted indices for Tier 1, Tier 2, All."""
    indices = {"all": {}, "tier1": {}, "tier2": {}, "gap": {}}
    
    for q in quarters:
        # Gather weights and ROICs
        all_data = []
        for ticker, co in results.items():
            qd = co["quarters"].get(q)
            if qd and qd.get("market_cap") and qd.get("adj_roic") is not None:
                all_data.append({
                    "ticker": ticker,
                    "tier": co["info"]["tier"],
                    "mktcap": qd["market_cap"],
                    "adj_roic": qd["adj_roic"],
                })
        
        if not all_data:
            continue
        
        for tier_filter, key in [(None, "all"), (1, "tier1"), (2, "tier2")]:
            subset = [d for d in all_data if (tier_filter is None or d["tier"] == tier_filter)]
            total_mc = sum(d["mktcap"] for d in subset)
            if total_mc > 0:
                weighted_roic = sum(d["mktcap"] * d["adj_roic"] for d in subset) / total_mc
                indices[key][q] = round(weighted_roic, 4)
        
        if q in indices["tier1"] and q in indices["tier2"]:
            indices["gap"][q] = round(indices["tier1"][q] - indices["tier2"][q], 4)
    
    return indices


# ── Output Generation ──

def generate_public_json(results, indices, quarters, events):
    """Public view: index charts + current company scores only."""
    # Current quarter = last available
    current_q = None
    for q in reversed(quarters):
        if q in indices["all"]:
            current_q = q
            break
    
    # Company scoreboard (current quarter only)
    scoreboard = []
    for ticker, co in results.items():
        qd = co["quarters"].get(current_q, {})
        if qd:
            scoreboard.append({
                "ticker": ticker,
                "name": co["info"]["name"],
                "sector": co["info"]["sector"],
                "tier": co["info"]["tier"],
                "adj_roic": qd.get("adj_roic"),
                "reported_roic": qd.get("reported_roic"),
                "spread": qd.get("spread"),
                "rev_per_employee": qd.get("rev_per_employee"),
            })
    
    scoreboard.sort(key=lambda x: x.get("adj_roic") or -999, reverse=True)
    
    return {
        "generated": datetime.utcnow().isoformat(),
        "current_quarter": current_q,
        "quarters": quarters,
        "indices": indices,
        "scoreboard": scoreboard,
        "events": events,
        "methodology_summary": {
            "adjustments": [
                "Strip goodwill and acquired intangibles from invested capital",
                "Add operating lease liabilities to invested capital (ASC 842)",
                "Amortize restructuring charges over 4-quarter rolling window",
                "Retain stock-based compensation as real cost",
            ],
            "tier1_description": "16 publicly traded companies that explicitly attributed layoffs to AI",
            "tier2_description": "10 control group companies not primarily citing AI for layoffs",
            "annualization": "Quarterly ROIC × 4",
        },
    }


def generate_internal_json(results, indices, quarters, events):
    """Internal view: full detail for all companies, all quarters."""
    return {
        "generated": datetime.utcnow().isoformat(),
        "quarters": quarters,
        "indices": indices,
        "companies": results,
        "events": events,
        "company_list": {t: COMPANIES[t] for t in COMPANIES},
    }


# ── Main ──

def main():
    print("═══════════════════════════════════════════════════")
    print("  ROIC CALCULATION ENGINE")
    print("═══════════════════════════════════════════════════")
    
    csv_path = os.path.join(INPUT_DIR, "all_companies_quarterly.csv")
    
    if not os.path.exists(csv_path):
        print(f"⚠ CSV not found at {csv_path}")
        print("  Run the EDGAR agent first, or set INPUT_DIR")
        return
    
    # Load data
    data = load_combined_csv(csv_path)
    print(f"Loaded {len(data)} companies from CSV")
    
    # Build quarter list from data
    all_quarters = set()
    for ticker_data in data.values():
        for item_data in ticker_data.values():
            all_quarters.update(item_data.keys())
    
    quarters = sorted(all_quarters, key=lambda q: (int(q.split()[1]), int(q[1])))
    print(f"Quarters: {quarters[0]} to {quarters[-1]} ({len(quarters)} total)")
    
    # Calculate
    results = calculate_adjustments(data, quarters)
    indices = calculate_indices(results, quarters)
    
    print(f"\nIndex values (latest quarter):")
    latest = quarters[-1]
    for key in ["tier1", "tier2", "all", "gap"]:
        v = indices[key].get(latest)
        if v: print(f"  {key:8s}: {v:.1%}")
    
    # Generate outputs
    os.makedirs(os.path.join(OUTPUT_DIR, "public"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "internal"), exist_ok=True)
    
    pub = generate_public_json(results, indices, quarters, AI_EVENTS)
    with open(os.path.join(OUTPUT_DIR, "public", "data.json"), 'w') as f:
        json.dump(pub, f, indent=2)
    print(f"\n✓ Public data: {len(pub['scoreboard'])} companies, {len(quarters)} quarters")
    
    internal = generate_internal_json(results, indices, quarters, AI_EVENTS)
    with open(os.path.join(OUTPUT_DIR, "internal", "data.json"), 'w') as f:
        json.dump(internal, f, indent=2)
    print(f"✓ Internal data: {len(internal['companies'])} companies, full detail")


if __name__ == "__main__":
    main()
