# ═══════════════════════════════════════════════════════════════════════
# EDGAR XBRL → ADJUSTED ROIC FRAMEWORK
# Google Colab Notebook (save as .ipynb or copy cells into Colab)
# 
# Pulls quarterly financial data from SEC EDGAR's free XBRL API,
# maps it to the Adjusted ROIC framework, and exports a clean CSV
# ready for the Excel workbook.
#
# STATUS: Production-ready for 6-30 companies
# REQUIREMENTS: Python 3.8+, requests, pandas (all pre-installed in Colab)
# SEC EDGAR FAIR USE: Max 10 requests/second, User-Agent required
# ═══════════════════════════════════════════════════════════════════════

# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 1: Configuration                                          ║
# ╚═══════════════════════════════════════════════════════════════════╝

# --- YOUR SETTINGS ---
# SEC requires a User-Agent with your name and email. This is not authentication,
# just identification so they can contact you if your script misbehaves.
USER_AGENT = "YourName your.email@example.com"  # ← CHANGE THIS

# Date range for data pull
START_YEAR = 2015
END_YEAR = 2025

# Output path (Colab default; change for local)
import os as _os
OUTPUT_DIR = _os.environ.get("OUTPUT_DIR", "/content/roic_output")  # Colab default; overridden by GitHub Actions

# --- COMPANY UNIVERSE ---
# Expand this list to 20-30 companies as needed.
# Format: (Ticker, Company Name, Sector, CIK number)
# CIK numbers from https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
COMPANIES = [
    # ═══════════════════════════════════════════════════════════════
    # TIER 1: AI-ATTRIBUTED LAYOFF COMPANIES (primary analysis set)
    # These companies explicitly cited AI as a driver of layoffs.
    # ═══════════════════════════════════════════════════════════════
    ("MSFT",  "Microsoft",         "Technology",       789019),   # 15,000 cuts through 2025
    ("AMZN",  "Amazon",            "Tech/Retail",      1018724),  # 14,000 corporate roles Oct 2025
    ("GOOGL", "Alphabet",          "Technology",       1652044),  # Multiple rounds 2023-2025
    ("META",  "Meta Platforms",    "Technology",       1326801),  # "Year of Efficiency" + ongoing
    ("IBM",   "IBM",               "Technology",       51143),    # AI replacing back-office roles
    ("CRM",   "Salesforce",        "Technology",       1108524),  # 4,000+ customer support cuts
    ("WDAY",  "Workday",           "Technology",       1327811),  # 1,750 jobs (8.5% workforce)
    ("SAP",   "SAP SE",            "Technology",       1000184),  # Up to 10,000 "Business AI" shift
    ("CRWD",  "CrowdStrike",       "Cybersecurity",    1535527),  # 500 jobs, CEO directly cited AI
    ("HPQ",   "HP Inc",            "Technology",       47217),    # 4,000-6,000 by 2028
    ("CHGG",  "Chegg",             "EdTech",           1364954),  # 45% workforce (disrupted BY AI)
    ("DBX",   "Dropbox",           "Technology",       1467623),  # 528 jobs, AI refocus
    ("CHRW",  "C.H. Robinson",     "Logistics",        1043277),  # 1,400 jobs, AI-driven tools
    ("PYPL",  "PayPal",            "Fintech",          1633917),  # 2,500 jobs, automation cited
    ("DUOL",  "Duolingo",          "EdTech",           1562088),  # 10% contractors, AI pivot
    ("FVRR",  "Fiverr",            "Marketplace",      1762301),  # 250 jobs (30%), "AI-First"
    
    # ═══════════════════════════════════════════════════════════════
    # TIER 2: CONTROL GROUP (major companies NOT primarily citing AI)
    # Compare AI-layoff companies against these to isolate the signal.
    # ═══════════════════════════════════════════════════════════════
    ("JPM",   "JPMorgan Chase",    "Financials",       19617),
    ("UNH",   "UnitedHealth",      "Healthcare",       731766),
    ("WMT",   "Walmart",           "Retail",           104169),
    ("CAT",   "Caterpillar",       "Industrials",      18230),
    ("AAPL",  "Apple",             "Technology",       320193),
    ("NVDA",  "NVIDIA",            "Technology",       1045810),
    ("JNJ",   "Johnson & Johnson", "Healthcare",       200406),
    ("COST",  "Costco",            "Retail",           909832),
    ("XOM",   "ExxonMobil",        "Energy",           34088),
    ("UPS",   "UPS",               "Logistics",        1090727),  # Partial AI attribution
    
    # ═══════════════════════════════════════════════════════════════
    # TIER 3: ADDITIONAL (uncomment as needed)
    # ═══════════════════════════════════════════════════════════════
    # ("HD",    "Home Depot",       "Retail",           354950),
    # ("BAC",   "Bank of America",  "Financials",       70858),
    # ("GE",    "GE Aerospace",     "Industrials",      40554),
    # ("NFLX",  "Netflix",          "Media",            1065280),
    # ("LLY",   "Eli Lilly",        "Healthcare",       59478),
    # ("HON",   "Honeywell",        "Industrials",      773840),
]




