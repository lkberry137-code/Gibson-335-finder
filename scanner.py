"""
Gibson ES-335 UK Deal Scanner & Travel Engine
Base Locations: Hull (HU1 1AA) & Burnham-on-Sea (TA8 1PE)
"""

import sys
import os
import json
import re
import math
import time
from datetime import datetime, timezone
import sqlite3
import urllib.request
import urllib.parse
import threading
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler

# ---------------------------------------------------------
# 1. BASE CONFIGURATION & HUBS
# ---------------------------------------------------------
HOME_BASES = {
    "Hull": {
        "name": "Hull HQ",
        "postcode": "HU1 1AA",
        "lat": 53.7457,
        "lng": -0.3367,
        "standard_max_hours": 3.0,
        "grail_max_hours": 4.5
    },
    "Somerset": {
        "name": "Somerset Family Base",
        "postcode": "TA8 1PE",
        "lat": 51.2383,
        "lng": -2.9972,
        "standard_max_hours": 1.5,
        "grail_max_hours": 2.5
    }
}

WATCHED_SHOPIFY_DEALERS = [
    {"name": "In Bloom Guitars", "url": "https://inbloomguitars.co.uk", "postcode": "RG1 1DN"},
    {"name": "Jordan Guitars", "url": "https://jordanguitars.co.uk", "postcode": "NR1 1AA"},
    {"name": "Peach Guitars", "url": "https://www.peachguitars.com", "postcode": "CO4 9QP"},
    {"name": "Coda Music", "url": "https://www.coda-music.com", "postcode": "SG6 2AL"},
    {"name": "Guitar Village", "url": "https://guitarvillage.co.uk", "postcode": "GU9 7ND"}
]

# ---------------------------------------------------------
# 2. TRAVEL & PETROL COST CALCULATOR
# ---------------------------------------------------------
POSTCODE_CACHE = {
    "HU1 1AA": (53.7457, -0.3367),
    "TA8 1PE": (51.2383, -2.9972),
    "RG1 1DN": (51.4543, -0.9781),
    "NR1 1AA": (52.6284, 1.2996),
    "CO4 9QP": (51.9056, 0.9419),
    "SG6 2AL": (51.9772, -0.2285),
    "GU9 7ND": (51.2141, -0.7984),
    "SW1A 1AA": (51.5014, -0.1419),
    "M1 1AE": (53.4808, -2.2426),
    "B1 1AA": (52.4772, -1.8986),
    "LS1 1AA": (53.7960, -1.5478),
    "BS1 1AA": (51.4545, -2.5879),
    "G1 1AA": (55.8642, -4.2518),
    "EH1 1AA": (55.9533, -3.1883),
    "NG18 1AA": (53.1436, -1.1983), # Mansfield
    "NG1 1AA": (52.9536, -1.1505),  # Nottingham
    "DE1 1AA": (52.9225, -1.4746),  # Derby
    "LE1 1AA": (52.6369, -1.1398),  # Leicester
    "DN1 1AA": (53.5228, -1.1311),  # Doncaster
    "YO1 7HH": (53.9599, -1.0873),  # York
    "YO8 8LZ": (53.7665, -1.0670),  # Selby
    "S1 2GE": (53.3811, -1.4701),   # Sheffield
    "S9 3RP": (53.4055, -1.4190),   # Sheffield Meadowhall
    "L1 8JQ": (53.4046, -2.9872),   # Liverpool
    "NE1 1AA": (54.9783, -1.6178),  # Newcastle
    "OX1 1AA": (51.7520, -1.2577),  # Oxford
    "CB1 1AA": (52.2053, 0.1218),   # Cambridge
    "BA1 1AA": (51.3811, -2.3590),   # Bath
    "CF10 1AA": (51.4816, -3.1791), # Cardiff
    "GL50 1TA": (51.8994, -2.0783), # Cheltenham
    "GU1 4RF": (51.2362, -0.5704),  # Guildford
    "PR7 1NY": (53.6534, -2.6325),  # Ormskirk
    "WC2H 8LP": (51.5152, -0.1292), # Denmark St London
    "WC2H 8LA": (51.5152, -0.1292), # Denmark St London
    "B5 4SL": (52.4737, -1.8947),   # Birmingham Fair Deal
    "PE29 3NW": (52.3304, -0.1846), # Huntingdon Music Street
    "GL10 2BG": (51.7463, -2.2869)  # Stonehouse World Guitars
}

UK_CITY_POSTCODES = {
    "hull": "HU1 1AA", "beverley": "HU17 8DB", "york": "YO1 7HH", "selby": "YO8 8LZ",
    "leeds": "LS1 1AA", "sheffield": "S1 2GE", "grimsby": "DN31 1AA", "scunthorpe": "DN15 6AA",
    "doncaster": "DN1 1AA", "mansfield": "NG18 1AA", "nottingham": "NG1 1AA", "derby": "DE1 1AA",
    "leicester": "LE1 1AA", "lincoln": "LN1 1AA", "liverpool": "L1 8JQ", "manchester": "M1 1AE",
    "bristol": "BS1 1AA", "bath": "BA1 1AA", "cardiff": "CF10 1AA", "london": "SW1A 1AA",
    "norwood": "SW1A 1AA", "birmingham": "B1 1AA", "norwich": "NR1 1AA", "colchester": "CO4 9QP",
    "newcastle": "NE1 1AA", "oxford": "OX1 1AA", "cambridge": "CB1 1AA", "exeter": "EX1 1AA",
    "plymouth": "PL1 1AA", "southampton": "SO14 1AA", "portsmouth": "PO1 1AA", "bournemouth": "BH1 1AA",
    "farnham": "GU9 7ND", "guildford": "GU1 4RF", "cheltenham": "GL50 1TA", "ormskirk": "PR7 1NY"
}

def resolve_uk_location_postcode(locality, shop_name=""):
    comb = f"{locality} {shop_name}".lower()
    for k, pc in UK_SHOP_POSTCODES.items():
        if k in comb:
            return pc
    for k, pc in UK_CITY_POSTCODES.items():
        if k in comb:
            return pc
    return "B1 1AA"

