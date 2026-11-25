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
    "GL10 2BG": (51.7463, -2.2869), # Stonehouse World Guitars
    "LE3 8HN": (52.6486, -1.2017),  # Leicester Jordan Guitars
    "NG9 8AR": (52.9278, -1.2750),  # Stapleford Nottingham Squealing Pig
    "TA1 5LU": (51.0150, -3.1030),  # Taunton Somerset Gas Station Guitars
    "AL1 1NG": (51.7520, -0.3360),  # St Albans The 58 Sound
    "CF10 5DR": (51.4730, -3.1730), # Cardiff MotoMusic
    "SW6 4SG": (51.4728, -0.2030),  # London New Kings Road Vintage
    "CV47 0AA": (52.2510, -1.3880), # Southam Warwickshire Rolly's Guitars
    "BN22 9BH": (50.7905, 0.2890),  # Eastbourne Bonners Music
    "BB7 9YE": (53.8220, -2.4080),  # Whalley Lancs Reidys Home of Music
    "CA3 8UU": (54.9010, -2.9360),  # Carlisle Rainbow Music
    "SR1 1AA": (54.9069, -1.3838)   # Sunderland Tyne & Wear
}

UK_CITY_POSTCODES = {
    "hull": "HU1 1AA", "beverley": "HU17 8DB", "york": "YO1 7HH", "selby": "YO8 8LZ",
    "leeds": "LS1 1AA", "sheffield": "S1 2GE", "grimsby": "DN31 1AA", "scunthorpe": "DN15 6AA",
    "doncaster": "DN1 1AA", "mansfield": "NG18 1AA", "nottingham": "NG1 1AA", "derby": "DE1 1AA",
    "leicester": "LE1 1AA", "lincoln": "LN1 1AA", "liverpool": "L1 8JQ", "manchester": "M1 1AE",
    "bristol": "BS1 1AA", "bath": "BA1 1AA", "cardiff": "CF10 1AA", "south wales": "CF10 1AA",
    "london": "SW1A 1AA", "norwood": "SW1A 1AA", "birmingham": "B1 1AA", "norwich": "NR1 1AA",
    "colchester": "CO4 9QP", "newcastle": "NE1 1AA", "sunderland": "SR1 1AA", "oxford": "OX1 1AA", "cambridge": "CB1 1AA",
    "exeter": "EX1 1AA", "plymouth": "PL1 1AA", "southampton": "SO14 1AA", "portsmouth": "PO1 1AA",
    "bournemouth": "BH1 1AA", "farnham": "GU9 7ND", "guildford": "GU1 4RF", "cheltenham": "GL50 1TA",
    "ormskirk": "PR7 1NY", "taunton": "TA1 5LU", "st albans": "AL1 1NG", "eastbourne": "BN22 9BH",
    "carlisle": "CA3 8UU", "blackburn": "BB7 9YE", "reading": "RG1 1DN"
}

def resolve_uk_location_postcode(locality, shop_name=""):
    comb = f"{locality} {shop_name}".lower()
    for k, pc in UK_SHOP_POSTCODES.items():
        if k in comb:
            return pc
    for k, pc in UK_CITY_POSTCODES.items():
        if k in comb:
            return pc
    return "UK (TBC)"

def get_postcode_coords(postcode):
    """Fetches (lat, lng) for a UK postcode or masked outcode (e.g. YO8***) via cache or postcodes.io."""
    if not postcode or "TBC" in str(postcode).upper():
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

def detect_model_family(title):
    """Detects whether a listing is an ES-345 vs ES-335 (or equivalent)."""
    tlow = (title or "").lower()
    if re.search(r'\b(es[\s-]?345|345)\b', tlow):
        return "ES-345"
    return "ES-335"

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

def evaluate_deal(price, brand_tier, era_boost, has_repair, has_case, drive_hours, max_hours=3.0, fuel_cost=0.0, model_family="ES-335"):
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
        if model_family == "ES-345":
            if true_landed_cost < 2300 or (true_landed_cost <= 2350 and era_boost >= 1.0):
                return {
                    "grade": "A+",
                    "badge_class": "bg-emerald-500 text-stone-950 font-black",
                    "verdict": "Grade A+ (Holy Grail Steal)",
                    "reason": f"Landed at £{true_landed_cost:.0f}. Rare sub-£2.3k threshold for authentic Gibson ES-345!",
                    "true_landed_cost": true_landed_cost,
                    "case_penalty": case_penalty
                }
            elif true_landed_cost <= 2500:
                return {
                    "grade": "A",
                    "badge_class": "bg-teal-500 text-stone-950 font-bold",
                    "verdict": "Grade A (Prime Target)",
                    "reason": f"Landed at £{true_landed_cost:.0f}. Well under £2,550 ES-345 market floor.",
                    "true_landed_cost": true_landed_cost,
                    "case_penalty": case_penalty
                }
            elif true_landed_cost <= 2750:
                return {
                    "grade": "B+",
                    "badge_class": "bg-blue-600 text-white",
                    "verdict": "Grade B+ (Fair Market)",
                    "reason": f"Landed at £{true_landed_cost:.0f}. Solid ES-345 market price; worth an offer.",
                    "true_landed_cost": true_landed_cost,
                    "case_penalty": case_penalty
                }
            elif true_landed_cost <= 2950:
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

        # Standard ES-335 thresholds
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_locations (
            shop_key TEXT PRIMARY KEY,
            locality TEXT,
            region TEXT,
            postcode TEXT,
            lat REAL,
            lng REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scan_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def _get_scan_state(key):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM scan_state WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def _set_scan_state(key, value):
    init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO scan_state (key, value, updated_at) VALUES (?, ?, ?)",
        (key, str(value), now_iso),
    )
    conn.commit()
    conn.close()

def _get_fb_sweep_timing(interval_hours=23.0):
    last_str = _get_scan_state("fb_apify_last_run_at")
    last_dt = _parse_iso_dt(last_str)
    if not last_dt:
        return None, None
    elapsed_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
    remaining_hours = max(0.0, float(interval_hours) - elapsed_hours)
    return elapsed_hours, remaining_hours

def should_run_fb_apify_sweep(interval_hours=23.0, force=False):
    if force or "--force-fb" in sys.argv:
        return True
    elapsed_hours, _ = _get_fb_sweep_timing(interval_hours)
    if elapsed_hours is None:
        return True
    return elapsed_hours >= float(interval_hours)