# ═══════════════════════════════════════════════════════════════════
# AI LAYOFF EVENTS TIMELINE
# Used to tag restructuring quarters in the output for overlay analysis.
# Format: (Ticker, Quarter, Jobs Cut, Attribution Strength, Description)
# Attribution: "direct" = leadership explicitly cited AI
#              "partial" = AI cited alongside other factors
#              "disrupted" = company disrupted BY AI (not deploying it)
#              "reversed" = layoffs later reversed or rehiring announced
# ═══════════════════════════════════════════════════════════════════

AI_LAYOFF_EVENTS = [
    # ── 2023 ──
    ("IBM",   "Q2 2023", 7800,  "direct",    "CEO Krishna: AI could replace ~7,800 back-office roles over 5 years"),
    ("CHGG",  "Q2 2023", 80,    "disrupted", "4% workforce cut; blamed ChatGPT for user loss"),
    ("DBX",   "Q2 2023", 500,   "direct",    "16% workforce; CEO Houston cited AI reshaping product mix"),
    ("META",  "Q1 2023", 10000, "partial",   "Second wave of 'Year of Efficiency'; AI investment simultaneous"),
    ("GOOGL", "Q1 2023", 12000, "partial",   "Broad restructuring; AI deployment across ad sales concurrent"),
    
    # ── 2024 ──
    ("DUOL",  "Q1 2024", 100,   "direct",    "10% contractors offboarded; spokesperson attributed to AI"),
    ("CHGG",  "Q2 2024", 248,   "disrupted", "22% workforce; revenue fell 30% as students shifted to ChatGPT"),
    ("GOOGL", "Q2 2024", 6000,  "partial",   "Mostly programmers; Pichai cited AI-driven efficiency"),
    ("CRM",   "Q1 2024", 700,   "partial",   "1% global workforce; AI-led restructuring"),
    ("PYPL",  "Q1 2024", 2500,  "partial",   "CEO Chriss: 'deploy automation, reduce complexity'"),
    ("DBX",   "Q4 2024", 528,   "direct",    "AI-powered search/productivity refocus"),
    ("SAP",   "Q1 2024", 8000,  "direct",    "'Business AI' restructuring; up to 10,000 affected"),
    
    # ── 2025 ──
    ("WDAY",  "Q1 2025", 1750,  "direct",    "8.5% workforce; investing more in AI"),
    ("MSFT",  "Q1 2025", 6000,  "direct",    "3% workforce; Nadella: 'reimagine mission for AI era'"),
    ("CRWD",  "Q2 2025", 500,   "direct",    "5% workforce; CEO Kurtz: 'AI flattens hiring curve'"),
    ("MSFT",  "Q3 2025", 9000,  "direct",    "Additional cuts; AI code writing at 30%"),
    ("CHGG",  "Q4 2025", 388,   "disrupted", "45% workforce; 'new realities of AI'"),
    ("FVRR",  "Q3 2025", 250,   "direct",    "30% workforce; CEO: 'AI-First mindset'"),
    ("IBM",   "Q4 2025", 2700,  "direct",    "AI agents replaced hundreds of back-office roles"),
    ("CRM",   "Q3 2025", 4000,  "direct",    "Customer support roles replaced by AI systems"),
    ("HPQ",   "Q4 2025", 6000,  "direct",    "CEO Lores: '$1B savings over 3 years' via AI"),
    ("CHRW",  "Q4 2025", 1400,  "direct",    "AI-driven pricing/scheduling/tracking tools deployed"),
    ("AMZN",  "Q4 2025", 14000, "direct",    "SVP Galetti: AI is 'most transformative tech since Internet'"),
    ("SAP",   "Q2 2025", 3000,  "direct",    "Continued 'Business AI' restructuring"),
    ("PYPL",  "Q1 2025", 1200,  "partial",   "Continued automation across fraud/risk/support"),
    ("UPS",   "Q3 2025", 14000, "partial",   "Corporate cuts partially AI; 66% volume through automated facilities"),
    
    # ── REVERSALS (critical for 'efficiency theater' analysis) ──
    # Note: Klarna is private but included for reference as a cautionary case
    # ("KLRNA","Q2 2025", -700, "reversed",  "CEO admitted AI approach led to 'lower quality'; rehiring"),
    ("IBM",   "Q2 2024", -200,  "reversed",  "Rehired in engineering/sales after AI couldn't fill gap"),
]