def get_postcode_coords(postcode):
    """Fetches (lat, lng) for a UK postcode or masked outcode (e.g. YO8***) via cache or postcodes.io."""
    if not postcode:
        return None
    clean = postcode.strip().upper()
    if clean in POSTCODE_CACHE:
        return POSTCODE_CACHE[clean]

    # Handle masked eBay UK postcodes like "YO8***" or "NG18***" -> outcode lookup
    if "*" in clean or len(clean.replace(" ", "")) <= 4:
        outcode = re.sub(r'[^A-Z0-9]', '', clean.split("*")[0]).strip()
        if outcode in POSTCODE_CACHE:
            return POSTCODE_CACHE[outcode]
        if outcode:
            try:
                req = urllib.request.Request(
                    f"https://api.postcodes.io/outcodes/{urllib.parse.quote(outcode)}",
                    headers={'User-Agent': 'Gibson335Radar/1.0'}
                )
                with urllib.request.urlopen(req, timeout=3) as res:
                    data = json.loads(res.read().decode())
                    if data.get("status") == 200 and "result" in data:
                        lat = data["result"]["latitude"]
                        lng = data["result"]["longitude"]
                        POSTCODE_CACHE[clean] = (lat, lng)
                        POSTCODE_CACHE[outcode] = (lat, lng)
                        return (lat, lng)
            except Exception:
                pass
        return None

    try:
        encoded = urllib.parse.quote(clean)
        req = urllib.request.Request(
            f"https://api.postcodes.io/postcodes/{encoded}",
            headers={'User-Agent': 'Gibson335Radar/1.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read().decode())
            if data.get("status") == 200 and "result" in data:
                lat = data["result"]["latitude"]
                lng = data["result"]["longitude"]
                POSTCODE_CACHE[clean] = (lat, lng)
                return (lat, lng)
    except Exception:
        # Fallback to outcode if full postcode fails
        outcode = clean.split()[0] if " " in clean else clean[:4]
        try:
            req = urllib.request.Request(
                f"https://api.postcodes.io/outcodes/{urllib.parse.quote(outcode)}",
                headers={'User-Agent': 'Gibson335Radar/1.0'}
            )
            with urllib.request.urlopen(req, timeout=3) as res:
                data = json.loads(res.read().decode())
                if data.get("status") == 200 and "result" in data:
                    lat = data["result"]["latitude"]
                    lng = data["result"]["longitude"]
                    POSTCODE_CACHE[clean] = (lat, lng)
                    return (lat, lng)
        except Exception:
            pass
    return None

def haversine_miles(lat1, lon1, lat2, lon2):
    """Calculates great-circle distance between two coordinates in miles."""
    r = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c

def calculate_travel_metrics(dest_coords, hub_name="Hull", car_mpg=38.0, fuel_price_per_litre=1.42):
    """
    Computes:
    - road_miles (approx 1.25x straight-line to account for UK road network)
    - round_trip_miles
    - drive_hours (estimated at 50 mph avg)
    - fuel_cost: ((round_trip_miles / mpg) * 4.54609) * fuel_price_per_litre
    """
    hub = HOME_BASES[hub_name]
    if not dest_coords:
        return {
            "one_way_miles": 0.0,
            "round_trip_miles": 0.0,
            "drive_hours": 0.0,
            "fuel_cost": 0.0
        }
    
    direct_miles = haversine_miles(hub["lat"], hub["lng"], dest_coords[0], dest_coords[1])
    road_miles = round(direct_miles * 1.25, 1)
    round_trip = round(road_miles * 2, 1)
    drive_hours = round(road_miles / 50.0, 1)
    
    gallons = round_trip / car_mpg
    litres = gallons * 4.54609
    fuel_cost = round(litres * fuel_price_per_litre, 2)
    
    return {
        "one_way_miles": road_miles,
        "round_trip_miles": round_trip,
        "drive_hours": drive_hours,
        "fuel_cost": fuel_cost
    }

# ---------------------------------------------------------
# 3. VALUATION & INTELLIGENCE ENGINE
# ---------------------------------------------------------
ERA_DATABASE = {
    (1990, 1999): {"name": "Good Wood Era", "badge": "⭐ GOOD WOOD (90s)", "boost": 1.0, "notes": "Honduran mahogany, early '57 Classics"},
    (2013, 2018): {"name": "Memphis Golden Age", "badge": "🎖️ MEMPHIS PEAK (13-18)", "boost": 0.5, "notes": "Rolled neck binding, Adirondack spruce, MHS PAFs"},
    (2020, 2026): {"name": "Modern Nashville", "badge": "🛡️ MODERN NASHVILLE", "boost": 0.0, "notes": "Calibrated T-Types, Rounded C neck, hand-wired"},
    (2012, 2012): {"name": "2012 Spec Alert", "badge": "⚠️ 2012 SPEC CHECK", "boost": -0.5, "notes": "Check for baked maple / laminated rosewood board"},
    (2015, 2015): {"name": "2015 Spec Alert", "badge": "⚠️ 2015 WIDE NECK", "boost": -0.5, "notes": "Check for wider fingerboard and zero-fret brass nut"},
    (1969, 1985): {"name": "Norlin Era", "badge": "🎸 NORLIN ERA", "boost": 0.0, "notes": "Check weight, 3-piece neck, volute"}
}

def detect_brand_tier(title, desc=""):
    combined = f"{title} {desc}".lower()
    if "epiphone" in combined and "elitist" not in combined:
        return "Epiphone (Exclude)"
    
    if "orville by gibson" in combined or "obg" in combined:
        return "Orville by Gibson"
    elif "orville" in combined:
        return "Orville MIJ"
    elif "heritage" in combined or "h-535" in combined:
        return "Heritage H-535"
    elif "tokai" in combined:
        return "Tokai Japan"
    elif "gibson" in combined:
        if "studio" in combined and "satin" not in combined:
            return "Gibson USA Studio"
        elif any(w in combined for w in ["custom shop", "historic", "1959", "1963", "murphy"]):
            return "Gibson Custom Shop"
        return "Gibson USA Standard"
    return "Other ES Equivalent"

def detect_era(text):
    # 1. Check explicit 4-digit year in title/description
    match = re.search(r'\b(19[6-9]\d|20[0-2]\d)\b', text)
    year = None
    if match:
        year = int(match.group(1))
    else:
        # 2. Check 9-digit Gibson serial number (e.g. #201230145: 1st digit '2' + 5th digit '3' = 2023)
        sn_match = re.search(r'#?(2\d{3})(\d)\d{4}', text)
        if sn_match:
            d1 = sn_match.group(1)[0]
            d5 = sn_match.group(2)
            year = int(f"20{d1}{d5}")

    if not year:
        return {"year": None, "name": "Standard / Unknown", "badge": "📅 ERA UNKNOWN", "boost": 0.0, "notes": "Year not specified"}
    for (start, end), data in ERA_DATABASE.items():
        if start <= year <= end:
            return {"year": year, **data}
    return {"year": year, "name": f"{year} Model", "badge": f"📅 {year}", "boost": 0.0, "notes": f"Production year {year}"}

def detect_repair_and_case(title, desc=""):
    combined = f"{title} {desc}".lower()
    
    repair_terms = [
        "headstock repair", "repaired headstock", "neck crack", "neck repair",
        "repaired neck", "smile repair", "heel repair", "repaired break"
    ]
    has_repair = any(term in combined for term in repair_terms)
    
    # Case Detection: Default to True if standard shop listing mentions case, False if explicitly no case/gig bag
    has_case = True
    if any(term in combined for term in ["no case", "gig bag", "gigbag", "soft case", "without case"]):
        has_case = False
    elif any(term in combined for term in ["ohsc", "hard case", "hardcase", "original case", "hiscox", "flight case"]):
        has_case = True
        
    return {"has_repair": has_repair, "has_case": has_case}

def detect_dexterity(title, desc=""):
    """Identifies if a listing is Left-Handed."""
    combined = f"{title} {desc}".lower()
    return bool(re.search(r'\b(left[\s-]?hand(ed)?|lh|lefty|southpaw)\b', combined))

def detect_shipping_info(source, title, price=0.0):
    """Determines shipping availability, fee, and carrier spec."""
    source_lower = str(source).lower()
    title_lower = str(title).lower()

    if any(term in title_lower for term in ["collection only", "pick up only", "pickup only", "no shipping"]):
        return {
            "shipping_available": False,
            "shipping_cost": 0.0,
            "shipping_carrier": "Collection in Person Only"
        }

    if "facebook" in source_lower:
        return {
            "shipping_available": False,
            "shipping_cost": 0.0,
            "shipping_carrier": "Collection in Person (Local)"
        }

    if "gumtree" in source_lower:
        return {
            "shipping_available": True,
            "shipping_cost": 35.0,
            "shipping_carrier": "Insured Courier (£35) or Free Collection"
        }

    dealers = ["peach", "jordan", "coda", "bonners", "wildwire", "rich tone", "sound affects", "gas station", "atb", "sutton", "in bloom"]
    if any(d in source_lower for d in dealers):
        if price >= 2400:
            return {
                "shipping_available": True,
                "shipping_cost": 0.0,
                "shipping_carrier": "Free Insured Next-Day UK Delivery"
            }
        return {
            "shipping_available": True,
            "shipping_cost": 25.0,
            "shipping_carrier": "Insured 24h Courier (£25)"
        }

    return {
        "shipping_available": True,
        "shipping_cost": 30.0,
        "shipping_carrier": "Tracked & Insured Courier (£30)"
    }

def evaluate_deal(price, brand_tier, era_boost, has_repair, has_case, drive_hours, max_hours=3.0, fuel_cost=0.0):
    """
    Core Deal Grading:
    Computes True Landed Cost = Price + Fuel Cost + Case Penalty (£150 if no case)
    Returns Grade (A+, A, B+, B, C) and summary reasoning.
    """
    case_penalty = 0 if has_case else 150
    true_landed_cost = round(price + fuel_cost + case_penalty, 2)
    
    # Extreme distance filter
    if drive_hours > 4.5:
        return {
            "grade": "C",
            "badge_class": "bg-stone-700 text-stone-300",
            "verdict": "Too Far",
            "reason": f"Drive time ({drive_hours}h) exceeds the 4.5h hard travel cap.",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }
    
    # Repaired headstock rule
    if has_repair:
        if true_landed_cost <= 1450:
            return {
                "grade": "B+",
                "badge_class": "bg-amber-600 text-white",
                "verdict": "Fair Repaired Player",
                "reason": "Headstock repair priced accordingly (-35% market value). Great player grade.",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
        return {
            "grade": "C",
            "badge_class": "bg-red-800 text-red-200",
            "verdict": "Caution (Overpriced Repair)",
            "reason": f"Repaired guitar landed at £{true_landed_cost:.0f}; above £1,450 safe threshold.",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }
    
    # Brand-specific evaluation
    if brand_tier in ["Gibson USA Standard", "Gibson Custom Shop"]:
        # Sub-£2,000 True Landed Cost is an instant Holy Grail Steal
        if true_landed_cost < 2000 or (true_landed_cost <= 2050 and era_boost >= 1.0):
            return {
                "grade": "A+",
                "badge_class": "bg-emerald-500 text-stone-950 font-black",
                "verdict": "Grade A+ (Holy Grail Steal)",
                "reason": f"Landed at £{true_landed_cost:.0f}. Rare sub-£2k threshold for authentic Gibson USA 335!",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
        elif true_landed_cost <= 2150:
            return {
                "grade": "A",
                "badge_class": "bg-teal-500 text-stone-950 font-bold",
                "verdict": "Grade A (Prime Target)",
                "reason": f"Landed at £{true_landed_cost:.0f}. Well under £2,200 average market floor.",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
        elif true_landed_cost <= 2350:
            return {
                "grade": "B+",
                "badge_class": "bg-blue-600 text-white",
                "verdict": "Grade B+ (Fair Market)",
                "reason": f"Landed at £{true_landed_cost:.0f}. Solid market price; worth an offer.",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
        elif true_landed_cost <= 2550:
            return {
                "grade": "B",
                "badge_class": "bg-stone-600 text-stone-200",
                "verdict": "Grade B (Negotiate Down)",
                "reason": "Room to negotiate £150-£250 off for travel offset.",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
        else:
            return {
                "grade": "C",
                "badge_class": "bg-stone-800 text-stone-400",
                "verdict": "Grade C (Overpriced)",
                "reason": f"Landed at £{true_landed_cost:.0f}. Higher than competitive private/used rates.",
                "true_landed_cost": true_landed_cost,
                "case_penalty": case_penalty
            }
            
    elif brand_tier == "Gibson USA Studio/Satin":
        if true_landed_cost <= 1400:
            grade = "A+"
        elif true_landed_cost <= 1600:
            grade = "A"
        elif true_landed_cost <= 1800:
            grade = "B"
        else:
            grade = "C"
        return {
            "grade": grade,
            "badge_class": "bg-amber-500 text-stone-950 font-bold",
            "verdict": f"Grade {grade} (Studio/Satin)",
            "reason": f"Landed at £{true_landed_cost:.0f} (fair Studio range: £1,400-£1,650).",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }
        
    elif brand_tier in ["Orville by Gibson", "Orville MIJ"]:
        if true_landed_cost <= 1250:
            grade = "A+"
        elif true_landed_cost <= 1450:
            grade = "A"
        elif true_landed_cost <= 1600:
            grade = "B"
        else:
            grade = "C"
        return {
            "grade": grade,
            "badge_class": "bg-purple-600 text-white font-bold",
            "verdict": f"Grade {grade} (Japanese Icon)",
            "reason": f"Landed at £{true_landed_cost:.0f}. FujiGen/Terada build quality.",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }
        
    elif brand_tier == "Heritage H-535":
        if true_landed_cost <= 1550:
            grade = "A+"
        elif true_landed_cost <= 1750:
            grade = "A"
        else:
            grade = "B"
        return {
            "grade": grade,
            "badge_class": "bg-amber-600 text-white font-bold",
            "verdict": f"Grade {grade} (Kalamazoo Craft)",
            "reason": f"Landed at £{true_landed_cost:.0f}. Built in former Gibson Parsons St plant.",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }
        
    elif brand_tier == "Tokai Japan":
        if true_landed_cost <= 1000:
            grade = "A+"
        elif true_landed_cost <= 1250:
            grade = "A"
        else:
            grade = "B"
        return {
            "grade": grade,
            "badge_class": "bg-indigo-600 text-white font-bold",
            "verdict": f"Grade {grade} (Tokai MIJ)",
            "reason": f"Landed at £{true_landed_cost:.0f}. Japanese ES build.",
            "true_landed_cost": true_landed_cost,
            "case_penalty": case_penalty
        }

    return {
        "grade": "B",
        "badge_class": "bg-stone-700 text-stone-300",
        "verdict": "Grade B (General ES)",
        "reason": f"Landed at £{true_landed_cost:.0f}.",
        "true_landed_cost": true_landed_cost,
        "case_penalty": case_penalty
    }

# ---------------------------------------------------------
# 4. DATABASE INITIALIZATION
# ---------------------------------------------------------
DB_FILE = os.path.join(os.path.dirname(__file__), "deals.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            title TEXT,
            price REAL,
            source TEXT,
            url TEXT,
            image_url TEXT,
            postcode TEXT,
            brand_tier TEXT,
            year INTEGER,
            era_badge TEXT,
            has_case INTEGER,
            has_repair INTEGER,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS listing_history (
            id TEXT PRIMARY KEY,
            title TEXT,
            first_seen TEXT,
            last_seen TEXT,
            initial_price REAL,
            last_price REAL,
            lowest_price REAL,
            previous_price REAL,
            price_dropped_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts_sent (
            alert_key TEXT PRIMARY KEY,
            listing_id TEXT,
            reason TEXT,
            sent_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def _parse_iso_dt(date_str):
    if not date_str:
        return None
    try:
        clean = str(date_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def track_and_annotate_listings(enriched_items):
    """Records prices & first-seen timestamps in deals.db and annotates price_drop + days_on_market."""
    if not enriched_items:
        return enriched_items
    init_db()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    for item in enriched_items:
        lid = str(item.get("id", ""))
        price = float(item.get("price", 0) or 0)
        published_dt = _parse_iso_dt(item.get("published_at") or item.get("created_at"))
        c.execute(
            "SELECT first_seen, initial_price, last_price, lowest_price, previous_price, price_dropped_at FROM listing_history WHERE id = ?",
            (lid,)
        )
        row = c.fetchone()

        if row is None:
            first_dt = published_dt or now
            first_iso = first_dt.isoformat()
            initial_price = price
            lowest_price = price
            previous_price = None
            dropped_at = None
            c.execute(
                """INSERT INTO listing_history
                   (id, title, first_seen, last_seen, initial_price, last_price, lowest_price, previous_price, price_dropped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lid, item.get("title", ""), first_iso, now_iso, initial_price, price, lowest_price, previous_price, dropped_at)
            )
        else:
            first_iso, initial_price, last_price, lowest_price, previous_price, dropped_at = row
            first_dt = _parse_iso_dt(first_iso) or now
            # If we later get an earlier real published_at timestamp from Reverb/eBay, use the earlier date
            if published_dt and published_dt < first_dt:
                first_dt = published_dt
                first_iso = first_dt.isoformat()

            if price < (last_price or price):
                previous_price = last_price
                dropped_at = now_iso
            if lowest_price is None or price < lowest_price:
                lowest_price = price
            if initial_price is None:
                initial_price = price

            c.execute(
                """UPDATE listing_history
                   SET title = ?, first_seen = ?, last_seen = ?, initial_price = ?, last_price = ?, lowest_price = ?, previous_price = ?, price_dropped_at = ?
                   WHERE id = ?""",
                (item.get("title", ""), first_iso, now_iso, initial_price, price, lowest_price, previous_price, dropped_at, lid)
            )

        days_on_market = max(0, (now - first_dt).days)
        price_drop = round(initial_price - price, 2) if (initial_price and price < initial_price - 0.5) else 0.0

        item["first_seen"] = first_iso
        item["days_on_market"] = days_on_market
        item["is_new_today"] = (days_on_market <= 1)
        item["initial_price"] = round(initial_price, 2)
        item["price_drop"] = price_drop
        item["previous_price"] = round(previous_price, 2) if previous_price else None

    conn.commit()
    conn.close()
    return enriched_items

def send_deal_alert_email(alerts, subject=None):
    """Sends a clean HTML email alert via Gmail SMTP SSL for Grade A+ steals & price drops."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    cfg = load_config().get("email_alerts", {})
    if not cfg.get("enabled"):
        return False, "Email alerts disabled in config.json"

    from_email = cfg.get("from_email", "").strip()
    to_email = cfg.get("to_email", "").strip()
    app_password = cfg.get("app_password", "").replace(" ", "").strip()
    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 465))

    if not from_email or not to_email or not app_password or "YOUR_GMAIL" in app_password:
        return False, "Gmail App Password not configured yet in config.json"

    if not subject:
        if len(alerts) == 1:
            a = alerts[0]
            subject = f"🎸 {a['tag']}: {a['item']['title']} (£{a['item']['price']:.0f})"
        else:
            subject = f"🎸 Gibson ES-335 Radar: {len(alerts)} New Alert(s)!"

    rows_html = ""
    for a in alerts:
        it = a["item"]
        hull = it.get("hubs", {}).get("Hull", {})
        travel = hull.get("travel", {})
        ev = hull.get("evaluation", {})
        ship_text = it.get("shipping_carrier", "Collection Only")
        drop_badge = f"<span style='color:#10b981;font-weight:700;'> ↓ Dropped £{it.get('price_drop', 0):.0f}</span>" if it.get("price_drop", 0) > 0 else ""
        rows_html += f"""
        <div style="background:#13100E;border:1px solid #2A221D;border-radius:10px;padding:16px;margin-bottom:14px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#E59A28;margin-bottom:6px;">
            {a['tag']} &bull; {it.get('brand_tier', '')} &bull; {it.get('source', '')}
          </div>
          <div style="font-size:16px;font-weight:700;color:#F5EFE6;margin-bottom:8px;">
            {it.get('title', '')}
          </div>
          <div style="font-size:13px;color:#A69A8E;margin-bottom:12px;line-height:1.5;">
            Asking: <strong style="color:#F5EFE6;">£{it.get('price', 0):,.0f}</strong>{drop_badge}<br>
            Hull Travel: <strong style="color:#F5EFE6;">{travel.get('one_way_miles', 0)} mi ({travel.get('drive_hours', 0)}h)</strong> &bull; Petrol: £{travel.get('fuel_cost', 0):.0f}<br>
            Delivery: <strong style="color:#F5EFE6;">{ship_text}</strong><br>
            True Landed Cost: <strong style="color:#E59A28;">£{ev.get('true_landed_cost', it.get('price', 0)):,.0f}</strong>
          </div>
          <a href="{it.get('url', '#')}" style="display:inline-block;background:#E59A28;color:#0B0908;text-decoration:none;font-weight:700;font-size:12px;padding:9px 16px;border-radius:6px;">
            View Live Listing &rarr;
          </a>
        </div>
        """

    html_body = f"""
    <html>
      <body style="background:#0B0908;color:#F5EFE6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;margin:0;">
        <div style="max-width:600px;margin:0 auto;">
          <h2 style="margin:0 0 6px 0;color:#F5EFE6;font-size:20px;">Gibson ES-335 UK Deal Radar</h2>
          <p style="margin:0 0 20px 0;color:#A69A8E;font-size:13px;">Live alert triggered by your automated UK scanner.</p>
          {rows_html}
          <p style="font-size:11px;color:#6E655D;margin-top:20px;">
            Automated alert from your local Gibson ES-335 Deal Radar. Duplicate alerts are automatically suppressed.
          </p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Gibson ES-335 Radar <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
            server.login(from_email, app_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        print(f"📧 Alert email sent to {to_email}: {subject}")
        return True, "Sent successfully"
    except Exception as e:
        print(f"✗ Email alert error: {e}")
        return False, str(e)

def check_and_send_alerts(enriched_items):
    """Checks for new Grade A+ steals or significant price drops and emails once per event."""
    cfg = load_config().get("email_alerts", {})
    if not cfg.get("enabled") or not cfg.get("app_password") or "YOUR_GMAIL" in cfg.get("app_password", ""):
        return

    min_drop = float(cfg.get("min_price_drop", 50))
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    pending_alerts = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for it in enriched_items:
        lid = str(it.get("id", ""))
        hull_grade = it.get("hubs", {}).get("Hull", {}).get("evaluation", {}).get("grade", "")
        som_grade = it.get("hubs", {}).get("Somerset", {}).get("evaluation", {}).get("grade", "")
        price_drop = float(it.get("price_drop", 0) or 0)
        price = float(it.get("price", 0) or 0)

        alert_key = None
        tag = None

        if price_drop >= min_drop:
            alert_key = f"drop_{lid}_{int(price)}"
            tag = f"PRICE DROP (−£{int(round(price_drop))})"
        elif hull_grade == "A+" or som_grade == "A+":
            alert_key = f"aplus_{lid}"
            tag = "GRADE A+ STEAL"

        if alert_key:
            c.execute("SELECT 1 FROM alerts_sent WHERE alert_key = ?", (alert_key,))
            if not c.fetchone():
                pending_alerts.append({"key": alert_key, "tag": tag, "item": it})

    if pending_alerts:
        ok, _ = send_deal_alert_email(pending_alerts[:10])
        if ok:
            for a in pending_alerts:
                c.execute(
                    "INSERT OR IGNORE INTO alerts_sent (alert_key, listing_id, reason, sent_at) VALUES (?, ?, ?, ?)",
                    (a["key"], str(a["item"].get("id", "")), a["tag"], now_iso)
                )
            conn.commit()
    conn.close()

# ---------------------------------------------------------
# 5. SHOPIFY HARVESTER WITH GHOST BUSTER
# ---------------------------------------------------------
def harvest_shopify_dealers():
    """Scrapes watched Shopify dealers via /products.json with SEO ghost filter."""
    print("🔍 Harvesting live Shopify guitar dealers...")
    discovered = []
    
    for dealer in WATCHED_SHOPIFY_DEALERS:
        store_url = dealer["url"]
        dealer_name = dealer["name"]
        dealer_pc = dealer["postcode"]
        
        try:
            feed_url = f"{store_url}/products.json?limit=50"
            req = urllib.request.Request(
                feed_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) GibsonDealScanner/1.0'}
            )
            with urllib.request.urlopen(req, timeout=6) as res:
                data = json.loads(res.read().decode('utf-8'))
                
            for product in data.get('products', []):
                title = product.get('title', '')
                title_lower = title.lower()
                body_html = product.get('body_html', '') or ''
                desc_lower = body_html.lower()
                
                # Filter: ES-335 or 335 keywords, reject acoustics/pedals/Epiphone
                if not ("335" in title_lower or "es-335" in title_lower):
                    continue
                if "epiphone" in title_lower and "elitist" not in title_lower:
                    continue
                    
                # SEO Ghost Buster: Check variant availability
                variants = product.get('variants', [])
                if not variants:
                    continue
                first_variant = variants[0]
                is_available = first_variant.get('available', False)
                if not is_available:
                    # Skip ghost out-of-stock listings
                    continue
                
                # Check for "sold" in title or description
                if any(w in title_lower for w in ["*sold*", "[sold]", "sold out"]):
                    continue
                    
                price = float(first_variant.get('price', 0))
                handle = product.get('handle', '')
                prod_url = f"{store_url}/products/{handle}"
                search_url = f"{store_url}/search?type=product&q={urllib.parse.quote(title)}"
                
                images = product.get('images', [])
                image_url = images[0].get('src', '') if images else ''
                
                brand = detect_brand_tier(title, desc_lower)
                era = detect_era(f"{title} {desc_lower}")
                flags = detect_repair_and_case(title, desc_lower)
                
                item = {
                    "id": f"{dealer_name.replace(' ', '_')}_{product.get('id')}",
                    "title": title,
                    "price": price,
                    "source": dealer_name,
                    "url": prod_url,
                    "search_url": search_url,
                    "image_url": image_url,
                    "postcode": dealer_pc,
                    "brand_tier": brand,
                    "year": era["year"],
                    "era_badge": era["badge"],
                    "era_boost": era.get("boost", 0.0),
                    "era_notes": era.get("notes", ""),
                    "has_case": flags["has_case"],
                    "has_repair": flags["has_repair"]
                }
                discovered.append(item)
                print(f"  ✓ Found [{brand}]: {title} - £{price}")
                
        except Exception as e:
            print(f"  ✗ Error checking {dealer_name}: {e}")
            
    return discovered

# ---------------------------------------------------------
# 6. SEED / REFERENCE DATA GENERATOR
# ---------------------------------------------------------
def generate_sample_listings():
    """Generates a realistic set of UK listings across hubs with active, working search URLs."""
    return [
        {
            "id": "peach_1995_dot",
            "title": "Gibson ES-335 Dot Reissue 1995 Sunburst (Good Wood Era)",
            "price": 1950.0,
            "source": "Peach Guitars",
            "url": "https://www.peachguitars.com/guitars/pre-owned-guitars/?search=335",
            "search_url": "https://www.peachguitars.com/guitars/pre-owned-guitars/?search=335",
            "image_url": "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600&auto=format&fit=crop",
            "postcode": "CO4 9QP",  # Colchester
            "brand_tier": "Gibson USA Standard",
            "year": 1995,
            "era_badge": "⭐ GOOD WOOD (90s)",
            "era_boost": 1.0,
            "era_notes": "Premium Honduran mahogany body, dark rosewood board, early '57 Classic PAFs.",
            "has_case": True,
            "has_repair": False
        },
        {
            "id": "coda_2016_memphis",
            "title": "Gibson Memphis ES-335 2016 Figured Cherry",
            "price": 2095.0,
            "source": "Coda Music",
            "url": "https://www.coda-music.com/catalogsearch/result/?q=gibson+335",
            "search_url": "https://www.coda-music.com/catalogsearch/result/?q=gibson+335",
            "image_url": "https://images.unsplash.com/photo-1564186763535-ebb21ef5277f?w=600&auto=format&fit=crop",
            "postcode": "SG6 2AL",  # Hertfordshire
            "brand_tier": "Gibson USA Standard",
            "year": 2016,
            "era_badge": "🎖️ MEMPHIS PEAK (13-18)",
            "era_boost": 0.5,
            "era_notes": "Adirondack spruce quartered bracing, MHS unpotted PAFs, rolled neck binding.",
            "has_case": True,
            "has_repair": False
        },
        {
            "id": "jordan_2022_original",
            "title": "Gibson ES-335 Original Collection 2022 Vintage Burst",
            "price": 2199.0,
            "source": "Jordan Guitars",
            "url": "https://jordanguitars.co.uk/search?type=product&q=335",
            "search_url": "https://jordanguitars.co.uk/search?type=product&q=335",
            "image_url": "https://images.unsplash.com/photo-1525201548942-d8732f6617a0?w=600&auto=format&fit=crop",
            "postcode": "NR1 1AA",  # Norwich
            "brand_tier": "Gibson USA Standard",
            "year": 2022,
            "era_badge": "🛡️ MODERN NASHVILLE",
            "era_boost": 0.0,
            "era_notes": "Calibrated T-Type humbuckers, hand-wired harness with Orange Drop caps.",
            "has_case": True,
            "has_repair": False
        },
        {
            "id": "private_obg_1993",
            "title": "Orville by Gibson ES-335 Dot 1993 Terada MIJ (Nitro & '57 Classics)",
            "price": 1200.0,
            "source": "Reverb UK Private",
            "url": "https://reverb.com/uk/marketplace?query=orville%20by%20gibson%20335",
            "search_url": "https://reverb.com/uk/marketplace?query=orville%20by%20gibson%20335",
            "image_url": "https://images.unsplash.com/photo-1516924962500-2b4b3b99ea02?w=600&auto=format&fit=crop",
            "postcode": "LS1 1AA",  # Leeds (very close to Hull!)
            "brand_tier": "Orville by Gibson",
            "year": 1993,
            "era_badge": "⭐ GOOD WOOD (90s)",
            "era_boost": 1.0,
            "era_notes": "Original nitrocellulose finish, fret-edge binding, Gibson USA pickups from factory.",
            "has_case": True,
            "has_repair": False
        },
        {
            "id": "private_heritage_535",
            "title": "Heritage H-535 Semi-Hollow 2018 Kalamazoo Sunburst",
            "price": 1495.0,
            "source": "Gumtree Bristol",
            "url": "https://www.gumtree.com/search?search_category=guitar&q=heritage+535",
            "search_url": "https://www.gumtree.com/search?search_category=guitar&q=heritage+535",
            "image_url": "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600&auto=format&fit=crop",
            "postcode": "BS1 1AA",  # Bristol (40 min from Somerset hub!)
            "brand_tier": "Heritage H-535",
            "year": 2018,
            "era_badge": "📅 2018",
            "era_boost": 0.0,
            "era_notes": "Seymour Duncan '59 set, Michigan curly maple, built in historic Parsons St factory.",
            "has_case": True,
            "has_repair": False
        },
        {
            "id": "inbloom_2011_player",
            "title": "Gibson ES-335 Dot 2011 Cherry Red (Headstock Smile Repair)",
            "price": 1450.0,
            "source": "In Bloom Guitars",
            "url": "https://inbloomguitars.co.uk/search?q=335",
            "search_url": "https://inbloomguitars.co.uk/search?q=335",
            "image_url": "https://images.unsplash.com/photo-1564186763535-ebb21ef5277f?w=600&auto=format&fit=crop",
            "postcode": "RG1 1DN",  # Reading
            "brand_tier": "Gibson USA Standard",
            "year": 2011,
            "era_badge": "📅 2011",
            "era_boost": 0.0,
            "era_notes": "Professional luthier cleat & refinish. Plays cleanly with rock solid stability.",
            "has_case": True,
            "has_repair": True
        },
        {
            "id": "tokai_es160_2017",
            "title": "Tokai Japan ES-160 / ES-180 Vintage Natural Flame",
            "price": 1050.0,
            "source": "Guitar Village",
            "url": "https://guitarvillage.co.uk/?s=tokai+335&post_type=product",
            "search_url": "https://guitarvillage.co.uk/?s=tokai+335&post_type=product",
            "image_url": "https://images.unsplash.com/photo-1525201548942-d8732f6617a0?w=600&auto=format&fit=crop",
            "postcode": "GU9 7ND",  # Farnham
            "brand_tier": "Tokai Japan",
            "year": 2017,
            "era_badge": "📅 2017",
            "era_boost": 0.0,
            "era_notes": "PAF-Vintage MK2 pickups, brass saddles, bone nut, lacquer finish.",
            "has_case": False,  # Needs case -> trigger +£150 rule
            "has_repair": False
        }
    ]

# ---------------------------------------------------------
# 7. ENRICHMENT & SCORING PIPELINE
# ---------------------------------------------------------
def is_valid_335_model(title, brand=""):
    """Strictly filters out Epiphones and non-335 models (e.g. Tokai Love Rock/Goldstar/LS/LC)."""
    tlow = (title or "").lower()
    blow = (brand or "").lower()
    if blow == "epiphone (exclude)" or ("epiphone" in tlow and "elitist" not in tlow):
        return False

    # Strict Tokai 335 semi-hollow gate: must be ES-series or 335, never Les Paul/Strat copies
    if "tokai" in tlow or "tokai" in blow:
        non_335_tokai = [
            "love rock", "goldstar", "breezysound", "silver star", "springy sound",
            "talbo", "hard puncher", "jazz sound", "reborn", "ate-", "ast-"
        ]
        if any(bad in tlow for bad in non_335_tokai):
            return False
        if re.search(r'\b(u?ls|lc|sg|lp|st|te)[\s-]?\d{2,3}', tlow):
            return False
        if not (re.search(r'\bes[\s-]?\d{2,3}', tlow) or "335" in tlow or "semi" in tlow):
            return False

    return True

def enrich_listings(listings, car_mpg=38.0, fuel_price=1.42):
    """Calculates distances, fuel costs, and deal grades for both Hull and Somerset hubs."""
    enriched = []
    
    for item in listings:
        # Strictly exclude Epiphones & non-335 Tokai models
        brand = item.get("brand_tier", "")
        if not is_valid_335_model(item.get("title", ""), brand):
            continue

        pc = item.get("postcode", "")
        coords = get_postcode_coords(pc)
        
        # Hull Hub Metrics
        hull_travel = calculate_travel_metrics(coords, "Hull", car_mpg, fuel_price)
        hull_eval = evaluate_deal(
            price=item["price"],
            brand_tier=item["brand_tier"],
            era_boost=item.get("era_boost", 0.0),
            has_repair=item.get("has_repair", False),
            has_case=item.get("has_case", True),
            drive_hours=hull_travel["drive_hours"],
            max_hours=3.0,
            fuel_cost=hull_travel["fuel_cost"]
        )
        
        # Somerset Hub Metrics
        somerset_travel = calculate_travel_metrics(coords, "Somerset", car_mpg, fuel_price)
        somerset_eval = evaluate_deal(
            price=item["price"],
            brand_tier=item["brand_tier"],
            era_boost=item.get("era_boost", 0.0),
            has_repair=item.get("has_repair", False),
            has_case=item.get("has_case", True),
            drive_hours=somerset_travel["drive_hours"],
            max_hours=1.5,
            fuel_cost=somerset_travel["fuel_cost"]
        )
        
        full_item = {
            **item,
            "coords": coords,
            "hubs": {
                "Hull": {
                    "travel": hull_travel,
                    "evaluation": hull_eval
                },
                "Somerset": {
                    "travel": somerset_travel,
                    "evaluation": somerset_eval
                }
            }
        }
        enriched.append(full_item)
        
    return track_and_annotate_listings(enriched)

# ---------------------------------------------------------
# 8. LOCAL WEB SERVER & RUNNER
# ---------------------------------------------------------
def export_deals_json(data, filename="deals.json"):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"📁 Exported {len(data)} deals to {filename}")

def scrape_and_enrich_single_fb(url, user_location="Hull"):
    """Scrapes a public Facebook Marketplace listing URL headlessly without login and enriches it."""
    from bs4 import BeautifulSoup
    from playwright.sync_api import sync_playwright

    clean_url = url.split('?')[0]
    match_id = re.search(r'/marketplace/item/(\d+)', clean_url)
    item_id = match_id.group(1) if match_id else str(int(time.time()))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(clean_url, wait_until="domcontentloaded", timeout=25000)
            final_url = page.url
            if any(term in final_url for term in ["two_step_verification", "checkpoint", "login"]):
                print("Facebook redirected to login/2FA checkpoint.")
                browser.close()
                return None

            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, 'html.parser')
        title_el = soup.find('h1')
        title = title_el.get_text(strip=True) if title_el else "Gibson ES-335 (Facebook Listing)"

        price = 0.0
        text = soup.get_text()
        matches = re.findall(r'[£$€]([\d,]+)', text)
        for m in matches:
            v = float(m.replace(',', ''))
            if v > 150:
                price = v
                break
        if price == 0.0:
            price = 1950.0

        images = [img.get('src') for img in soup.find_all('img') if img.get('src') and 'fbcdn.net' in img.get('src')]
        image_url = images[0] if images else "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600"

        # Determine postcode
        pc = "HU1 1AA"
        loc_lower = user_location.lower()
        city_lookup = {
            "hull": "HU1 1AA", "beverley": "HU17 8DB", "york": "YO1 7HH", "leeds": "LS1 1AA",
            "sheffield": "S1 2GE", "grimsby": "DN31 1AA", "scunthorpe": "DN15 6AA",
            "bristol": "BS1 1AA", "bath": "BA1 1AA", "burnham": "TA8 1PE", "cardiff": "CF10 1AA",
            "london": "SW1A 1AA", "manchester": "M1 1AE", "birmingham": "B1 1AA"
        }
        for k, v in city_lookup.items():
            if k in loc_lower:
                pc = v
                break

        brand = detect_brand_tier(title)
        era = detect_era(title)
        flags = detect_repair_and_case(title)
        is_lefty = detect_dexterity(title)
        ship_info = detect_shipping_info(f"Facebook ({user_location})", title, price)

        raw_item = {
            "id": f"fb_{item_id}",
            "title": title,
            "price": price,
            "source": f"Facebook ({user_location.title()})",
            "url": clean_url,
            "image_url": image_url,
            "postcode": pc,
            "brand_tier": brand,
            "year": era["year"],
            "era_badge": era["badge"],
            "era_boost": era.get("boost", 0.0),
            "era_notes": era.get("notes", ""),
            "has_case": flags["has_case"],
            "has_repair": flags["has_repair"],
            "is_left_handed": is_lefty,
            "shipping_available": ship_info["shipping_available"],
            "shipping_cost": ship_info["shipping_cost"],
            "shipping_carrier": ship_info["shipping_carrier"]
        }

        enriched = enrich_listings([raw_item])
        return enriched[0] if enriched else None
    except Exception as e:
        print(f"Error importing FB item {url}: {e}")
        return None

def parse_gumtree_single(url, user_location="London"):
    """Scrapes a public Gumtree guitar listing and enriches it with travel & deal grading."""
    import requests
    from bs4 import BeautifulSoup
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')

        title = "Gibson ES-335"
        price = 1800.0
        location = user_location or "London"
        img_url = ""
        desc_text = ""

        # 1. Parse JSON-LD Schema (100% structured schema.org/Product)
        ld_script = soup.find('script', type='application/ld+json')
        ld_data = {}
        if ld_script:
            try:
                ld_data = json.loads(ld_script.string or ld_script.get_text())
            except Exception:
                pass

        if ld_data and ld_data.get('@type') == 'Product':
            title = ld_data.get('name') or title
            desc_text = ld_data.get('description', '')
            offers = ld_data.get('offers', {})
            if isinstance(offers, dict):
                p_val = offers.get('price')
                if p_val:
                    try:
                        price = float(p_val)
                    except (ValueError, TypeError):
                        pass
                location = offers.get('availableAtOrFrom') or location
            images = ld_data.get('image', [])
            if images and isinstance(images, list):
                img_url = images[0]
        else:
            og_title = soup.find('meta', property='og:title')
            title_raw = og_title.get('content', '') if og_title else ''
            parts = title_raw.split('|')
            title = parts[0].strip() if parts else "Gibson ES-335"
            # Strip trailing price text like ", £1,800.00 for Sale"
            title = re.sub(r',\s*£[\d,]+(?:\.\d+)?\s*for\s*sale.*$', '', title, flags=re.I).strip()

            og_img = soup.find('meta', property='og:image')
            img_url = og_img.get('content', '') if og_img else ''

            text = soup.get_text()
            p_match = re.search(r'£\s*([\d,]+)', text)
            if p_match:
                price = float(p_match.group(1).replace(',', ''))

            og_desc = soup.find('meta', property='og:description')
            if og_desc and "in " in og_desc.get('content', ''):
                desc_content = og_desc.get('content', '')
                loc_match = re.search(r'in\s+([A-Za-z\s,]+?)(?:\.|$)', desc_content)
                if loc_match:
                    location = loc_match.group(1).strip()

        match_id = re.search(r'/(\d{7,12})', url)
        item_id = match_id.group(1) if match_id else str(int(time.time()))

        pc = "SW1A 1AA" # Default London
        city_lookup = {
            "hull": "HU1 1AA", "beverley": "HU17 8DB", "york": "YO1 7HH", "leeds": "LS1 1AA",
            "sheffield": "S1 2GE", "grimsby": "DN31 1AA", "scunthorpe": "DN15 6AA",
            "liverpool": "L1 8JQ", "manchester": "M1 1AE", "bristol": "BS1 1AA",
            "bath": "BA1 1AA", "cardiff": "CF10 1AA", "london": "SW1A 1AA", "norwood": "SW1A 1AA",
            "birmingham": "B1 1AA", "norwich": "NR1 1AA", "colchester": "CO4 9QP"
        }
        for k, v in city_lookup.items():
            if k in location.lower():
                pc = v
                break

        brand = detect_brand_tier(title, desc_text)
        era = detect_era(f"{title} {desc_text}")
        flags = detect_repair_and_case(f"{title} {desc_text}")
        is_lefty = detect_dexterity(title, desc_text)

        # Check delivery vs collection in text / description
        combined_text = f"{title} {desc_text}".lower()
        if any(term in combined_text for term in ["free delivery", "free postage"]):
            shipping_available = True
            shipping_cost = 0.0
            shipping_carrier = "Seller Free UK Delivery"
        elif any(term in combined_text for term in ["delivery available", "can post", "courier available"]):
            shipping_available = True
            shipping_cost = 35.0
            shipping_carrier = "Seller Delivery: £35.00"
        else:
            shipping_available = False
            shipping_cost = 0.0
            shipping_carrier = "Collection in Person Only"

        raw_item = {
            "id": f"gumtree_{item_id}",
            "title": title,
            "price": price,
            "source": f"Gumtree ({location})",
            "url": url,
            "image_url": img_url,
            "postcode": pc,
            "brand_tier": brand,
            "year": era["year"],
            "era_badge": era["badge"],
            "era_boost": era.get("boost", 0.0),
            "era_notes": era.get("notes", ""),
            "has_case": flags["has_case"],
            "has_repair": flags["has_repair"],
            "is_left_handed": is_lefty,
            "shipping_available": shipping_available,
            "shipping_cost": shipping_cost,
            "shipping_carrier": shipping_carrier
        }

        enriched = enrich_listings([raw_item])
        return enriched[0] if enriched else None
    except Exception as e:
        print(f"Error parsing Gumtree item {url}: {e}")
        return None

def parse_reverb_single(url):
    """Parses a single Reverb listing URL, fetches data via Reverb API, and returns an enriched item."""
    m = re.search(r'/item/(\d+)', url)
    if not m:
        return None
    item_id = m.group(1)
    api_url = f"https://api.reverb.com/api/listings/{item_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Version': '3.0',
        'X-Display-Currency': 'GBP'
    }
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            it = json.loads(resp.read().decode('utf-8'))

        title = it.get("title", "")
        price_data = it.get("buyer_price") or it.get("price") or {}
        try:
            raw_price = round(float(price_data.get("amount", 0)), 2)
        except (ValueError, TypeError):
            raw_price = 0.0

        vat_price = round(raw_price * 1.2, 2)
        if abs(vat_price - round(vat_price)) < 0.05 and raw_price != round(raw_price) and raw_price > 1000:
            price = float(round(vat_price))
        else:
            price = raw_price

        web_url = it.get("_links", {}).get("web", {}).get("href", "") or url
        photos = it.get("photos", [])
        image_url = photos[0].get("_links", {}).get("large_crop", {}).get("href", "") if photos else ""
        shop_name = it.get("shop_name") or "Reverb UK Seller"

        loc_data = it.get("location", {}) or {}
        locality = loc_data.get("locality") or loc_data.get("display_location") or ""
        postcode = resolve_uk_location_postcode(locality, shop_name)

        desc_text = it.get("description", "")
        brand = detect_brand_tier(title, desc_text)
        if brand == "Epiphone (Exclude)" or ("epiphone" in f"{title} {desc_text}".lower() and "elitist" not in f"{title} {desc_text}".lower()):
            print(f"Skipping Epiphone listing: {title}")
            return None

        era = detect_era(f"{title} {desc_text}")
        flags = detect_repair_and_case(f"{title} {desc_text}")
        is_lefty = detect_dexterity(title, desc_text)

        shipping_obj = it.get("shipping", {}) or {}
        rates = shipping_obj.get("rates", []) or []
        gb_rate = next((r for r in rates if r.get("region_code") == "GB"), None)
        if not gb_rate:
            ior = shipping_obj.get("initial_offer_rate", {}) or {}
            if ior.get("region_code") == "GB":
                gb_rate = ior

        shipping_available = False
        shipping_cost = 0.0
        shipping_carrier = "Collection in Person Only"

        if gb_rate and "rate" in gb_rate:
            shipping_available = True
            rate_info = gb_rate["rate"]
            amt_str = rate_info.get("amount")
            if amt_str is None and isinstance(rate_info.get("original"), dict):
                amt_str = rate_info["original"].get("amount")
            try:
                shipping_cost = round(float(amt_str), 2) if amt_str is not None else 0.0
            except (ValueError, TypeError):
                shipping_cost = 0.0

            if shipping_cost == 0.0:
                shipping_carrier = "Seller Free UK Delivery"
            else:
                shipping_carrier = f"Seller UK Delivery: £{shipping_cost:.2f}"

        raw_item = {
            "id": f"reverb_{item_id}",
            "title": title,
            "price": price,
            "source": f"{shop_name} ({locality})" if locality else shop_name,
            "url": web_url,
            "image_url": image_url,
            "postcode": postcode,
            "brand_tier": brand,
            "year": era["year"],
            "era_badge": era["badge"],
            "era_boost": era.get("boost", 0.0),
            "era_notes": era.get("notes", ""),
            "has_case": flags["has_case"],
            "has_repair": flags["has_repair"],
            "is_left_handed": is_lefty,
            "shipping_available": shipping_available,
            "shipping_cost": shipping_cost,
            "shipping_carrier": shipping_carrier,
            "published_at": it.get("published_at") or it.get("created_at")
        }

        enriched = enrich_listings([raw_item])
        return enriched[0] if enriched else None
    except Exception as e:
        print(f"Error parsing single Reverb listing {url}: {e}")
        return None

class DealRadarServer(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
        
    def do_GET(self):
        try:
            if self.path.startswith("/api/import_fb") or self.path.startswith("/api/import_deal"):
                parsed_url = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed_url.query)
                target_url = qs.get("url", [""])[0]
                loc = qs.get("location", [""])[0]

                if target_url:
                    if "reverb.com" in target_url:
                        new_item = parse_reverb_single(target_url)
                    elif "gumtree.com" in target_url:
                        new_item = parse_gumtree_single(target_url, loc or "Liverpool")
                    else:
                        new_item = scrape_and_enrich_single_fb(target_url, loc or "Hull")

                    if new_item:
                        filepath = os.path.join(os.path.dirname(__file__), "deals.json")
                        deals = []
                        if os.path.exists(filepath):
                            with open(filepath, "r", encoding="utf-8-sig") as f:
                                deals = json.load(f)
                        deals.insert(0, new_item)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(deals, f, indent=2)

                        res_body = json.dumps({"status": "ok", "item": new_item}).encode('utf-8')
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(res_body)))
                        self.end_headers()
                        self.wfile.write(res_body)
                        return
                    else:
                        msg = "Facebook security 2FA checkpoint blocked automated parsing. Please view listing directly on Facebook." if "facebook.com" in target_url else "Could not fetch Gumtree listing."
                        res_body = json.dumps({"status": "error", "message": msg}).encode('utf-8')
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(res_body)))
                        self.end_headers()
                        self.wfile.write(res_body)
                        return

                res_body = json.dumps({"status": "error", "message": "No URL provided"}).encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(res_body)))
                self.end_headers()
                self.wfile.write(res_body)
                return

            if self.path.startswith("/api/scan_now"):
                def run_sweep():
                    try:
                        print("🔍 [Manual Scan] Initiating live UK Reverb + eBay scan...")
                        live_deals = harvest_all_sources()
                        enriched = enrich_listings(live_deals)
                        filepath = os.path.join(os.path.dirname(__file__), "deals.json")
                        saved_imports = []
                        if os.path.exists(filepath):
                            with open(filepath, "r", encoding="utf-8-sig") as f:
                                prev = json.load(f)
                                seen_ids = {d.get("id") for d in enriched}
                                saved_imports = [d for d in prev if (d.get("id", "").startswith("gumtree_") or d.get("id", "").startswith("fb_")) and d.get("id") not in seen_ids]
                        combined = saved_imports + enriched
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(combined, f, indent=2)
                        check_and_send_alerts(combined)
                        print(f"✓ [Manual Scan] Deals feed updated with {len(combined)} active guitars!")
                    except Exception as ex:
                        print(f"✗ [Manual Scan] Error: {ex}")

                t = threading.Thread(target=run_sweep, daemon=True)
                t.start()
                res_body = json.dumps({"status": "ok", "message": "Background scan started"}).encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(res_body)))
                self.end_headers()
                self.wfile.write(res_body)
                return

            if self.path.startswith("/api/deals") or self.path == "/deals.json":
                filepath = os.path.join(os.path.dirname(__file__), "deals.json")
                if os.path.exists(filepath):
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
        except Exception as e:
            err_body = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
            return

        super().do_GET()

def background_auto_scanner(interval_minutes=30):
    """Background thread that automatically sweeps Reverb & eBay periodically."""
    while True:
        time.sleep(interval_minutes * 60)
        try:
            print(f"\n⏰ [Auto-Scanner] Running {interval_minutes}-minute scheduled live deal sweep...")
            live_deals = harvest_all_sources()
            enriched = enrich_listings(live_deals)
            filepath = os.path.join(os.path.dirname(__file__), "deals.json")
            saved_imports = []
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    prev = json.load(f)
                    seen_ids = {d.get("id") for d in enriched}
                    saved_imports = [d for d in prev if (d.get("id", "").startswith("gumtree_") or d.get("id", "").startswith("fb_")) and d.get("id") not in seen_ids]
            combined = saved_imports + enriched
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(combined, f, indent=2)
            check_and_send_alerts(combined)
            print(f"✓ [Auto-Scanner] Deals feed refreshed ({len(combined)} listings active).\n")
        except Exception as e:
            print(f"✗ [Auto-Scanner] Error during background sweep: {e}")

def start_server(port=8000):
    os.chdir(os.path.dirname(__file__))
    # Start auto-scanner in background thread (runs every 30 minutes)
    scanner_thread = threading.Thread(target=background_auto_scanner, args=(30,), daemon=True)
    scanner_thread.start()

    # Bind to '' with multi-threaded handler so requests never block
    try:
        server = ThreadingHTTPServer(('', port), DealRadarServer)
    except Exception:
        server = HTTPServer(('', port), DealRadarServer)
    print(f"\n============================================================")
    print(f"🚀 Gibson ES-335 Deal Radar is LIVE!")
    print(f"👉 Open in your browser: http://localhost:{port}")
    print(f"   (or http://127.0.0.1:{port})")
    print(f"⏰ Auto-scan interval: Every 30 minutes")
    print(f"============================================================")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")

UK_SHOP_POSTCODES = {
    "wildwire": "YO8 8LZ",   # Selby, North Yorkshire (35 miles from Hull HQ!)
    "rich tone": "S9 3RP",   # Sheffield (60 miles from Hull HQ!)
    "coda music": "SG6 2AL", # Hertfordshire
    "peach": "CO4 9QP",      # Colchester
    "guitar village": "GU9 7ND", # Farnham
    "andertons": "GU1 4RF",  # Guildford
    "atb guitars": "GL50 1TA", # Cheltenham (near Somerset!)
    "wunjo": "WC2H 8LA",     # London
    "soundaffects": "PR7 1NY", # Ormskirk, Lancs
    "guitarguitar": "B5 4RB" # Birmingham
}

def harvest_live_reverb():
    """Fetches 100% REAL, LIVE, active UK Gibson ES-335 listings directly via UK live feed."""
    print("🔍 Harvesting live UK listings via Reverb UK Live Feed...")
    queries = ["gibson es-335", "orville 335", "heritage h-535", "tokai 335"]
    harvested = []
    seen_ids = set()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Version': '3.0',
        'X-Display-Currency': 'GBP'
    }

    for q in queries:
        try:
            for page in range(1, 4):
                url = f"https://api.reverb.com/api/listings?query={urllib.parse.quote(q)}&item_region=GB&price_min=650&currency=GBP&per_page=50&page={page}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    listings = data.get("listings", [])
                    if not listings:
                        break
                    for it in listings:
                        item_id = str(it.get("id"))
                        if item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)

                        title = it.get("title", "")
                        title_lower = title.lower()
                        if any(bad in title_lower for bad in ["case only", "pickguard", "wiring", "pickups only", "strap", "knobs", "epiphone"]):
                            if "elitist" not in title_lower:
                                continue

                        price_data = it.get("buyer_price") or it.get("price") or {}
                        try:
                            raw_price = round(float(price_data.get("amount", 0)), 2)
                        except (ValueError, TypeError):
                            continue

                        if raw_price < 650:
                            continue

                        # UK VAT adjustment for business dealer prices:
                        # Reverb API returns net ex-VAT prices for UK registered shops (e.g. 1999.17 -> 2399.00 inc 20% VAT)
                        vat_price = round(raw_price * 1.2, 2)
                        if abs(vat_price - round(vat_price)) < 0.05 and raw_price != round(raw_price) and raw_price > 1000:
                            price = float(round(vat_price))
                        else:
                            price = raw_price

                        web_url = it.get("_links", {}).get("web", {}).get("href", "")
                        photos = it.get("photos", [])
                        image_url = photos[0].get("_links", {}).get("large_crop", {}).get("href", "") if photos else ""
                        shop_name = it.get("shop_name") or "Reverb UK Seller"

                        # Determine accurate UK town / city postcode
                        loc_data = it.get("location", {}) or {}
                        locality = loc_data.get("locality") or loc_data.get("display_location") or ""
                        postcode = resolve_uk_location_postcode(locality, shop_name)

                        brand = detect_brand_tier(title)
                        if brand == "Epiphone (Exclude)":
                            continue
                        era = detect_era(title)
                        flags = detect_repair_and_case(title)
                        is_lefty = detect_dexterity(title)

                        # Scrape seller's actual offered delivery / shipping fee directly from the listing
                        shipping_obj = it.get("shipping", {}) or {}
                        rates = shipping_obj.get("rates", []) or []
                        gb_rate = next((r for r in rates if r.get("region_code") == "GB"), None)
                        if not gb_rate:
                            ior = shipping_obj.get("initial_offer_rate", {}) or {}
                            if ior.get("region_code") == "GB":
                                gb_rate = ior

                        shipping_available = False
                        shipping_cost = 0.0
                        shipping_carrier = "Collection in Person Only"

                        if gb_rate and "rate" in gb_rate:
                            shipping_available = True
                            rate_info = gb_rate["rate"]
                            amt_str = rate_info.get("amount")
                            if amt_str is None and isinstance(rate_info.get("original"), dict):
                                amt_str = rate_info["original"].get("amount")
                            try:
                                shipping_cost = round(float(amt_str), 2) if amt_str is not None else 0.0
                            except (ValueError, TypeError):
                                shipping_cost = 0.0

                            if shipping_cost == 0.0:
                                shipping_carrier = "Seller Free UK Delivery"
                            else:
                                shipping_carrier = f"Seller Postage: £{shipping_cost:.2f}"
                        elif shipping_obj.get("free_expedited_shipping") or shipping_obj.get("free_shipping"):
                            shipping_available = True
                            shipping_cost = 0.0
                            shipping_carrier = "Seller Free UK Delivery"
                        elif shipping_obj.get("local") is True:
                            shipping_available = False
                            shipping_cost = 0.0
                            shipping_carrier = "Collection in Person Only"

                        harvested.append({
                            "id": f"reverb_{item_id}",
                            "title": title,
                            "price": price,
                            "source": f"{shop_name} ({locality})" if locality else shop_name,
                            "url": web_url,
                            "image_url": image_url,
                            "postcode": postcode,
                            "brand_tier": brand,
                            "year": era["year"],
                            "era_badge": era["badge"],
                            "era_boost": era.get("boost", 0.0),
                            "era_notes": era.get("notes", ""),
                            "has_case": flags["has_case"],
                            "has_repair": flags["has_repair"],
                            "is_left_handed": is_lefty,
                            "shipping_available": shipping_available,
                            "shipping_cost": shipping_cost,
                            "shipping_carrier": shipping_carrier,
                            "published_at": it.get("published_at") or it.get("created_at")
                        })
                        print(f"  ✓ Live UK [{brand}]: {title} (£{price}) - {shop_name}")
        except Exception as e:
            print(f"  ✗ Error querying {q}: {e}")

    return harvested

def load_config():
    """Loads configuration from config.json and overlays environment variables (for GitHub Actions / cloud)."""
    cfg = {}
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    # Environment variable overrides (keeps secrets out of Git)
    if os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET"):
        cfg["ebay"] = {
            "enabled": True,
            "client_id": os.environ["EBAY_CLIENT_ID"].strip(),
            "client_secret": os.environ["EBAY_CLIENT_SECRET"].strip(),
        }
    if os.environ.get("GMAIL_APP_PASSWORD"):
        alert_email = os.environ.get("ALERT_EMAIL", "lkberry137@gmail.com").strip()
        cfg["email_alerts"] = {
            "enabled": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "from_email": alert_email,
            "to_email": alert_email,
            "app_password": os.environ["GMAIL_APP_PASSWORD"].strip(),
            "min_price_drop": 50,
        }
    return cfg

def get_ebay_oauth_token(client_id, client_secret):
    """Generates an OAuth 2.0 application access token using eBay Client Credentials."""
    import base64
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_auth}"
    }
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("access_token")
    except Exception as e:
        print(f"  ✗ Error authenticating with eBay API: {e}")
        return None

def harvest_live_ebay(client_id, client_secret):
    """Fetches real live Gibson ES-335 items from the official eBay Browse API (eBay UK)."""
    token = get_ebay_oauth_token(client_id, client_secret)
    if not token:
        return []

    print("\n🔍 Harvesting live UK items from official eBay Browse API...")
    queries = ["gibson es-335", "orville 335", "heritage h-535", "tokai 335"]
    harvested = []
    seen_ids = set()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "Accept": "application/json"
    }

    for q in queries:
        params = {
            "q": q,
            "category_ids": "3858", # Electric Guitars
            "filter": "price:[600..],priceCurrency:GBP,itemLocationCountry:GB",
            "limit": "40"
        }
        url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for it in data.get("itemSummaries", []):
                    item_id = it.get("itemId")
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    title = it.get("title", "")
                    title_lower = title.lower()
                    if any(bad in title_lower for bad in ["case only", "pickguard", "wiring", "pickups only", "strap", "knobs", "epiphone", "love rock", "goldstar", "breezysound", "uls129", "lc-156", "ls115", "ls75"]):
                        if "elitist" not in title_lower:
                            continue

                    price_val = it.get("price", {}).get("value", "0")
                    try:
                        price = round(float(price_val), 2)
                    except ValueError:
                        continue
                    if price < 600:
                        continue

                    web_url = it.get("itemWebUrl", "")
                    image_url = it.get("image", {}).get("imageUrl", "")
                    seller_name = it.get("seller", {}).get("username", "eBay UK Seller")
                    loc_info = it.get("itemLocation", {}) or {}
                    raw_pc = (loc_info.get("postalCode") or "").strip()
                    city = (loc_info.get("city") or "").strip()
                    if raw_pc:
                        postcode = raw_pc.replace("*", "").strip() or resolve_uk_location_postcode(city, seller_name)
                    else:
                        postcode = resolve_uk_location_postcode(city, seller_name)

                    brand = detect_brand_tier(title)
                    if brand == "Epiphone (Exclude)":
                        continue
                    era = detect_era(title)
                    flags = detect_repair_and_case(title)
                    is_lefty = detect_dexterity(title)

                    # Scrape exact eBay shipping/delivery cost
                    shipping_opts = it.get("shippingOptions", []) or []
                    shipping_available = False
                    shipping_cost = 0.0
                    shipping_carrier = "Collection in Person Only"
                    if shipping_opts:
                        opt = shipping_opts[0]
                        ship_cost_obj = opt.get("shippingCost", {}) or {}
                        ship_type = opt.get("shippingCostType", "")
                        if "value" in ship_cost_obj:
                            try:
                                shipping_cost = round(float(ship_cost_obj["value"]), 2)
                                shipping_available = True
                                if shipping_cost == 0.0:
                                    shipping_carrier = "Seller Free UK Delivery"
                                else:
                                    shipping_carrier = f"Seller Postage: £{shipping_cost:.2f}"
                            except (ValueError, TypeError):
                                pass
                        elif ship_type == "FIXED":
                            shipping_available = True
                            shipping_cost = 0.0
                            shipping_carrier = "Seller Free UK Delivery"

                    source_label = f"eBay UK ({city})" if city else f"eBay UK ({seller_name})"

                    harvested.append({
                        "id": f"ebay_{item_id}",
                        "title": title,
                        "price": price,
                        "source": source_label,
                        "url": web_url,
                        "image_url": image_url,
                        "postcode": postcode,
                        "brand_tier": brand,
                        "year": era["year"],
                        "era_badge": era["badge"],
                        "era_boost": era.get("boost", 0.0),
                        "era_notes": era.get("notes", ""),
                        "has_case": flags["has_case"],
                        "has_repair": flags["has_repair"],
                        "is_left_handed": is_lefty,
                        "shipping_available": shipping_available,
                        "shipping_cost": shipping_cost,
                        "shipping_carrier": shipping_carrier,
                        "published_at": it.get("itemCreationDate")
                    })
                    print(f"  ✓ Live [eBay UK]: {title} (£{price}) - {source_label}")
        except Exception as e:
            print(f"  ✗ Error querying eBay for '{q}': {e}")

    print(f"Found {len(harvested)} live guitars on eBay UK!")
    return harvested

INDIE_UK_SHOPS = [
    {"slug": "jordan", "name": "Jordan Guitars", "base": "https://jordanguitars.co.uk", "type": "shopify", "postcode": "NR1 1AA", "city": "Norwich", "shipping_cost": 0.0, "shipping_carrier": "Free Insured UK Delivery"},
    {"slug": "soundaffects", "name": "Soundaffects", "base": "https://www.soundaffects.com", "type": "shopify", "postcode": "PR7 1NY", "city": "Ormskirk", "shipping_cost": 0.0, "shipping_carrier": "Free UK Courier"},
    {"slug": "atb", "name": "ATB Guitars", "base": "https://atbguitars.com", "type": "shopify", "postcode": "GL50 1TA", "city": "Cheltenham", "shipping_cost": 25.0, "shipping_carrier": "Dealer UK Courier: £25.00"},
    {"slug": "guitarvillage", "name": "Guitar Village", "base": "https://guitarvillage.co.uk", "type": "woo", "postcode": "GU9 7ND", "city": "Farnham", "shipping_cost": 0.0, "shipping_carrier": "Free UK Delivery"},
    {"slug": "fairdeal", "name": "Fair Deal Music", "base": "https://www.fairdealmusic.co.uk", "type": "shopify", "postcode": "B5 4SL", "city": "Birmingham", "shipping_cost": 0.0, "shipping_carrier": "Free UK Delivery"},
    {"slug": "notom", "name": "No.Tom Guitars", "base": "https://notomguitars.com", "type": "shopify", "postcode": "WC2H 8LP", "city": "London", "shipping_cost": 35.0, "shipping_carrier": "Dealer UK Courier: £35.00"},
    {"slug": "wunjo", "name": "Wunjo Guitars", "base": "https://wunjoguitars.com", "type": "shopify", "postcode": "WC2H 8LA", "city": "London", "shipping_cost": 25.0, "shipping_carrier": "Dealer UK Courier: £25.00"},
    {"slug": "musicstreet", "name": "Music Street", "base": "https://musicstreet.co.uk", "type": "shopify", "postcode": "PE29 3NW", "city": "Huntingdon", "shipping_cost": 0.0, "shipping_carrier": "Free UK Delivery"},
    {"slug": "worldguitars", "name": "World Guitars", "base": "https://worldguitars.co.uk", "type": "shopify", "postcode": "GL10 2BG", "city": "Stonehouse", "shipping_cost": 0.0, "shipping_carrier": "Free UK Delivery"},
    {"slug": "regentsounds", "name": "Regent Sounds", "base": "https://www.regentsounds.com", "type": "shopify", "postcode": "WC2H 8LA", "city": "London", "shipping_cost": 25.0, "shipping_carrier": "Dealer UK Courier: £25.00"},
]

def harvest_live_indie_shops():
    """Fetches real, in-stock direct website listings from 10 UK independent guitar shops."""
    print("\n🏪 Harvesting live in-stock guitars from Independent UK Guitar Shops...")
    harvested = []
    seen_ids = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    bad_terms = [
        "case only", "hard case only", "pickguard", "wiring", "pickups only", "pickup set",
        "strap", "knobs", "epiphone", "pedal", "cable", "strings", "book", "t-shirt",
        "love rock", "goldstar", "breezysound", "sold"
    ]
    queries = ["gibson 335", "orville 335", "heritage 535", "tokai es"]

    for shop in INDIE_UK_SHOPS:
        shop_count = 0
        for q in queries:
            try:
                if shop["type"] == "shopify":
                    url = f"{shop['base']}/search/suggest.json?q={urllib.parse.quote(q)}&resources[type]=product&resources[limit]=10"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    products = data.get("resources", {}).get("results", {}).get("products", [])
                    for p in products:
                        if not p.get("available", False):
                            continue
                        pid = f"indie_{shop['slug']}_{p.get('id')}"
                        if pid in seen_ids:
                            continue
                        title = (p.get("title") or "").strip()
                        vendor = (p.get("vendor") or "").strip().lower()
                        tlow = title.lower()
                        if "epiphone" in vendor and "elitist" not in tlow:
                            continue
                        if any(b in tlow for b in bad_terms) and "elitist" not in tlow:
                            continue
                        if not any(m in tlow for m in ["335", "535", "es-1", "es-2", "es1", "es60", "es70", "es80", "es90", "es120", "es135", "es156", "es160", "es166"]):
                            continue
                        try:
                            price = round(float(p.get("price") or 0), 2)
                        except (ValueError, TypeError):
                            continue
                        if price < 600:
                            continue
                        desc = re.sub(r'<[^>]+>', ' ', p.get("body") or "")
                        brand = detect_brand_tier(title, desc)
                        if brand == "Epiphone (Exclude)":
                            continue
                        seen_ids.add(pid)
                        rel_url = (p.get("url") or "").split("?")[0]
                        full_url = f"{shop['base']}{rel_url}" if rel_url.startswith("/") else rel_url
                        img_url = p.get("image") or (p.get("featured_image", {}) or {}).get("url") or ""
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        era = detect_era(f"{title} {desc[:300]}")
                        flags = detect_repair_and_case(title, desc)
                        is_lefty = detect_dexterity(title, desc)
                        harvested.append({
                            "id": pid,
                            "title": title,
                            "price": price,
                            "source": f"{shop['name']} ({shop['city']})",
                            "source_type": "indie",
                            "url": full_url,
                            "image_url": img_url,
                            "postcode": shop["postcode"],
                            "brand_tier": brand,
                            "year": era["year"],
                            "era_badge": era["badge"],
                            "era_boost": era.get("boost", 0.0),
                            "era_notes": era.get("notes", ""),
                            "has_case": flags["has_case"],
                            "has_repair": flags["has_repair"],
                            "is_left_handed": is_lefty,
                            "shipping_available": True,
                            "shipping_cost": shop["shipping_cost"],
                            "shipping_carrier": shop["shipping_carrier"]
                        })
                        shop_count += 1
                elif shop["type"] == "woo":
                    url = f"{shop['base']}/wp-json/wc/store/v1/products?search={urllib.parse.quote(q)}&per_page=15"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        products = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    if not isinstance(products, list):
                        continue
                    for p in products:
                        if not p.get("is_in_stock", False):
                            continue
                        pid = f"indie_{shop['slug']}_{p.get('id')}"
                        if pid in seen_ids:
                            continue
                        title = re.sub(r'&#8211;|&#8212;|&amp;', '-', (p.get("name") or "").strip())
                        tlow = title.lower()
                        if any(b in tlow for b in bad_terms) and "elitist" not in tlow:
                            continue
                        if not any(m in tlow for m in ["335", "535", "es-1", "es-2", "es1", "es60", "es70", "es80", "es90", "es120", "es135", "es156", "es160", "es166"]):
                            continue
                        prices = p.get("prices", {}) or {}
                        minor = int(prices.get("currency_minor_unit", 2))
                        try:
                            price = round(float(prices.get("price") or 0) / (10 ** minor), 2)
                        except (ValueError, TypeError):
                            continue
                        if price < 600:
                            continue
                        desc = re.sub(r'<[^>]+>', ' ', p.get("description") or "")
                        brand = detect_brand_tier(title, desc)
                        if brand == "Epiphone (Exclude)":
                            continue
                        seen_ids.add(pid)
                        full_url = p.get("permalink") or shop["base"]
                        imgs = p.get("images") or []
                        img_url = imgs[0].get("src", "") if imgs else ""
                        era = detect_era(f"{title} {desc[:300]}")
                        flags = detect_repair_and_case(title, desc)
                        is_lefty = detect_dexterity(title, desc)
                        harvested.append({
                            "id": pid,
                            "title": title,
                            "price": price,
                            "source": f"{shop['name']} ({shop['city']})",
                            "source_type": "indie",
                            "url": full_url,
                            "image_url": img_url,
                            "postcode": shop["postcode"],
                            "brand_tier": brand,
                            "year": era["year"],
                            "era_badge": era["badge"],
                            "era_boost": era.get("boost", 0.0),
                            "era_notes": era.get("notes", ""),
                            "has_case": flags["has_case"],
                            "has_repair": flags["has_repair"],
                            "is_left_handed": is_lefty,
                            "shipping_available": True,
                            "shipping_cost": shop["shipping_cost"],
                            "shipping_carrier": shop["shipping_carrier"]
                        })
                        shop_count += 1
            except Exception:
                continue
        if shop_count > 0:
            print(f"  ✓ [{shop['name']}]: {shop_count} live in-stock 335s")

    print(f"Found {len(harvested)} live in-stock guitars across Independent UK Shops!")
    return harvested

def harvest_all_sources():
    """Harvests live listings from Independent UK Shops + Reverb UK + eBay UK."""
    deals = harvest_live_indie_shops()
    deals.extend(harvest_live_reverb())
    cfg = load_config()
    ebay_cfg = cfg.get("ebay", {})
    if ebay_cfg.get("enabled") and ebay_cfg.get("client_id") and "YOUR_EBAY" not in ebay_cfg.get("client_id"):
        ebay_deals = harvest_live_ebay(ebay_cfg["client_id"], ebay_cfg.get("client_secret", ""))
        deals.extend(ebay_deals)
    return deals

def main():
    print("=" * 60)
    print("🎸 Gibson ES-335 UK Deal Scanner & Travel Engine")
    print("=" * 60)
    init_db()

    if "--serve" in sys.argv:
        port = int(os.environ.get("PORT", 8000))
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        filepath = os.path.join(os.path.dirname(__file__), "deals.json")
        if os.path.exists(filepath):
            start_server(port)
            return

    # Harvest from all live sources (Independent UK Shops + Reverb UK + eBay UK)
    all_live_deals = harvest_all_sources()

    print(f"\nTotal live active UK guitars: {len(all_live_deals)}")
    enriched = enrich_listings(all_live_deals)

    # Preserve any imported Gumtree & FB deals across runs
    filepath = os.path.join(os.path.dirname(__file__), "deals.json")
    saved_imports = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                prev = json.load(f)
                seen_ids = {d.get("id") for d in enriched}
                saved_imports = [d for d in prev if (d.get("id", "").startswith("gumtree_") or d.get("id", "").startswith("fb_")) and d.get("id") not in seen_ids]
        except Exception:
            pass

    combined_deals = saved_imports + enriched
    export_deals_json(combined_deals)
    check_and_send_alerts(combined_deals)

    if "--serve" in sys.argv:
        port = int(os.environ.get("PORT", 8000))
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        start_server(port)

if __name__ == "__main__":
    main()