def geocode_uk_town(locality, region="ENG"):
    """Resolves any UK town/village name to (postcode_or_outcode, (lat, lng)) using region matching."""
    if not locality:
        return "UK (TBC)", None
    loc_low = locality.strip().lower()
    # 1. Instant match for major UK cities/towns
    for k, pc in UK_CITY_POSTCODES.items():
        if k == loc_low or k in loc_low:
            coords = get_postcode_coords(pc)
            if coords:
                return pc, coords

    # 2. Live lookup via postcodes.io/places (covers every UK town & village)
    region_to_country = {"ENG": "England", "SCT": "Scotland", "WLS": "Wales", "NIR": "Northern Ireland"}
    want_country = region_to_country.get((region or "").upper())
    try:
        url = f"https://api.postcodes.io/places?q={urllib.parse.quote(locality.strip())}&limit=5"
        req = urllib.request.Request(url, headers={"User-Agent": "Gibson335Radar/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        results = data.get("result") or []
        if results:
            pick = None
            if want_country:
                pick = next((r for r in results if r.get("country") == want_country and r.get("outcode")), None)
            if not pick:
                pick = next((r for r in results if r.get("outcode")), results[0])
            outcode = pick.get("outcode") or locality.strip()
            lat, lng = pick.get("latitude"), pick.get("longitude")
            if lat is not None and lng is not None:
                POSTCODE_CACHE[outcode] = (lat, lng)
                return outcode, (lat, lng)
    except Exception:
        pass
    return "UK (TBC)", None

def resolve_reverb_shop_location(shop_name, item_id, headers):
    """Fetches & caches each Reverb shop's real UK town/locality from Reverb's API in deals.db."""
    shop_key = (shop_name or "").strip().lower()
    if not shop_key:
        return "", "UK (TBC)", None

    # 1. Check SQLite cache first (instant on all future scans)
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT locality, postcode, lat, lng FROM shop_locations WHERE shop_key = ?", (shop_key,))
        row = c.fetchone()
        conn.close()
        if row:
            loc, pc, lat, lng = row
            coords = (lat, lng) if (lat is not None and lng is not None) else None
            return (loc or ""), (pc or "UK (TBC)"), coords
    except Exception:
        pass

    # 2. Fetch real location from Reverb single-listing API once per unique shop
    locality, region = "", "ENG"
    try:
        detail_url = f"https://api.reverb.com/api/listings/{item_id}"
        req = urllib.request.Request(detail_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            detail = json.loads(resp.read().decode("utf-8", errors="ignore"))
        loc_obj = detail.get("location", {}) or {}
        locality = (loc_obj.get("locality") or "").strip()
        region = (loc_obj.get("region") or "ENG").strip()
    except Exception:
        pass

    pc, coords = geocode_uk_town(locality, region) if locality else ("UK (TBC)", None)

    # Secondary fallback to verified shop dictionary only if Reverb returned no locality
    if not coords:
        fallback_pc = resolve_uk_location_postcode(locality, shop_name)
        if fallback_pc != "UK (TBC)":
            pc = fallback_pc
            coords = get_postcode_coords(fallback_pc)

    # 3. Persist to SQLite cache so this shop is resolved instantly forever
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO shop_locations (shop_key, locality, region, postcode, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
            (shop_key, locality, region, pc, coords[0] if coords else None, coords[1] if coords else None)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return locality, pc, coords

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

        if price_drop >= min_drop and not it.get("is_auction"):
            alert_key = f"drop_{lid}_{int(price)}"
            tag = f"PRICE DROP (−£{int(round(price_drop))})"
        elif (hull_grade == "A+" or som_grade == "A+") and not it.get("is_auction"):
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
BLOCKED_LISTING_IDS = {
    "gumtree_1511012969", # Suspected fake ("Bozeman Plant MT USA" ES-335 + misaligned tuners)
}

def load_blocklist():
    ids = set(BLOCKED_LISTING_IDS)
    bl_path = os.path.join(os.path.dirname(__file__), "blocklist.json")
    if os.path.exists(bl_path):
        try:
            with open(bl_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    ids.update(str(x) for x in data)
        except Exception:
            pass
    return ids

def detect_fake_risk(title, desc="", price=0, brand="", has_repair=False, year=None, is_auction=False):
    """Detects counterfeit / Chibson red flags on Gibson ES-335/345 listings."""
    tlow = (title or "").lower()
    combined = f"{title} {desc}".lower()
    reasons = []

    # 1. Impossible factory claims for ES-335/345
    if "bozeman" in combined and "gibson" in combined:
        reasons.append("Impossible factory: Gibson Bozeman MT only builds acoustics, never ES-335/345s")
    if "kalamazoo" in combined and "gibson" in combined and year and int(year) >= 1985 and "heritage" not in combined and "reissue" not in combined and "custom shop" not in combined:
        reasons.append(f"Impossible factory: Kalamazoo closed in 1984 (listed as {year})")

    # 2. Explicit replica / copy / counterfeit hardware red flags
    fake_keywords = [
        ("chibson", "Listed as Chibson/replica"),
        ("replica", "Listed as replica"),
        ("copy", "Listed as copy"),
        ("tribute build", "Non-Gibson tribute build"),
        ("kit guitar", "Kit guitar build"),
        ("3-screw", "3-screw truss rod cover (Gibson uses 2)"),
        ("3 screw", "3-screw truss rod cover (Gibson uses 2)"),
        ("metric bridge", "Metric bridge posts (counterfeit indicator)"),
    ]
    for kw, msg in fake_keywords:
        if kw in tlow:
            reasons.append(msg)

    # 3. Suspiciously cheap Gibson USA ES-335/345 without repair (excluding 335-S solid-body and live auctions)
    if not is_auction and "gibson usa" in (brand or "").lower() and not has_repair and "335-s" not in tlow and "studio" not in tlow:
        if price and 0 < float(price) < 1250:
            reasons.append(f"Suspiciously low price (£{int(price)}) for an unrepaired authentic Gibson USA ES-335/345 — inspect carefully")

    if reasons:
        return True, " • ".join(reasons)
    return False, ""

def is_valid_335_model(title, brand=""):
    """Strictly filters out Epiphones, non-335 Tokai models, and unrelated non-ES solid bodies."""
    tlow = (title or "").lower()
    blow = (brand or "").lower()
    if blow == "epiphone (exclude)" or ("epiphone" in tlow and "elitist" not in tlow):
        return False

    # Avoid letting unrelated non-ES solid bodies or keyword-stuffed non-335/345 ES models slip in via search queries
    if "gibson" in tlow or "gibson" in blow:
        if not re.search(r'(335|345|355|es[\s-]?\d{3})', tlow):
            return False
        if re.search(r'\bes[\s-]?(125|135|137|150|175|225|275|295|325|330|333|339)\b', tlow):
            if not re.search(r'\bes[\s-]?(335|345|355)\b', tlow):
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
        if not (re.search(r'\bes[\s-]?\d{2,3}', tlow) or "335" in tlow or "345" in tlow or "semi" in tlow):
            return False

    return True

def enrich_listings(listings, car_mpg=38.0, fuel_price=1.42, skip_model_filter=False):
    """Calculates distances, fuel costs, counterfeit risk flags, and deal grades for both hubs."""
    enriched = []
    blocked = load_blocklist()
    
    for item in listings:
        # Skip user-removed / blocked fake listings
        if str(item.get("id", "")) in blocked:
            continue

        # Strictly exclude Epiphones, non-335 Tokai models, and unrelated non-ES solid bodies
        brand = item.get("brand_tier", "")
        if not skip_model_filter and not is_valid_335_model(item.get("title", ""), brand):
            continue

        model_family = detect_model_family(item.get("title", ""))
        item["model_family"] = model_family

        fake_risk, fake_reason = detect_fake_risk(
            title=item.get("title", ""),
            desc=item.get("era_notes", ""),
            price=item.get("price", 0),
            brand=brand,
            has_repair=item.get("has_repair", False),
            year=item.get("year"),
            is_auction=item.get("is_auction", False)
        )
        item["fake_risk"] = fake_risk
        item["fake_reason"] = fake_reason

        pc = item.get("postcode", "")
        coords = item.get("coords") or get_postcode_coords(pc)
        
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
            fuel_cost=hull_travel["fuel_cost"],
            model_family=model_family
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
            fuel_cost=somerset_travel["fuel_cost"],
            model_family=model_family
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

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents automatic redirect following so /share/ Location headers can be inspected hop-by-hop."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def is_facebook_url(url):
    """Returns True for facebook.com (including m./web./mobile.), fb.com, and fb.me URLs."""
    try:
        host = (urllib.parse.urlparse((url or "").strip()).hostname or "").lower()
    except Exception:
        return False
    return bool(re.match(r'^(?:[a-z0-9-]+\.)*(?:facebook\.com|fb\.com|fb\.me)$', host))


def _extract_fb_item_id(url_or_text):
    """Extracts numeric Facebook Marketplace item ID directly or from encoded redirect query params."""
    if not url_or_text:
        return None
    text = str(url_or_text)
    m = re.search(r'/marketplace/(?:[^/?#]+/)?item/(\d{8,20})', text)
    if m:
        return m.group(1)
    try:
        parsed = urllib.parse.urlparse(text)
        qs = urllib.parse.parse_qs(parsed.query)
        for key in ("next", "u", "redirect_uri", "href", "target"):
            for val in qs.get(key, []):
                decoded = urllib.parse.unquote(val)
                m2 = re.search(r'/marketplace/(?:[^/?#]+/)?item/(\d{8,20})', decoded)
                if m2:
                    return m2.group(1)
    except Exception:
        pass
    return None


def normalize_and_resolve_facebook_url(url):
    """Validates any Facebook Marketplace /item/ or mobile /share/ URL and resolves its clean canonical URL."""
    raw = (url or "").strip()
    if not raw or not is_facebook_url(raw):
        return None, None, "Not a valid Facebook Marketplace or share URL."

    # 1. Direct /marketplace/item/<id> link (www., m., web., with any tracking query params)
    direct_id = _extract_fb_item_id(raw)
    if direct_id:
        return f"https://www.facebook.com/marketplace/item/{direct_id}/", direct_id, None

    parsed = urllib.parse.urlparse(raw)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if not (path.startswith("/share/") or host.endswith("fb.me")):
        return (
            None,
            None,
            "Unsupported Facebook URL. Paste a Marketplace item link (/marketplace/item/...) or mobile share link (/share/...).",
        )

    # 2. Server-side redirect & HTML resolution for mobile /share/ links (with desktop Chrome UA)
    desktop_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    opener = urllib.request.build_opener(_NoRedirectHandler())
    current_url = raw

    for _ in range(6):
        req = urllib.request.Request(current_url, headers=desktop_headers)
        try:
            with opener.open(req, timeout=12) as resp:
                # Followed without 3xx -> inspect final URL and HTML body metadata
                final_id = _extract_fb_item_id(resp.geturl())
                if final_id:
                    return f"https://www.facebook.com/marketplace/item/{final_id}/", final_id, None

                html = resp.read(250 * 1024).decode("utf-8", errors="ignore")
                html_patterns = [
                    r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url["\']',
                    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
                    r'(?:/|\\/)marketplace(?:/|\\/)item(?:/|\\/)(\d{8,20})',
                    r'"listing_id"\s*:\s*"(\d{8,20})"',
                ]
                for pat in html_patterns:
                    m = re.search(pat, html, re.I)
                    if not m:
                        continue
                    candidate = m.group(1)
                    if candidate.isdigit():
                        return f"https://www.facebook.com/marketplace/item/{candidate}/", candidate, None
                    cid = _extract_fb_item_id(candidate.replace("\\/", "/"))
                    if cid:
                        return f"https://www.facebook.com/marketplace/item/{cid}/", cid, None
                break

        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            code = e.code
            e.close()
            if code in (301, 302, 303, 307, 308) and loc:
                next_url = urllib.parse.urljoin(current_url, loc)
                if urllib.parse.urlparse(next_url).scheme not in ("http", "https"):
                    break
                next_id = _extract_fb_item_id(next_url)
                if next_id:
                    return f"https://www.facebook.com/marketplace/item/{next_id}/", next_id, None
                current_url = next_url
                continue
            break
        except Exception:
            break

    return (
        None,
        None,
        "Could not resolve this Facebook /share/ link to a Marketplace item (it may be expired, a private group post, or blocked by Facebook). Paste the direct /marketplace/item/<id> URL or enter the details manually below.",
    )


def _resolve_uk_location_smart(loc_str):
    """Resolves either a UK postcode/outcode or a town/city string into (postcode, coords, display_city)."""
    clean = (loc_str or "").strip()
    if not clean:
        return "UK (TBC)", None, ""

    # 1. Direct UK postcode or outcode check (e.g. "LS1 1AA" or "EN9")
    if re.match(r'^[A-Za-z]{1,2}\d[A-Za-z\d]?(?:\s*\d[A-Za-z]{2})?$', clean):
        upper_pc = re.sub(r'\s+', ' ', clean.upper()).strip()
        coords = get_postcode_coords(upper_pc)
        if coords:
            return upper_pc, coords, upper_pc

    # 2. Strip trailing country suffixes from Marketplace locations (e.g. "Leeds, United Kingdom")
    city_clean = re.sub(
        r',\s*(?:united kingdom|uk|england|scotland|wales|great britain)\s*$',
        '',
        clean,
        flags=re.I,
    ).strip()
    pc, coords = geocode_uk_town(city_clean)
    if not coords and "," in city_clean:
        parts = [p.strip() for p in city_clean.split(",") if p.strip()]
        for candidate in ([parts[0], parts[-1]] if len(parts) > 1 else parts):
            pc, coords = geocode_uk_town(candidate)
            if coords:
                break
    return pc, coords, city_clean


def fetch_fb_listing_via_apify(canonical_url, token, actor_id="apify/facebook-marketplace-scraper"):
    """Runs Apify synchronous dataset endpoint for a single canonical Facebook Marketplace item URL."""
    actor_slug = (actor_id or "apify/facebook-marketplace-scraper").strip().replace("/", "~")
    safe_slug = urllib.parse.quote(actor_slug, safe="~-._")
    endpoint = f"https://api.apify.com/v2/acts/{safe_slug}/run-sync-get-dataset-items?timeout=50"

    payload = json.dumps({
        "startUrls": [{"url": canonical_url}],
        "resultsLimit": 1,
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        items = json.loads(body) if body else []
        if not isinstance(items, list) or not items:
            return None, {
                "code": "APIFY_EMPTY",
                "message": "Apify could not extract this Facebook listing (it may be sold, expired, or inside a private group). Enter the listing details manually below.",
            }
        first = items[0] if isinstance(items[0], dict) else {}
        if not first or first.get("error") or first.get("errorDescription"):
            err_detail = first.get("errorDescription") or first.get("error") or "Listing unavailable"
            return None, {
                "code": "APIFY_EMPTY",
                "message": f"Facebook listing could not be scraped ({err_detail}). Enter the listing details manually below.",
            }
        return first, None
    except urllib.error.HTTPError as e:
        code = e.code
        e.close()
        if code in (401, 403):
            return None, {
                "code": "APIFY_AUTH_ERROR",
                "message": "Apify rejected APIFY_TOKEN (401/403). Verify your Apify token in config.json or environment variables, or enter the listing details manually below.",
            }
        if code == 402:
            return None, {
                "code": "APIFY_LIMIT_REACHED",
                "message": "Apify monthly free-tier usage limit reached (402). Enter the listing details manually below.",
            }
        if code in (408, 504):
            return None, {
                "code": "APIFY_TIMEOUT",
                "message": f"Apify scraper timed out (HTTP {code}) on Facebook. Enter the listing details manually below.",
            }
        return None, {
            "code": "APIFY_HTTP_ERROR",
            "message": f"Apify API error (HTTP {code}). Enter the listing details manually below.",
        }
    except Exception as e:
        return None, {
            "code": "APIFY_TIMEOUT",
            "message": f"Apify request did not complete ({e}). Enter the listing details manually below.",
        }


def _parse_numeric_price(val):
    """Safely extracts a float price from Apify price dicts, formatted currency strings, or numbers."""
    if val is None or isinstance(val, bool):
        return 0.0
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    if isinstance(val, dict):
        for key in ("amount", "value", "formatted_amount"):
            if val.get(key) is not None:
                parsed = _parse_numeric_price(val[key])
                if parsed > 0:
                    return parsed
        cents = val.get("amount_with_offset_in_cents")
        if cents is not None:
            try:
                return round(float(cents) / 100.0, 2)
            except (ValueError, TypeError):
                pass
        return 0.0
    m = re.search(r'[\d,]+(?:\.\d+)?', str(val))
    if not m:
        return 0.0
    try:
        return round(float(m.group(0).replace(",", "")), 2)
    except ValueError:
        return 0.0


def _extract_apify_location(apify_item):
    """Extracts human-readable city text and optional (lat, lng) from Apify Marketplace output."""
    loc_obj = apify_item.get("location")
    apify_coords = None
    loc_text = ""

    if isinstance(loc_obj, dict):
        rg = loc_obj.get("reverse_geocode") or {}
        if isinstance(rg, dict):
            cp = rg.get("city_page") or {}
            if isinstance(cp, dict) and cp.get("display_name"):
                loc_text = str(cp["display_name"]).strip()
            elif rg.get("city"):
                loc_text = str(rg["city"]).strip()
        if not loc_text:
            loc_text = str(loc_obj.get("city") or loc_obj.get("display_name") or loc_obj.get("name") or "").strip()

        lat = loc_obj.get("latitude")
        lng = loc_obj.get("longitude")
        if lat is None and isinstance(rg, dict):
            lat = rg.get("latitude")
            lng = rg.get("longitude")
        try:
            if lat is not None and lng is not None:
                apify_coords = (float(lat), float(lng))
        except (ValueError, TypeError):
            apify_coords = None
    elif isinstance(loc_obj, str):
        loc_text = loc_obj.strip()

    if not loc_text:
        lt = apify_item.get("location_text") or apify_item.get("locationText") or apify_item.get("locationName") or ""
        if isinstance(lt, dict):
            loc_text = str(lt.get("text") or "").strip()
        elif isinstance(lt, str):
            loc_text = lt.strip()

    return loc_text, apify_coords


def _map_apify_fb_item_to_raw(apify_item, canonical_url, item_id, user_location=""):
    """Maps an Apify facebook-marketplace-scraper dataset item into the scanner/Landed Cost raw schema."""
    title = (
        apify_item.get("marketplace_listing_title")
        or apify_item.get("listingTitle")
        or apify_item.get("custom_title")
        or apify_item.get("title")
        or apify_item.get("name")
        or ""
    ).strip()

    price = _parse_numeric_price(
        apify_item.get("listing_price") or apify_item.get("listingPrice") or apify_item.get("price")
    )

    raw_loc_text, apify_coords = _extract_apify_location(apify_item)
    effective_loc = raw_loc_text or (user_location or "").strip()
    pc, coords, display_loc = _resolve_uk_location_smart(effective_loc)
    if apify_coords and 49.8 <= apify_coords[0] <= 61.0 and -8.5 <= apify_coords[1] <= 2.0:
        coords = apify_coords
        try:
            rev_url = f"https://api.postcodes.io/outcodes?lon={apify_coords[1]}&lat={apify_coords[0]}&limit=1"
            req = urllib.request.Request(rev_url, headers={"User-Agent": "Gibson335Radar/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                rdata = json.loads(resp.read().decode("utf-8", errors="ignore"))
            if rdata.get("status") == 200 and rdata.get("result"):
                rev_pc = rdata["result"][0].get("outcode")
                if rev_pc:
                    pc = rev_pc
        except Exception:
            pass
    if not display_loc:
        display_loc = user_location.strip() or "UK"

    # Extract primary image URL across common Apify snake_case and camelCase schemas
    image_url = ""
    plp = apify_item.get("primary_listing_photo")
    if isinstance(plp, dict):
        img_obj = plp.get("image") or {}
        if isinstance(img_obj, dict):
            image_url = img_obj.get("uri") or img_obj.get("url") or ""
        if not image_url:
            image_url = plp.get("photo_image_url") or plp.get("uri") or plp.get("url") or ""
    elif isinstance(plp, str):
        image_url = plp

    if not image_url:
        photos = apify_item.get("listing_photos") or apify_item.get("listingPhotos") or apify_item.get("images") or []
        if isinstance(photos, list) and photos:
            first_photo = photos[0]
            if isinstance(first_photo, dict):
                image_url = (first_photo.get("image") or {}).get("uri") or first_photo.get("url") or ""
            elif isinstance(first_photo, str):
                image_url = first_photo

    if not image_url:
        image_url = "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600"

    desc_obj = apify_item.get("redacted_description") or apify_item.get("description") or ""
    if isinstance(desc_obj, dict):
        desc = str(desc_obj.get("text") or "")
    else:
        desc = str(desc_obj or "")

    seller_obj = apify_item.get("marketplace_listing_seller") or apify_item.get("seller") or {}
    if isinstance(seller_obj, dict):
        seller_name = str(seller_obj.get("name") or "").strip()
    else:
        seller_name = str(seller_obj or apify_item.get("seller_name") or "").strip()

    published_at = apify_item.get("timestamp")
    if not published_at and apify_item.get("creation_time") is not None:
        ct = apify_item.get("creation_time")
        if isinstance(ct, (int, float)):
            try:
                published_at = datetime.fromtimestamp(float(ct), tz=timezone.utc).isoformat()
            except Exception:
                published_at = None
        elif isinstance(ct, str):
            published_at = ct

    if not title or price <= 0:
        return None, {
            "code": "APIFY_INCOMPLETE",
            "canonical_url": canonical_url,
            "message": "Facebook returned partial listing data (missing title or price). Review or fill the missing fields below.",
            "partial": {
                "title": title,
                "price": price if price > 0 else "",
                "location": display_loc,
                "canonical_url": canonical_url,
            },
        }

    brand = detect_brand_tier(title, desc)
    era = detect_era(f"{title} {desc}")
    flags = detect_repair_and_case(title, desc)
    is_lefty = detect_dexterity(title, desc)
    ship_info = detect_shipping_info(f"Facebook ({display_loc})", f"{title} {desc}", price)

    raw_item = {
        "id": f"fb_{item_id}",
        "title": title,
        "price": price,
        "source": f"Facebook ({display_loc})",
        "url": canonical_url,
        "image_url": image_url,
        "postcode": pc,
        "coords": coords,
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
        "shipping_carrier": ship_info["shipping_carrier"],
    }
    if published_at:
        raw_item["published_at"] = published_at
    if seller_name:
        raw_item["seller_name"] = seller_name
    return raw_item, None


def scrape_and_enrich_single_fb(url, user_location=""):
    """Resolves any Facebook Marketplace /share/ or /item/ URL, scrapes via Apify, and enriches for Landed Cost."""
    canonical_url, item_id, resolve_err = normalize_and_resolve_facebook_url(url)
    if resolve_err or not canonical_url:
        return None, {
            "code": "FB_URL_RESOLUTION_FAILED",
            "message": resolve_err or "Could not resolve Facebook URL.",
        }

    cfg = load_config()
    apify_cfg = cfg.get("apify") or {}
    token = (apify_cfg.get("token") or "").strip()
    actor_id = (apify_cfg.get("actor_id") or "apify/facebook-marketplace-scraper").strip()
    if not token or "YOUR_APIFY" in token.upper():
        return None, {
            "code": "MISSING_APIFY_TOKEN",
            "canonical_url": canonical_url,
            "message": (
                "APIFY_TOKEN is not configured on the local server. Set the APIFY_TOKEN environment variable "
                "(or add \"apify\": {\"token\": \"...\"} in config.json) to auto-scrape Facebook Marketplace, "
                "or enter the title and price manually below."
            ),
        }

    apify_item, apify_err = fetch_fb_listing_via_apify(canonical_url, token, actor_id=actor_id)
    if apify_err:
        apify_err.setdefault("canonical_url", canonical_url)
        return None, apify_err

    raw_item, map_err = _map_apify_fb_item_to_raw(apify_item, canonical_url, item_id, user_location=user_location)
    if map_err:
        return None, map_err

    enriched = enrich_listings([raw_item], skip_model_filter=True)
    if not enriched:
        return None, {
            "code": "ENRICHMENT_FAILED",
            "canonical_url": canonical_url,
            "message": "Listing could not be scored by the Landed Cost engine.",
        }
    return enriched[0], None


def build_manual_deal_item(url="", title="", price=0, location="", has_case=True, has_repair=False, shipping_cost=None, image_url=""):
    """Builds and enriches a manual/override listing so Landed Cost calculation always works cleanly."""
    import hashlib

    clean_title = (title or "").strip()
    try:
        numeric_price = round(float(price), 2)
    except (ValueError, TypeError):
        numeric_price = 0.0
    if not clean_title or numeric_price <= 0:
        return None

    clean_url = (url or "").strip()
    is_fb = bool(clean_url and is_facebook_url(clean_url))
    if is_fb:
        fb_id = _extract_fb_item_id(clean_url)
        if fb_id:
            clean_url = f"https://www.facebook.com/marketplace/item/{fb_id}/"
            item_id = f"fb_{fb_id}"
        else:
            clean_url = clean_url.split("?")[0]
            digest = hashlib.md5(clean_url.encode("utf-8")).hexdigest()[:10]
            item_id = f"fb_manual_{digest}"
    elif clean_url:
        digest = hashlib.md5(clean_url.encode("utf-8")).hexdigest()[:10]
        item_id = f"manual_{digest}"
    else:
        item_id = f"manual_{int(time.time())}"

    pc, coords, display_loc = _resolve_uk_location_smart(location)
    loc_label = display_loc or (location or "").strip() or "UK"
    if is_fb:
        source_label = f"Facebook ({loc_label})"
    elif clean_url:
        host = (urllib.parse.urlparse(clean_url).hostname or "").replace("www.", "")
        source_label = f"{host} ({loc_label})" if host else f"Manual Import ({loc_label})"
    else:
        source_label = f"Manual Import ({loc_label})"

    brand = detect_brand_tier(clean_title)
    era = detect_era(clean_title)
    is_lefty = detect_dexterity(clean_title)

    if shipping_cost is not None and str(shipping_cost).strip() != "":
        try:
            scost = round(float(shipping_cost), 2)
            ship_info = {
                "shipping_available": scost >= 0,
                "shipping_cost": max(0.0, scost),
                "shipping_carrier": "Seller Free UK Delivery" if scost == 0 else f"Seller Delivery: £{scost:.2f}",
            }
        except (ValueError, TypeError):
            ship_info = detect_shipping_info(source_label, clean_title, numeric_price)
    else:
        ship_info = detect_shipping_info(source_label, clean_title, numeric_price)

    raw_item = {
        "id": item_id,
        "title": clean_title,
        "price": numeric_price,
        "source": source_label,
        "url": clean_url or "#",
        "image_url": (image_url or "").strip() or "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600",
        "postcode": pc,
        "coords": coords,
        "brand_tier": brand,
        "year": era["year"],
        "era_badge": era["badge"],
        "era_boost": era.get("boost", 0.0),
        "era_notes": era.get("notes", ""),
        "has_case": bool(has_case),
        "has_repair": bool(has_repair),
        "is_left_handed": is_lefty,
        "shipping_available": ship_info["shipping_available"],
        "shipping_cost": ship_info["shipping_cost"],
        "shipping_carrier": ship_info["shipping_carrier"],
    }

    enriched = enrich_listings([raw_item], skip_model_filter=True)
    return enriched[0] if enriched else None

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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def _send_json(self, payload, status=200):
        res_body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(res_body)))
        self.end_headers()
        self.wfile.write(res_body)

    def _upsert_deal_to_json(self, new_item):
        filepath = os.path.join(os.path.dirname(__file__), "deals.json")
        deals = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8-sig") as f:
                deals = json.load(f)
        new_id = str(new_item.get("id", ""))
        deals = [d for d in deals if str(d.get("id", "")) != new_id]
        deals.insert(0, new_item)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(deals, f, indent=2)

    def _handle_import_request(self, payload):
        try:
            target_url = (payload.get("url") or "").strip()
            loc = (payload.get("location") or "").strip()
            title = (payload.get("title") or "").strip()
            raw_price = payload.get("price")
            is_manual = bool(payload.get("manual")) or (bool(title) and raw_price is not None and str(raw_price).strip() != "")

            if is_manual:
                try:
                    price_val = float(raw_price or 0)
                except (ValueError, TypeError):
                    price_val = 0.0
                if not title or price_val <= 0:
                    self._send_json({
                        "status": "error",
                        "code": "INVALID_MANUAL_INPUT",
                        "message": "Enter both a guitar title and a positive asking price (£) to calculate Landed Cost."
                    })
                    return

                has_case = payload.get("has_case", True)
                if isinstance(has_case, str):
                    has_case = has_case.strip().lower() not in ("false", "0", "no")
                has_repair = payload.get("has_repair", False)
                if isinstance(has_repair, str):
                    has_repair = has_repair.strip().lower() in ("true", "1", "yes")

                new_item = build_manual_deal_item(
                    url=target_url,
                    title=title,
                    price=price_val,
                    location=loc,
                    has_case=bool(has_case),
                    has_repair=bool(has_repair),
                    shipping_cost=payload.get("shipping_cost"),
                    image_url=payload.get("image_url", ""),
                )
                if not new_item:
                    self._send_json({
                        "status": "error",
                        "code": "MANUAL_BUILD_FAILED",
                        "message": "Could not build listing from provided manual details."
                    })
                    return
                self._upsert_deal_to_json(new_item)
                self._send_json({"status": "ok", "item": new_item})
                return

            if not target_url:
                self._send_json({
                    "status": "error",
                    "code": "MISSING_URL",
                    "message": "Paste a listing URL (Reverb, eBay UK, Gumtree, or Facebook Marketplace)."
                })
                return

            parsed = urllib.parse.urlparse(target_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                self._send_json({
                    "status": "error",
                    "code": "INVALID_URL",
                    "message": "Please paste a valid http:// or https:// listing URL."
                })
                return

            host = (parsed.hostname or "").lower()
            err_info = None
            new_item = None

            if "reverb.com" in host:
                new_item = parse_reverb_single(target_url)
                if not new_item:
                    err_info = {
                        "code": "REVERB_PARSE_ERROR",
                        "message": "Could not fetch this Reverb listing (check the /item/<id> link or enter details manually below)."
                    }
            elif "ebay.co.uk" in host or "ebay.com" in host:
                new_item = parse_ebay_single(target_url)
                if not new_item:
                    err_info = {
                        "code": "EBAY_PARSE_ERROR",
                        "message": "Could not fetch this eBay listing (ended/unlisted item, non-UK listing, or API error). Enter details manually below."
                    }
            elif "gumtree.com" in host:
                new_item = parse_gumtree_single(target_url, loc or "London")
                if not new_item:
                    err_info = {
                        "code": "GUMTREE_PARSE_ERROR",
                        "message": "Could not fetch this Gumtree listing (it may have been removed). Enter details manually below."
                    }
            elif is_facebook_url(target_url):
                new_item, err_info = scrape_and_enrich_single_fb(target_url, loc)
            else:
                err_info = {
                    "code": "UNSUPPORTED_URL",
                    "message": "Unsupported URL domain. Supported auto-importers: Facebook Marketplace, Reverb, eBay UK, and Gumtree — or enter details manually below."
                }

            if new_item:
                self._upsert_deal_to_json(new_item)
                self._send_json({"status": "ok", "item": new_item})
                return

            resp_err = {"status": "error", "code": "IMPORT_FAILED", "message": "Could not extract listing details. Enter details manually below."}
            if err_info:
                resp_err.update(err_info)
            self._send_json(resp_err)
        except Exception as ex:
            self._send_json({
                "status": "error",
                "code": "IMPORT_EXCEPTION",
                "message": f"Import failed ({ex}). Enter the listing details manually below."
            })

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        try:
            if self.path.startswith("/api/import_fb") or self.path.startswith("/api/import_deal"):
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw_body = self.rfile.read(min(length, 1024 * 1024)).decode("utf-8", errors="ignore") if length > 0 else "{}"
                payload = json.loads(raw_body) if raw_body.strip() else {}
                if not isinstance(payload, dict):
                    payload = {}
                self._handle_import_request(payload)
                return
            self._send_json({"status": "error", "code": "NOT_FOUND", "message": "Endpoint not found"}, status=404)
        except Exception as e:
            self._send_json({
                "status": "error",
                "code": "BAD_REQUEST",
                "message": f"Invalid import payload ({e}). Enter details manually below."
            })

    def do_GET(self):
        try:
            if self.path.startswith("/api/import_fb") or self.path.startswith("/api/import_deal"):
                parsed_url = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed_url.query)
                payload = {
                    "url": qs.get("url", [""])[0],
                    "location": qs.get("location", [""])[0],
                    "title": qs.get("title", [""])[0],
                    "price": qs.get("price", [None])[0],
                    "manual": qs.get("manual", [""])[0].lower() in ("1", "true", "yes"),
                    "has_case": qs.get("has_case", ["true"])[0],
                    "has_repair": qs.get("has_repair", ["false"])[0],
                }
                self._handle_import_request(payload)
                return

            if self.path.startswith("/api/remove_deal"):
                parsed_url = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed_url.query)
                rem_id = qs.get("id", [""])[0].strip()
                if rem_id:
                    bl_path = os.path.join(os.path.dirname(__file__), "blocklist.json")
                    bl = list(load_blocklist())
                    if rem_id not in bl:
                        bl.append(rem_id)
                    with open(bl_path, "w", encoding="utf-8") as f:
                        json.dump(bl, f, indent=2)
                    filepath = os.path.join(os.path.dirname(__file__), "deals.json")
                    if os.path.exists(filepath):
                        with open(filepath, "r", encoding="utf-8-sig") as f:
                            deals = json.load(f)
                        deals = [d for d in deals if str(d.get("id", "")) != rem_id]
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(deals, f, indent=2)
                    res_body = json.dumps({"status": "ok", "removed": rem_id}).encode("utf-8")
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
                        live_deals, fb_refreshed = harvest_all_sources(return_meta=True)
                        enriched = enrich_listings(live_deals)
                        combined = _save_combined_deals(enriched, fb_refreshed=fb_refreshed)
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
            live_deals, fb_refreshed = harvest_all_sources(return_meta=True)
            enriched = enrich_listings(live_deals)
            combined = _save_combined_deals(enriched, fb_refreshed=fb_refreshed)
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
    "wildwire": "YO8 8LZ",          # Selby, North Yorkshire (35 miles from Hull HQ!)
    "rich tone": "S9 3RP",          # Sheffield (60 miles from Hull HQ!)
    "coda music": "SG6 2AL",        # Hertfordshire
    "peach": "CO4 9QP",             # Colchester
    "guitar village": "GU9 7ND",    # Farnham
    "andertons": "GU1 4RF",         # Guildford
    "atb guitars": "GL50 1TA",      # Cheltenham (near Somerset!)
    "wunjo": "WC2H 8LA",            # London
    "denmark street": "WC2H 8LP",   # London
    "no.tom": "WC2H 8LP",           # London
    "regent sounds": "WC2H 8LA",    # London
    "soundaffects": "PR7 1NY",      # Ormskirk, Lancs
    "sound affects": "PR7 1NY",     # Ormskirk, Lancs
    "guitarguitar": "B5 4RB",       # Birmingham
    "fair deal": "B5 4SL",          # Birmingham
    "jordan": "LE3 8HN",            # Leicester (Glenfield)
    "squealing pig": "NG9 8AR",     # Stapleford, Nottingham
    "gas station": "TA1 5LU",       # Taunton, Somerset
    "58 sound": "AL1 1NG",          # St Albans, Herts
    "motomusic": "CF10 5DR",        # Cardiff
    "in bloom": "LS1 1AA",          # Leeds, West Yorkshire
    "new kings road": "SW6 4SG",    # London
    "rolly": "CV47 0AA",            # Southam, Warwickshire
    "guitars in the attic": "NG18 1AA", # Mansfield, Notts
    "south wales": "CF10 1AA",      # South Wales
    "bonners": "BN22 9BH",          # Eastbourne
    "reidys": "BB7 9YE",            # Whalley, Lancs
    "rainbow music": "CA3 8UU",     # Carlisle
    "music street": "PE29 3NW",     # Huntingdon
    "world guitars": "GL10 2BG"     # Stonehouse, Glos
}

def harvest_live_reverb():
    """Fetches 100% REAL, LIVE, active UK Gibson ES-335 & ES-345 listings directly via UK live feed."""
    print("🔍 Harvesting live UK listings via Reverb UK Live Feed...")
    queries = ["gibson es-335", "gibson es-345", "orville 335", "heritage h-535", "tokai 335"]
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

                        # Systematically resolve real UK town & coords from Reverb API (cached per shop in deals.db)
                        loc_data = it.get("location", {}) or {}
                        locality = (loc_data.get("locality") or "").strip()
                        region = (loc_data.get("region") or "ENG").strip()
                        if locality:
                            postcode, resolved_coords = geocode_uk_town(locality, region)
                        else:
                            locality, postcode, resolved_coords = resolve_reverb_shop_location(shop_name, item_id, headers)

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
                            "coords": resolved_coords,
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
    if os.environ.get("APIFY_TOKEN"):
        cfg.setdefault("apify", {})["token"] = os.environ["APIFY_TOKEN"].strip()
    if os.environ.get("APIFY_FB_ACTOR_ID"):
        cfg.setdefault("apify", {})["actor_id"] = os.environ["APIFY_FB_ACTOR_ID"].strip()
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

def _parse_ebay_browse_item(it, min_price=600.0, fallback_url=""):
    """Normalizes an eBay Browse API item object into a scanner raw listing dict."""
    item_id = it.get("itemId")
    if not item_id:
        return None

    title = (it.get("title") or "").strip()
    title_lower = title.lower()
    if any(bad in title_lower for bad in ["case only", "pickguard", "wiring", "pickups only", "strap", "knobs", "epiphone", "love rock", "goldstar", "breezysound", "uls129", "lc-156", "ls115", "ls75"]):
        if "elitist" not in title_lower:
            return None

    price_obj = it.get("price") or it.get("currentBidPrice") or {}
    price_val = price_obj.get("value", "0")
    try:
        price = round(float(price_val), 2)
    except (ValueError, TypeError):
        return None
    if price <= 0 or price < min_price:
        return None

    buying_opts = it.get("buyingOptions") or []
    is_auction = ("AUCTION" in buying_opts) and ("FIXED_PRICE" not in buying_opts)

    brand = detect_brand_tier(title)
    if not is_valid_335_model(title, brand):
        return None

    web_url = it.get("itemWebUrl") or fallback_url
    image_url = (it.get("image") or {}).get("imageUrl", "")
    seller_name = (it.get("seller") or {}).get("username", "eBay UK Seller")
    loc_info = it.get("itemLocation", {}) or {}
    raw_pc = (loc_info.get("postalCode") or "").strip()
    city = (loc_info.get("city") or "").strip()
    if raw_pc:
        postcode = raw_pc.replace("*", "").strip() or resolve_uk_location_postcode(city, seller_name)
    else:
        postcode = resolve_uk_location_postcode(city, seller_name)

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

    return {
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
        "is_auction": is_auction,
        "buying_options": buying_opts,
        "shipping_available": shipping_available,
        "shipping_cost": shipping_cost,
        "shipping_carrier": shipping_carrier,
        "published_at": it.get("itemCreationDate")
    }

def parse_ebay_single(url):
    """Fetches a single eBay UK listing via Browse API get_item_by_legacy_id and enriches it."""
    m = re.search(r'/itm/(?:[^/]+/)?(\d{9,15})', url)
    if not m:
        return None
    legacy_id = m.group(1)
    cfg = load_config()
    ebay_cfg = cfg.get("ebay", {})
    cid = ebay_cfg.get("client_id", "")
    csec = ebay_cfg.get("client_secret", "")
    if not cid or "YOUR_EBAY" in cid:
        return None
    token = get_ebay_oauth_token(cid, csec)
    if not token:
        return None

    api_url = f"https://api.ebay.com/buy/browse/v1/item/get_item_by_legacy_id?legacy_item_id={legacy_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "Accept": "application/json"
    }
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            it = json.loads(resp.read().decode('utf-8'))
        raw_item = _parse_ebay_browse_item(it, min_price=0.0, fallback_url=url)
        if not raw_item:
            return None
        enriched = enrich_listings([raw_item])
        return enriched[0] if enriched else None
    except Exception as e:
        print(f"Error parsing single eBay listing {url}: {e}")
        return None

def harvest_live_ebay(client_id, client_secret):
    """Fetches real live Gibson ES-335 & ES-345 items from the official eBay Browse API (eBay UK)."""
    token = get_ebay_oauth_token(client_id, client_secret)
    if not token:
        return []

    print("\n🔍 Harvesting live UK items from official eBay Browse API...")
    queries = [
        "gibson es-335", "gibson 335",
        "gibson es-345", "gibson 345",
        "orville 335",
        "heritage h-535", "heritage 535",
        "tokai 335", "tokai es"
    ]
    harvested = []
    seen_ids = set()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        "Accept": "application/json"
    }

    page_size = 200
    max_offset = 600

    for q in queries:
        offset = 0
        while offset < max_offset:
            params = {
                "q": q,
                "category_ids": "3858", # Guitars & Basses (includes 33034 Electric Guitars + semi-hollows)
                "filter": "price:[600..],priceCurrency:GBP,itemLocationCountry:GB,buyingOptions:{FIXED_PRICE|AUCTION}",
                "limit": str(page_size),
                "offset": str(offset)
            }
            url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?{urllib.parse.urlencode(params)}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                summaries = data.get("itemSummaries", [])
                if not summaries:
                    break
                for it in summaries:
                    item_id = it.get("itemId")
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    parsed = _parse_ebay_browse_item(it, min_price=600.0)
                    if not parsed:
                        continue

                    harvested.append(parsed)
                    auction_tag = " [AUCTION]" if parsed.get("is_auction") else ""
                    print(f"  ✓ Live [eBay UK]{auction_tag}: {parsed['title']} (£{parsed['price']}) - {parsed['source']}")

                total = int(data.get("total") or 0)
                offset += len(summaries)
                if offset >= total or len(summaries) < page_size:
                    break
            except Exception as e:
                print(f"  ✗ Error querying eBay for '{q}' (offset={offset}): {e}")
                break

    print(f"Found {len(harvested)} live guitars on eBay UK!")
    return harvested

INDIE_UK_SHOPS = [
    {"slug": "jordan", "name": "Jordan Guitars", "base": "https://jordanguitars.co.uk", "type": "shopify", "postcode": "LE3 8HN", "city": "Leicester", "shipping_cost": 0.0, "shipping_carrier": "Free Insured UK Delivery"},
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
    queries = ["gibson 335", "gibson 345", "orville 335", "heritage 535", "tokai es"]

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
                        if not any(m in tlow for m in ["335", "345", "535", "es-1", "es-2", "es1", "es60", "es70", "es80", "es90", "es120", "es135", "es156", "es160", "es166"]):
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
                        if not any(m in tlow for m in ["335", "345", "535", "es-1", "es-2", "es1", "es60", "es70", "es80", "es90", "es120", "es135", "es156", "es160", "es166"]):
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

def harvest_live_facebook_apify(token, actor_id="apify/facebook-marketplace-scraper", results_limit=5, max_charge_usd=0.16):
    """Throttled UK Facebook Marketplace sweep via Apify (capped to stay inside the $5/mo free tier)."""
    print("\n📘 Harvesting UK Facebook Marketplace listings via Apify (daily throttled sweep)...")
    search_urls = [
        "https://www.facebook.com/marketplace/hull/search/?query=gibson%20335&minPrice=600",
        "https://www.facebook.com/marketplace/newcastle/search/?query=gibson%20335&minPrice=600",
        "https://www.facebook.com/marketplace/bristol/search/?query=gibson%20335&minPrice=600",
        "https://www.facebook.com/marketplace/manchester/search/?query=gibson%20335&minPrice=600",
        "https://www.facebook.com/marketplace/london/search/?query=gibson%20335&minPrice=600",
    ]

    actor_slug = (actor_id or "apify/facebook-marketplace-scraper").strip().replace("/", "~")
    safe_slug = urllib.parse.quote(actor_slug, safe="~-._")
    endpoint = (
        f"https://api.apify.com/v2/acts/{safe_slug}/run-sync-get-dataset-items"
        f"?timeout=120&maxTotalChargeUsd={float(max_charge_usd):.2f}"
    )

    payload = json.dumps({
        "startUrls": [{"url": u} for u in search_urls],
        "resultsLimit": int(results_limit),
        "includeListingDetails": False,
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=145) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        raw_items = json.loads(body) if body else []
        if not isinstance(raw_items, list):
            raw_items = []
    except urllib.error.HTTPError as e:
        code = e.code
        e.close()
        if code == 402:
            print("  ⚠️ Apify free-tier usage limit reached (HTTP 402) — backing off 23h and preserving cached FB listings.")
            _set_scan_state("fb_apify_last_run_at", datetime.now(timezone.utc).isoformat())
        else:
            print(f"  ✗ Error harvesting Facebook Marketplace via Apify (HTTP {code}) — preserving cached FB listings.")
        return [], False
    except Exception as e:
        print(f"  ✗ Error harvesting Facebook Marketplace via Apify ({e}) — preserving cached FB listings.")
        return [], False

    harvested = []
    seen_ids = set()
    bad_terms = ["case only", "pickguard", "wiring", "pickups only", "strap", "knobs", "gig bag only", "epiphone"]

    for it in raw_items:
        if not isinstance(it, dict) or it.get("error") or it.get("errorDescription"):
            continue

        raw_id = str(it.get("id") or "").strip()
        item_id = raw_id if raw_id.isdigit() else _extract_fb_item_id(it.get("listingUrl") or it.get("url") or "")
        if not item_id or item_id in seen_ids:
            continue

        # Ensure GBP UK pricing
        lp = it.get("listing_price") or it.get("listingPrice") or it.get("price") or {}
        currency = str(lp.get("currency") or "").upper() if isinstance(lp, dict) else ""
        fmt_amt = str(lp.get("formatted_amount") or "") if isinstance(lp, dict) else str(lp or "")
        if currency and currency != "GBP":
            continue
        if not currency and fmt_amt and any(sym in fmt_amt for sym in ("$", "€", "CA$", "A$", "USD", "EUR")):
            continue

        canonical_url = f"https://www.facebook.com/marketplace/item/{item_id}/"
        raw_item, map_err = _map_apify_fb_item_to_raw(it, canonical_url, item_id, user_location="")
        if map_err or not raw_item:
            continue

        if float(raw_item.get("price") or 0) < 600:
            continue

        tlow = (raw_item.get("title") or "").lower()
        if any(b in tlow for b in bad_terms) and "elitist" not in tlow:
            continue
        if not is_valid_335_model(raw_item.get("title", ""), raw_item.get("brand_tier", "")):
            continue

        coords = raw_item.get("coords")
        if coords:
            lat, lng = coords
            if not (49.8 <= lat <= 61.0 and -8.5 <= lng <= 2.0):
                continue

        seen_ids.add(item_id)
        raw_item["auto_harvested_fb"] = True
        raw_item["source_type"] = "facebook"
        harvested.append(raw_item)
        print(f"  ✓ Live [Facebook UK]: {raw_item['title']} (£{raw_item['price']}) - {raw_item['source']}")

    _set_scan_state("fb_apify_last_run_at", datetime.now(timezone.utc).isoformat())
    print(f"Found {len(harvested)} valid UK guitars on Facebook Marketplace (from {len(raw_items)} raw Apify items)!")
    return harvested, True


def _save_combined_deals(enriched, fb_refreshed=False):
    """Merges preserved Gumtree, manual & throttled Facebook Marketplace listings into deals.json."""
    filepath = os.path.join(os.path.dirname(__file__), "deals.json")
    blocked_ids = load_blocklist()
    saved_imports = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                prev = json.load(f)
                seen_ids = {d.get("id") for d in enriched}
                for d in prev:
                    did = str(d.get("id", ""))
                    if did in seen_ids or did in blocked_ids:
                        continue
                    if did.startswith(("gumtree_", "manual_")):
                        saved_imports.append(d)
                    elif did.startswith("fb_"):
                        if not d.get("auto_harvested_fb") or not fb_refreshed:
                            if d.get("postcode") == "UK (TBC)" or not d.get("coords"):
                                m_loc = re.search(r'\(([^)]+)\)', str(d.get("source", "")))
                                if m_loc:
                                    pc_fix, coords_fix, _ = _resolve_uk_location_smart(m_loc.group(1))
                                    if coords_fix:
                                        d["postcode"] = pc_fix
                                        d["coords"] = coords_fix
                                        fixed_list = enrich_listings([d], skip_model_filter=True)
                                        if fixed_list:
                                            d = fixed_list[0]
                            saved_imports.append(d)
        except Exception:
            pass
    combined_deals = saved_imports + enriched
    export_deals_json(combined_deals)
    return combined_deals


def harvest_all_sources(force_fb=False, return_meta=False):
    """Harvests live listings from Independent UK Shops + Reverb UK + eBay UK + throttled daily Facebook UK."""
    deals = harvest_live_indie_shops()
    deals.extend(harvest_live_reverb())
    cfg = load_config()
    ebay_cfg = cfg.get("ebay", {})
    if ebay_cfg.get("enabled") and ebay_cfg.get("client_id") and "YOUR_EBAY" not in ebay_cfg.get("client_id"):
        ebay_deals = harvest_live_ebay(ebay_cfg["client_id"], ebay_cfg.get("client_secret", ""))
        deals.extend(ebay_deals)

    fb_refreshed = False
    apify_cfg = cfg.get("apify") or {}
    apify_token = (apify_cfg.get("token") or "").strip()
    if apify_token and "YOUR_APIFY" not in apify_token.upper() and apify_cfg.get("daily_sweep_enabled", True):
        interval_hours = float(apify_cfg.get("sweep_interval_hours", 23))
        if should_run_fb_apify_sweep(interval_hours=interval_hours, force=force_fb):
            actor_id = (apify_cfg.get("actor_id") or "apify/facebook-marketplace-scraper").strip()
            results_limit = int(apify_cfg.get("results_limit", 5))
            max_charge = float(apify_cfg.get("max_total_charge_usd", 0.16))
            fb_deals, fb_ok = harvest_live_facebook_apify(
                apify_token,
                actor_id=actor_id,
                results_limit=results_limit,
                max_charge_usd=max_charge,
            )
            if fb_ok:
                deals.extend(fb_deals)
                fb_refreshed = True
        else:
            elapsed, remaining = _get_fb_sweep_timing(interval_hours)
            if elapsed is not None:
                print(f"\n⏭️  Facebook Marketplace daily sweep skipped (last run {elapsed:.1f}h ago; next run in {remaining:.1f}h).")

    if return_meta:
        return deals, fb_refreshed
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

    # Harvest from all live sources (Independent UK Shops + Reverb UK + eBay UK + throttled daily Facebook UK)
    all_live_deals, fb_refreshed = harvest_all_sources(return_meta=True)

    print(f"\nTotal live active UK guitars: {len(all_live_deals)}")
    enriched = enrich_listings(all_live_deals)

    combined_deals = _save_combined_deals(enriched, fb_refreshed=fb_refreshed)
    check_and_send_alerts(combined_deals)

    if "--serve" in sys.argv:
        port = int(os.environ.get("PORT", 8000))
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=")[1])
        start_server(port)

if __name__ == "__main__":
    main()