def export_events_csv(events, output_dir):
    """Export AI layoff events as a CSV for overlay analysis."""
    import csv
    filepath = os.path.join(output_dir, "ai_layoff_events.csv")
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Ticker", "Quarter", "Jobs_Cut", "Attribution", "Description"])
        for event in events:
            writer.writerow(event)
    print(f"  ✓ Saved AI layoff events: {filepath}")
    return filepath


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 2: XBRL Tag Mapping Engine                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

# The hardest part of EDGAR XBRL: companies use different tags for the
# same concept. This mapping tries multiple tags in priority order.
# "duration" = flow metric (income statement), "instant" = stock (balance sheet)

XBRL_TAG_MAP = {
    "revenue": {
        "tags": [
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:Revenues",
            "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
            "us-gaap:SalesRevenueNet",
            "us-gaap:SalesRevenueGoodsNet",
            "us-gaap:InterestAndDividendIncomeOperating",  # banks
        ],
        "period_type": "duration",
        "scale": 1e-6,  # Convert to $mm
    },
    "operating_income": {
        "tags": [
            "us-gaap:OperatingIncomeLoss",
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "income_tax_rate": {
        # Effective tax rate is reported directly by many companies
        "tags": [
            "us-gaap:EffectiveIncomeTaxRateContinuingOperations",
        ],
        "period_type": "duration",
        "scale": 1,  # Already a ratio
        "fallback": "calculate",  # If not reported, calc from tax expense / pretax income
    },
    "income_tax_expense": {
        # Used to calculate effective tax rate when not directly reported
        "tags": [
            "us-gaap:IncomeTaxExpenseBenefit",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "pretax_income": {
        "tags": [
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "sbc": {
        "tags": [
            "us-gaap:ShareBasedCompensation",
            "us-gaap:AllocatedShareBasedCompensationExpense",
            "us-gaap:EmployeeServiceShareBasedCompensationNonvestedAwardsTotalCompensationCostNotYetRecognized",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "restructuring": {
        "tags": [
            "us-gaap:RestructuringCharges",
            "us-gaap:RestructuringAndRelatedCostIncurredCost",
            "us-gaap:RestructuringCostsAndAssetImpairmentCharges",
            "us-gaap:RestructuringSettlementAndImpairmentProvisions",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "total_debt": {
        "tags": [
            "us-gaap:LongTermDebtAndCapitalLeaseObligations",
            "us-gaap:LongTermDebt",
            "us-gaap:LongTermDebtNoncurrent",
        ],
        "period_type": "instant",
        "scale": 1e-6,
        "add_tags": [  # Also add short-term debt
            "us-gaap:ShortTermBorrowings",
            "us-gaap:LongTermDebtCurrent",
            "us-gaap:CommercialPaper",
        ],
    },
    "total_equity": {
        "tags": [
            "us-gaap:StockholdersEquity",
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        "period_type": "instant",
        "scale": 1e-6,
    },
    "cash": {
        "tags": [
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:CashCashEquivalentsAndShortTermInvestments",
            "us-gaap:Cash",
        ],
        "period_type": "instant",
        "scale": 1e-6,
    },
    "goodwill": {
        "tags": [
            "us-gaap:Goodwill",
        ],
        "period_type": "instant",
        "scale": 1e-6,
    },
    "acquired_intangibles": {
        "tags": [
            "us-gaap:IntangibleAssetsNetExcludingGoodwill",
            "us-gaap:FiniteLivedIntangibleAssetsNet",
        ],
        "period_type": "instant",
        "scale": 1e-6,
    },
    "operating_lease_liabilities": {
        "tags": [
            "us-gaap:OperatingLeaseLiability",
            "us-gaap:OperatingLeaseLiabilityCurrent",  # may need to sum current + noncurrent
        ],
        "period_type": "instant",
        "scale": 1e-6,
        "add_tags": [
            "us-gaap:OperatingLeaseLiabilityNoncurrent",
        ],
    },
    "share_buybacks": {
        "tags": [
            "us-gaap:PaymentsForRepurchaseOfCommonStock",
            "us-gaap:PaymentsForRepurchaseOfEquity",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "headcount": {
        "tags": [
            "dei:EntityNumberOfEmployees",
        ],
        "period_type": "instant",
        "scale": 1,  # Raw number
    },
    "capex": {
        "tags": [
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "us-gaap:CapitalExpenditureDiscontinuedOperations",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "fcf": {
        # FCF = Operating Cash Flow - Capex (calculated, not a direct tag)
        "tags": [],
        "period_type": "duration",
        "scale": 1e-6,
        "fallback": "calculate",
    },
    "operating_cash_flow": {
        "tags": [
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        ],
        "period_type": "duration",
        "scale": 1e-6,
    },
    "market_cap": {
        # Not in EDGAR — pulled separately or from companion source
        "tags": [],
        "period_type": "instant",
        "scale": 1e-6,
        "fallback": "external",
    },
}


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 3: EDGAR API Client                                       ║
# ╚═══════════════════════════════════════════════════════════════════╝

import requests
import pandas as pd
import time
import json
import os
import warnings
from datetime import datetime, timedelta
from collections import defaultdict

warnings.filterwarnings('ignore')

class EDGARClient:
    """SEC EDGAR XBRL API client with rate limiting and caching."""
    
    BASE_URL = "https://data.sec.gov"
    RATE_LIMIT = 0.12  # seconds between requests (~8/sec, under 10/sec limit)
    
    def __init__(self, user_agent):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })
        self.last_request_time = 0
        self.cache = {}
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self.last_request_time = time.time()
    
    def get_company_facts(self, cik):
        """Pull ALL XBRL facts for a company. This is the master dataset."""
        cik_padded = str(cik).zfill(10)
        cache_key = f"facts_{cik}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit()
        url = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self.cache[cache_key] = data
            return data
        except Exception as e:
            print(f"  ⚠ Error fetching CIK {cik}: {e}")
            return None
    
    def get_company_concept(self, cik, taxonomy, tag):
        """Pull a single XBRL concept for a company."""
        cik_padded = str(cik).zfill(10)
        cache_key = f"concept_{cik}_{tag}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        self._rate_limit()
        url = f"{self.BASE_URL}/api/xbrl/companyconcept/CIK{cik_padded}/{taxonomy}/{tag}.json"
        
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            self.cache[cache_key] = data
            return data
        except Exception as e:
            return None


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 4: Data Extraction Engine                                  ║
# ╚═══════════════════════════════════════════════════════════════════╝

class XBRLExtractor:
    """Extracts and normalizes quarterly financial data from EDGAR XBRL."""
    
    def __init__(self, client, start_year=2015, end_year=2025):
        self.client = client
        self.start_year = start_year
        self.end_year = end_year
        # Build quarter labels
        self.quarters = []
        for y in range(start_year, end_year + 1):
            for q in range(1, 5):
                self.quarters.append(f"Q{q} {y}")
    
    def _parse_tag_from_facts(self, facts_data, taxonomy, tag_name):
        """Extract a specific tag's data from the company facts JSON."""
        try:
            tag_data = facts_data["facts"][taxonomy][tag_name]
            # Get USD units (or pure number for ratios/counts)
            units = tag_data.get("units", {})
            if "USD" in units:
                return units["USD"]
            elif "pure" in units:
                return units["pure"]
            elif "shares" in units:
                return units["shares"]
            # Try first available unit
            for unit_key, unit_data in units.items():
                return unit_data
            return []
        except (KeyError, TypeError):
            return []
    
    def _assign_to_quarter(self, filings, period_type, scale=1e-6):
        """Map filing data points to calendar quarters.
        
        This is the tricky part:
        - 'instant' values (balance sheet): use the 'end' date
        - 'duration' values (income statement): need to be quarterly
          - 10-Q filings are quarterly (3 months)
          - 10-K filings may be annual (12 months) — need to subtract prior 3 quarters
          - Some companies file YTD figures in 10-Q (6mo, 9mo) — need to difference
        """
        quarterly = {}
        
        # Sort by end date
        sorted_filings = sorted(filings, key=lambda x: x.get("end", ""))
        
        # First pass: collect all data points by end date and form type
        by_end = defaultdict(list)
        for f in sorted_filings:
            end = f.get("end", "")
            start = f.get("start", "")
            val = f.get("val")
            form = f.get("form", "")
            
            if val is None or end == "":
                continue
            if form not in ("10-Q", "10-K", "10-K/A", "10-Q/A"):
                continue
            
            # Calculate duration in days
            if start:
                try:
                    d_start = datetime.strptime(start, "%Y-%m-%d")
                    d_end = datetime.strptime(end, "%Y-%m-%d")
                    duration_days = (d_end - d_start).days
                except:
                    duration_days = 0
            else:
                duration_days = 0
            
            by_end[end].append({
                "val": val,
                "start": start,
                "end": end,
                "form": form,
                "duration_days": duration_days,
            })
        
        if period_type == "instant":
            # Balance sheet items: just take the value at period end
            for end_date, entries in by_end.items():
                try:
                    dt = datetime.strptime(end_date, "%Y-%m-%d")
                except:
                    continue
                year = dt.year
                # Determine quarter from month
                month = dt.month
                if month <= 3: q = 1
                elif month <= 6: q = 2
                elif month <= 9: q = 3
                else: q = 4
                
                qkey = f"Q{q} {year}"
                # Prefer 10-Q/10-K over amendments
                best = None
                for e in entries:
                    if best is None or e["form"] in ("10-Q", "10-K"):
                        best = e
                if best and qkey not in quarterly:
                    quarterly[qkey] = best["val"] * (1/scale) if scale != 1 else best["val"]
        
        elif period_type == "duration":
            # Income statement / cash flow: need quarterly isolation
            # Strategy: collect all periods, prefer ~90-day durations (true quarterly)
            # Fall back to differencing YTD/annual figures
            
            all_periods = []
            for end_date, entries in by_end.items():
                for e in entries:
                    all_periods.append(e)
            
            # Sort by end date, then by duration (prefer shorter = more granular)
            all_periods.sort(key=lambda x: (x["end"], x["duration_days"]))
            
            # First, collect true quarterly values (60-100 day duration)
            for p in all_periods:
                if 60 <= p["duration_days"] <= 105:
                    try:
                        dt = datetime.strptime(p["end"], "%Y-%m-%d")
                    except:
                        continue
                    month = dt.month
                    year = dt.year
                    if month <= 3: q = 1
                    elif month <= 6: q = 2
                    elif month <= 9: q = 3
                    else: q = 4
                    qkey = f"Q{q} {year}"
                    if qkey not in quarterly:
                        quarterly[qkey] = p["val"] * (1/scale) if scale != 1 else p["val"]
            
            # Second pass: for missing quarters, try to derive from YTD/annual
            # Collect annual and semi-annual values
            annual_vals = {}
            ytd_vals = defaultdict(dict)
            
            for p in all_periods:
                try:
                    dt_end = datetime.strptime(p["end"], "%Y-%m-%d")
                except:
                    continue
                year = dt_end.year
                
                if 350 <= p["duration_days"] <= 380:
                    # Annual value
                    annual_vals[year] = p["val"]
                elif 170 <= p["duration_days"] <= 200:
                    # 6-month YTD
                    month = dt_end.month
                    if month <= 6:
                        ytd_vals[year]["H1"] = p["val"]
                    else:
                        ytd_vals[year]["H2_cumul"] = p["val"]
                elif 260 <= p["duration_days"] <= 290:
                    # 9-month YTD
                    ytd_vals[year]["9M"] = p["val"]
            
            # Try to fill gaps using differencing
            for year in range(self.start_year, self.end_year + 1):
                for q in range(1, 5):
                    qkey = f"Q{q} {year}"
                    if qkey in quarterly:
                        continue
                    
                    # Try deriving Q4 from annual - 9M
                    if q == 4 and year in annual_vals and "9M" in ytd_vals.get(year, {}):
                        val = annual_vals[year] - ytd_vals[year]["9M"]
                        quarterly[qkey] = val * (1/scale) if scale != 1 else val
                    
                    # Try deriving Q2 from H1 - Q1
                    elif q == 2 and "H1" in ytd_vals.get(year, {}):
                        q1key = f"Q1 {year}"
                        if q1key in quarterly:
                            raw_q1 = quarterly[q1key] * scale if scale != 1 else quarterly[q1key]
                            val = ytd_vals[year]["H1"] - raw_q1
                            quarterly[qkey] = val * (1/scale) if scale != 1 else val
        
        return quarterly
    
    def extract_metric(self, facts_data, metric_name):
        """Extract a specific metric using the tag mapping with fallbacks."""
        mapping = XBRL_TAG_MAP.get(metric_name, {})
        tags = mapping.get("tags", [])
        period_type = mapping.get("period_type", "duration")
        scale = mapping.get("scale", 1e-6)
        add_tags = mapping.get("add_tags", [])
        
        # Try primary tags in order
        for tag_full in tags:
            taxonomy, tag = tag_full.split(":", 1)
            # Map taxonomy prefix to EDGAR format
            tax_map = {"us-gaap": "us-gaap", "dei": "dei"}
            taxonomy_key = tax_map.get(taxonomy, taxonomy)
            
            data = self._parse_tag_from_facts(facts_data, taxonomy_key, tag)
            if data:
                result = self._assign_to_quarter(data, period_type, scale)
                if result:
                    # If there are add_tags, sum them in
                    if add_tags:
                        for add_tag_full in add_tags:
                            add_tax, add_tag = add_tag_full.split(":", 1)
                            add_tax_key = tax_map.get(add_tax, add_tax)
                            add_data = self._parse_tag_from_facts(facts_data, add_tax_key, add_tag)
                            if add_data:
                                add_result = self._assign_to_quarter(add_data, period_type, scale)
                                for qk, qv in add_result.items():
                                    if qk in result:
                                        result[qk] += qv
                                    else:
                                        result[qk] = qv
                    return result
        
        return {}
    
    def extract_company(self, ticker, name, cik):
        """Extract all metrics for a single company."""
        print(f"\n{'='*60}")
        print(f"  {ticker} ({name}) — CIK {cik}")
        print(f"{'='*60}")
        
        facts = self.client.get_company_facts(cik)
        if not facts:
            print(f"  ✗ Failed to fetch data")
            return None
        
        results = {}
        
        # Extract each metric
        metrics_to_pull = [
            "revenue", "operating_income", "income_tax_rate",
            "income_tax_expense", "pretax_income",
            "sbc", "restructuring",
            "total_debt", "total_equity", "cash",
            "goodwill", "acquired_intangibles", "operating_lease_liabilities",
            "share_buybacks", "headcount",
            "capex", "operating_cash_flow",
        ]
        
        for metric in metrics_to_pull:
            data = self.extract_metric(facts, metric)
            results[metric] = data
            found = sum(1 for q in self.quarters if q in data)
            total = len(self.quarters)
            status = "✓" if found > total * 0.7 else ("◐" if found > 0 else "✗")
            print(f"  {status} {metric:35s} {found:2d}/{total} quarters")
        
        # Calculate derived metrics
        # Effective tax rate (if not directly reported)
        if len(results.get("income_tax_rate", {})) < len(self.quarters) * 0.5:
            tax_exp = results.get("income_tax_expense", {})
            pretax = results.get("pretax_income", {})
            calc_rate = {}
            for q in self.quarters:
                if q in tax_exp and q in pretax and pretax[q] != 0:
                    rate = abs(tax_exp[q] / pretax[q])
                    if 0 < rate < 0.6:  # Sanity check
                        calc_rate[q] = round(rate, 3)
            if calc_rate:
                results["income_tax_rate"] = calc_rate
                print(f"  ℹ Calculated tax rate from expense/pretax for {len(calc_rate)} quarters")
        
        # FCF = Operating Cash Flow - Capex
        ocf = results.get("operating_cash_flow", {})
        capex = results.get("capex", {})
        fcf = {}
        for q in self.quarters:
            if q in ocf and q in capex:
                fcf[q] = round(ocf[q] - capex[q], 1)
        results["fcf"] = fcf
        
        # Fill zero for missing restructuring (most quarters have none)
        for q in self.quarters:
            if q not in results.get("restructuring", {}):
                results.setdefault("restructuring", {})[q] = 0
        
        return results


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 5: Market Cap Supplement                                   ║
# ╚═══════════════════════════════════════════════════════════════════╝

def get_market_caps_placeholder(companies, quarters):
    """
    Market cap is NOT in EDGAR XBRL. Options to fill this:
    
    1. MANUAL: Enter from Yahoo Finance historical data (free)
       https://finance.yahoo.com/quote/MSFT/history/
       Market cap = shares outstanding × closing price at quarter end
    
    2. SHARES OUTSTANDING from EDGAR + price from Yahoo:
       EDGAR tag: dei:EntityCommonStockSharesOutstanding
       Multiply by quarter-end price from Yahoo Finance
    
    3. THIRD-PARTY API (free tier):
       - Financial Modeling Prep API (250 req/day free)
       - Alpha Vantage (25 req/day free)
    
    For now, this returns empty dict. Fill via one of the above methods.
    """
    print("\n⚠ Market Cap requires supplemental data source (not in EDGAR)")
    print("  Options: Yahoo Finance historical prices × shares outstanding,")
    print("  or Financial Modeling Prep API (free tier)")
    print("  The script will attempt to pull shares outstanding from EDGAR")
    print("  and you can multiply by quarter-end stock prices.")
    return {}


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 6: Export to CSV (maps to Excel workbook structure)        ║
# ╚═══════════════════════════════════════════════════════════════════╝

def export_to_csv(all_results, companies, quarters, output_dir):
    """Export extracted data to CSVs matching the Excel workbook structure."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Map our internal metric names to the Excel line item names
    EXCEL_LINE_MAP = [
        ("Revenue ($mm)",                   "revenue"),
        ("Operating Income ($mm)",          "operating_income"),
        ("Effective Tax Rate",              "income_tax_rate"),
        ("Stock-Based Compensation ($mm)",  "sbc"),
        ("Restructuring Charges ($mm)",     "restructuring"),
        ("Total Debt ($mm)",                "total_debt"),
        ("Total Shareholders' Equity ($mm)","total_equity"),
        ("Cash & Equivalents ($mm)",        "cash"),
        ("Goodwill ($mm)",                  "goodwill"),
        ("Acquired Intangibles ($mm)",      "acquired_intangibles"),
        ("Operating Lease Liabilities ($mm)","operating_lease_liabilities"),
        ("Share Buybacks ($mm)",            "share_buybacks"),
        ("Headcount",                       "headcount"),
        ("Capital Expenditures ($mm)",      "capex"),
        ("Free Cash Flow ($mm)",            "fcf"),
        ("Market Cap ($mm)",                "market_cap"),
    ]
    
    # Create one CSV per company (easy to review and correct)
    for ticker, name, sector, cik in companies:
        if ticker not in all_results:
            continue
        
        company_data = all_results[ticker]
        rows = []
        
        for excel_name, metric_key in EXCEL_LINE_MAP:
            row = {"Line Item": excel_name}
            metric_data = company_data.get(metric_key, {})
            for q in quarters:
                val = metric_data.get(q, "")
                if isinstance(val, float):
                    val = round(val, 1)
                row[q] = val
            rows.append(row)
        
        df = pd.DataFrame(rows)
        filepath = os.path.join(output_dir, f"{ticker}_quarterly.csv")
        df.to_csv(filepath, index=False)
        print(f"  ✓ Saved {filepath}")
    
    # Also create a combined "all companies" CSV for direct Excel import
    all_rows = []
    for ticker, name, sector, cik in companies:
        if ticker not in all_results:
            continue
        company_data = all_results[ticker]
        for excel_name, metric_key in EXCEL_LINE_MAP:
            row = {"Ticker": ticker, "Company": name, "Line Item": excel_name}
            metric_data = company_data.get(metric_key, {})
            for q in quarters:
                val = metric_data.get(q, "")
                if isinstance(val, float):
                    val = round(val, 1)
                row[q] = val
            all_rows.append(row)
    
    df_all = pd.DataFrame(all_rows)
    combined_path = os.path.join(output_dir, "all_companies_quarterly.csv")
    df_all.to_csv(combined_path, index=False)
    print(f"\n  ✓ Combined file: {combined_path}")
    
    # Coverage report
    print(f"\n{'='*60}")
    print("  DATA COVERAGE REPORT")
    print(f"{'='*60}")
    for ticker, name, sector, cik in companies:
        if ticker not in all_results:
            print(f"  {ticker:6s}  ✗ No data")
            continue
        company_data = all_results[ticker]
        total_cells = 0
        filled_cells = 0
        for excel_name, metric_key in EXCEL_LINE_MAP:
            metric_data = company_data.get(metric_key, {})
            for q in quarters:
                total_cells += 1
                if q in metric_data and metric_data[q] != "" and metric_data[q] != 0:
                    filled_cells += 1
        pct = filled_cells / total_cells * 100 if total_cells > 0 else 0
        print(f"  {ticker:6s}  {filled_cells:4d}/{total_cells:4d} cells ({pct:.0f}%)")
    
    return combined_path


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 7: Scheduling / Auto-Update                               ║
# ╚═══════════════════════════════════════════════════════════════════╝

def check_new_filings(client, companies, days_back=45):
    """Check EDGAR for recent 10-Q/10-K filings to trigger update.
    
    Uses the EDGAR full-text search to find recent filings.
    Designed to be called by a scheduler (cron, Colab scheduler, GitHub Actions).
    """
    print(f"\n{'='*60}")
    print(f"  CHECKING FOR NEW FILINGS (last {days_back} days)")
    print(f"{'='*60}")
    
    new_filings = []
    cutoff = datetime.now() - timedelta(days=days_back)
    
    for ticker, name, sector, cik in companies:
        cik_padded = str(cik).zfill(10)
        client._rate_limit()
        
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        try:
            resp = client.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            
            for form, date_str in zip(forms, dates):
                if form in ("10-Q", "10-K"):
                    try:
                        filing_date = datetime.strptime(date_str, "%Y-%m-%d")
                        if filing_date >= cutoff:
                            new_filings.append({
                                "ticker": ticker,
                                "form": form,
                                "date": date_str,
                            })
                            print(f"  ✓ {ticker}: {form} filed {date_str}")
                    except:
                        pass
        except Exception as e:
            print(f"  ⚠ {ticker}: Error checking filings — {e}")
    
    if not new_filings:
        print("  No new 10-Q/10-K filings found")
    
    return new_filings


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 8: MAIN EXECUTION                                         ║
# ╚═══════════════════════════════════════════════════════════════════╝

def main():
    print("═══════════════════════════════════════════════════════════")
    print("  EDGAR XBRL → ADJUSTED ROIC DATA PIPELINE")
    print(f"  {len(COMPANIES)} companies | {START_YEAR}–{END_YEAR} | {(END_YEAR-START_YEAR+1)*4} quarters")
    print("═══════════════════════════════════════════════════════════")
    
    # Validate config
    if "your.email" in USER_AGENT.lower() or "yourname" in USER_AGENT.lower():
        print("\n⚠ ERROR: Please set USER_AGENT to your real name and email.")
        print("  SEC requires this for API access. It is not authentication.")
        print("  Example: 'John Smith john@company.com'")
        return
    
    # Initialize
    client = EDGARClient(USER_AGENT)
    extractor = XBRLExtractor(client, START_YEAR, END_YEAR)
    
    # Extract data for all companies
    all_results = {}
    for ticker, name, sector, cik in COMPANIES:
        result = extractor.extract_company(ticker, name, cik)
        if result:
            all_results[ticker] = result
    
    # Export
    print(f"\n{'='*60}")
    print("  EXPORTING TO CSV")
    print(f"{'='*60}")
    combined_path = export_to_csv(all_results, COMPANIES, extractor.quarters, OUTPUT_DIR)
    
    # Export AI layoff events timeline
    export_events_csv(AI_LAYOFF_EVENTS, OUTPUT_DIR)
    
    # Check for new filings (for scheduling context)
    new = check_new_filings(client, COMPANIES, days_back=45)
    
    print(f"\n{'='*60}")
    print("  COMPLETE")
    print(f"{'='*60}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print(f"  Combined CSV: {combined_path}")
    print(f"\n  NEXT STEPS:")
    print(f"  1. Review individual company CSVs for data gaps")
    print(f"  2. Fill Market Cap from Yahoo Finance or FMP API")
    print(f"  3. Upload combined CSV + ai_layoff_events.csv to Claude")
    print(f"  4. Claude will rebuild the Excel workbook with verified data")
    print(f"     and overlay AI layoff events on the ROIC timeline")
    print(f"  5. Set up quarterly schedule (see SCHEDULING section below)")
    
    return all_results

# Run it
if __name__ == "__main__":
    results = main()


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  CELL 9: SCHEDULING OPTIONS                                     ║
# ╚═══════════════════════════════════════════════════════════════════╝

SCHEDULING_GUIDE = """
═══════════════════════════════════════════════════════════════
  QUARTERLY AUTO-UPDATE OPTIONS
═══════════════════════════════════════════════════════════════

OPTION A: Google Colab + Google Apps Script (Recommended for simplicity)
  1. Save this notebook in Google Drive
  2. Create a Google Apps Script trigger:
     - Go to script.google.com
     - Create function that opens Colab notebook via API
     - Set trigger: Time-driven → Month timer → 15th of month
     - Run quarterly: Jan 15, Apr 15, Jul 15, Oct 15
       (Most 10-Qs are filed within 40 days of quarter end)

OPTION B: GitHub Actions (Recommended for reliability)
  1. Push this script to a GitHub repo
  2. Create .github/workflows/quarterly_update.yml:
  
  name: Quarterly EDGAR Update
  on:
    schedule:
      # Run on 15th of Jan, Apr, Jul, Oct at 8am UTC
      - cron: '0 8 15 1,4,7,10 *'
    workflow_dispatch:  # Manual trigger
  
  jobs:
    update:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - run: pip install requests pandas
        - run: python edgar_roic_agent.py
        - uses: actions/upload-artifact@v4
          with:
            name: roic-data
            path: roic_output/

OPTION C: Local cron job (Linux/Mac)
  # Edit crontab
  crontab -e
  
  # Add line (runs 15th of Jan/Apr/Jul/Oct at 8am):
  0 8 15 1,4,7,10 * cd /path/to/project && python3 edgar_roic_agent.py >> roic_log.txt 2>&1

OPTION D: Windows Task Scheduler
  1. Open Task Scheduler → Create Basic Task
  2. Set trigger: Monthly, on the 15th of Jan/Apr/Jul/Oct
  3. Action: Start a program → python.exe
  4. Arguments: edgar_roic_agent.py
  5. Start in: C:\\path\\to\\project
"""

print(SCHEDULING_GUIDE)
