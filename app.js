// Gibson ES-335 Deal Radar Client Application
// Dual Hub Travel Engine: Hull HQ & Somerset
// Valuations, Fuel & Travel Math, Shipping vs Driving Comparisons, Dexterity Filters

let currentHub = "Hull";
let rawListings = [];
let filteredBrand = "all";
let filteredSource = "all"; // "all" | "indie" | "ebay" | "reverb" | "gumtree"
let filteredActivity = "all"; // "all" | "new" | "drops" | "stale"
let searchQuery = "";
let filteredDexterity = "right"; // "right" | "all" | "left"
let viewMode = "grid"; // "grid" | "table"
let showShortlistOnly = false;
let lastRenderedListings = [];
let ukMapInstance = null;
let ukMapLayerGroup = null;

// Persisted Shortlist & Hidden Sets (localStorage)
let shortlistedIds = new Set(JSON.parse(localStorage.getItem("es335_shortlist") || "[]"));
let hiddenIds = new Set(JSON.parse(localStorage.getItem("es335_hidden") || "[]"));

function saveUserSets() {
  localStorage.setItem("es335_shortlist", JSON.stringify([...shortlistedIds]));
  localStorage.setItem("es335_hidden", JSON.stringify([...hiddenIds]));
  updateShortlistHiddenUI();
}

function updateShortlistHiddenUI() {
  const slCount = document.getElementById("shortlistCount");
  if (slCount) slCount.textContent = shortlistedIds.size;
  const hdBtn = document.getElementById("restoreHiddenBtn");
  const hdCount = document.getElementById("hiddenCount");
  if (hdCount) hdCount.textContent = hiddenIds.size;
  if (hdBtn) {
    if (hiddenIds.size > 0) hdBtn.classList.remove("hidden");
    else hdBtn.classList.add("hidden");
  }
}

function toggleShortlist(id) {
  if (shortlistedIds.has(id)) {
    shortlistedIds.delete(id);
    showToast("Removed from Shortlist");
  } else {
    shortlistedIds.add(id);
    showToast("Saved to Shortlist");
  }
  saveUserSets();
  renderListings();
}

function hideListing(id) {
  hiddenIds.add(id);
  shortlistedIds.delete(id);
  saveUserSets();
  showToast("Listing hidden (click Restore anytime)");
  renderListings();
}

function restoreHiddenListings() {
  hiddenIds.clear();
  saveUserSets();
  showToast("All hidden listings restored");
  renderListings();
}

// Base coordinates for hubs
const HUBS = {
  Hull: { name: "Hull HQ", postcode: "HU1 1AA", lat: 53.7457, lng: -0.3367, maxHours: 3.0 },
  Somerset: { name: "Somerset Base", postcode: "TA8 1PE", lat: 51.2383, lng: -2.9972, maxHours: 1.5 }
};

// UK Imperial gallons conversion factor
const LITRES_PER_GALLON = 4.54609;

// Fallback seed data in case file is opened directly as file:// or API is offline
const FALLBACK_LISTINGS = [
  {
    "id": "peach_1995_dot",
    "title": "Gibson ES-335 Dot Reissue 1995 Sunburst (Good Wood Era)",
    "price": 1950.0,
    "source": "Peach Guitars",
    "url": "https://www.peachguitars.com/guitars/pre-owned-guitars/?search=335",
    "image_url": "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600&auto=format&fit=crop",
    "postcode": "CO4 9QP",
    "coords": [51.9056, 0.9419],
    "brand_tier": "Gibson USA Standard",
    "year": 1995,
    "era_badge": "⭐ GOOD WOOD (90s)",
    "era_boost": 1.0,
    "era_notes": "Honduran mahogany, dark rosewood board, early '57 Classic PAFs.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 0.0,
    "shipping_carrier": "Free Insured Next-Day UK Delivery"
  },
  {
    "id": "coda_2016_memphis",
    "title": "Gibson Memphis ES-335 2016 Figured Cherry",
    "price": 2095.0,
    "source": "Coda Music",
    "url": "https://www.coda-music.com/catalogsearch/result/?q=gibson+335",
    "image_url": "https://images.unsplash.com/photo-1564186763535-ebb21ef5277f?w=600&auto=format&fit=crop",
    "postcode": "SG6 2AL",
    "coords": [51.9772, -0.2285],
    "brand_tier": "Gibson USA Standard",
    "year": 2016,
    "era_badge": "🎖️ MEMPHIS PEAK (13-18)",
    "era_boost": 0.5,
    "era_notes": "Adirondack spruce quartered bracing, unpotted MHS PAF pickups.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 15.0,
    "shipping_carrier": "Seller UK Postage: £15.00"
  },
  {
    "id": "jordan_2022_original",
    "title": "Gibson ES-335 Original Collection 2022 Vintage Burst",
    "price": 2199.0,
    "source": "Jordan Guitars",
    "url": "https://jordanguitars.co.uk/search?type=product&q=335",
    "image_url": "https://images.unsplash.com/photo-1525201548942-d8732f6617a0?w=600&auto=format&fit=crop",
    "postcode": "NR1 1AA",
    "coords": [52.6284, 1.2996],
    "brand_tier": "Gibson USA Standard",
    "year": 2022,
    "era_badge": "🛡️ MODERN NASHVILLE",
    "era_boost": 0.0,
    "era_notes": "Calibrated T-Type humbuckers, hand-wired with Orange Drop caps.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 0.0,
    "shipping_carrier": "Free Insured Next-Day UK Delivery"
  },
  {
    "id": "bonners_lh_cherry",
    "title": "Gibson ES-335 (Left-handed); Sixties Cherry",
    "price": 2665.83,
    "source": "Bonners Music",
    "url": "https://reverb.com/item/87073449-gibson-es-335-left-handed-sixties-cherry",
    "image_url": "https://rvb-img.reverb.com/i/s--AYVG1P_t--/quality=medium-low,height=800,width=800,fit=contain/fcb98142-39b5-4324-b331-d41f563f8e06.jpg",
    "postcode": "B1 1AA",
    "coords": [52.4772, -1.8986],
    "brand_tier": "Gibson USA Standard",
    "year": 2021,
    "era_badge": "🛡️ MODERN NASHVILLE",
    "era_boost": 0.0,
    "era_notes": "Authentic Left-handed factory spec. Calibrated T-Types, Grover Rotomatics.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": true,
    "shipping_available": true,
    "shipping_cost": 0.0,
    "shipping_carrier": "Free Insured Next-Day UK Delivery"
  },
  {
    "id": "private_obg_1993",
    "title": "Orville by Gibson ES-335 Dot 1993 Terada MIJ (Nitro & '57 Classics)",
    "price": 1200.0,
    "source": "Reverb UK Private",
    "url": "https://reverb.com/uk/marketplace?query=orville%20by%20gibson%20335",
    "image_url": "https://images.unsplash.com/photo-1516924962500-2b4b3b99ea02?w=600&auto=format&fit=crop",
    "postcode": "LS1 1AA",
    "coords": [53.7960, -1.5478],
    "brand_tier": "Orville by Gibson",
    "year": 1993,
    "era_badge": "⭐ GOOD WOOD (90s)",
    "era_boost": 1.0,
    "era_notes": "Original nitro finish, fret-edge binding, USA pickups from factory.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 30.0,
    "shipping_carrier": "Tracked & Insured Courier (£30)"
  },
  {
    "id": "gumtree_bozeman_2002",
    "title": "Gibson ES-335 Dot (2002 Bozeman Plant MT USA)",
    "price": 1650.0,
    "source": "Gumtree (Liverpool)",
    "url": "https://www.gumtree.com/p/guitar-instrument/gibson-es335-/1511012969",
    "image_url": "https://img.gumtree.com/ePR8PyKf84wPHx7_RYmEag/d2aea4753ec64a9f8f_5b50cb47b960/86",
    "postcode": "L1 8JQ",
    "coords": [53.4045, -2.9871],
    "brand_tier": "Gibson USA Standard",
    "year": 2002,
    "era_badge": "🛡️ 2002 MODEL",
    "era_boost": 0.0,
    "era_notes": "Bozeman USA plant production, fitted with Gibson TP6 fine tuner, Kluson waffle backs.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": false,
    "shipping_cost": 0.0,
    "shipping_carrier": "Collection in Person Only"
  },
  {
    "id": "private_heritage_535",
    "title": "Heritage H-535 Semi-Hollow 2018 Kalamazoo Sunburst",
    "price": 1495.0,
    "source": "Gumtree Bristol",
    "url": "https://www.gumtree.com/search?search_category=guitar&q=heritage+535",
    "image_url": "https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=600&auto=format&fit=crop",
    "postcode": "BS1 1AA",
    "coords": [51.4545, -2.5879],
    "brand_tier": "Heritage H-535",
    "year": 2018,
    "era_badge": "📅 2018",
    "era_boost": 0.0,
    "era_notes": "Seymour Duncan '59 set, built in historic 225 Parsons St factory.",
    "has_case": true,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 25.0,
    "shipping_carrier": "Insured Courier (£25)"
  },
  {
    "id": "inbloom_2011_player",
    "title": "Gibson ES-335 Dot 2011 Cherry Red (Headstock Smile Repair)",
    "price": 1450.0,
    "source": "In Bloom Guitars",
    "url": "https://inbloomguitars.co.uk/search?q=335",
    "image_url": "https://images.unsplash.com/photo-1564186763535-ebb21ef5277f?w=600&auto=format&fit=crop",
    "postcode": "RG1 1DN",
    "coords": [51.4543, -0.9781],
    "brand_tier": "Gibson USA Standard",
    "year": 2011,
    "era_badge": "📅 2011",
    "era_boost": 0.0,
    "era_notes": "Professional luthier cleat & refinish. Plays clean with rock solid stability.",
    "has_case": true,
    "has_repair": true,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 25.0,
    "shipping_carrier": "Insured 24h Courier (£25)"
  },
  {
    "id": "tokai_es160_2017",
    "title": "Tokai Japan ES-160 Vintage Natural Flame (Gig Bag Only)",
    "price": 1050.0,
    "source": "Guitar Village",
    "url": "https://guitarvillage.co.uk/?s=tokai+335&post_type=product",
    "image_url": "https://images.unsplash.com/photo-1525201548942-d8732f6617a0?w=600&auto=format&fit=crop",
    "postcode": "GU9 7ND",
    "coords": [51.2141, -0.7984],
    "brand_tier": "Tokai Japan",
    "year": 2017,
    "era_badge": "📅 2017",
    "era_boost": 0.0,
    "era_notes": "PAF-Vintage MK2 pickups, bone nut, lacquer. Comes in padded gig bag.",
    "has_case": false,
    "has_repair": false,
    "is_left_handed": false,
    "shipping_available": true,
    "shipping_cost": 25.0,
    "shipping_carrier": "Insured 24h Courier (£25)"
  }
];

// Distance math (Haversine in miles)
function haversineMiles(lat1, lon1, lat2, lon2) {
  const R = 3958.8;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Compute dynamic metrics based on sliders & current hub
function computeListingMetrics(listing, mpg, fuelPrice, maxDriveHours) {
  const hub = HUBS[currentHub];
  let oneWayMiles = 0;
  let roundTripMiles = 0;
  let driveHours = 0;
  let fuelCost = 0;

  if (listing.coords && listing.coords.length === 2) {
    const direct = haversineMiles(hub.lat, hub.lng, listing.coords[0], listing.coords[1]);
    oneWayMiles = Math.round(direct * 1.25); // 1.25 UK road network winding factor
    roundTripMiles = oneWayMiles * 2;
    driveHours = parseFloat((oneWayMiles / 50.0).toFixed(1)); // 50mph UK average road speed
    
    const gallons = roundTripMiles / mpg;
    const litres = gallons * LITRES_PER_GALLON;
    fuelCost = Math.round(litres * fuelPrice);
  }

  // Case Penalty (£150 if no hard case included)
  const casePenalty = listing.has_case ? 0 : 150;

  // Road Trip Landed Cost
  const landedDriveCost = Math.round(listing.price + fuelCost + casePenalty);

  // Shipping / Delivery Parameters (Scraped directly from seller's listing)
  const shippingAvailable = Boolean(listing.shipping_available);
  const shippingCost = listing.shipping_cost !== undefined ? Number(listing.shipping_cost) : 0.0;
  const shippingCarrier = listing.shipping_carrier || (shippingAvailable ? (shippingCost === 0 ? "Seller Free UK Delivery" : `Seller Postage: £${shippingCost.toFixed(2)}`) : "Collection in Person Only");
  const landedShipCost = shippingAvailable ? Math.round(listing.price + shippingCost + casePenalty) : null;

  // Cheaper Option Comparison & Savings
  let cheaperMethod = "drive";
  let cheaperMethodLabel = "Road Trip";
  let cheaperText = "";
  let cheaperCalloutClass = "";
  let cheaperIcon = "car";
  let bestLandedCost = landedDriveCost;
  let savings = 0;

  if (shippingAvailable) {
    if (fuelCost < shippingCost) {
      cheaperMethod = "drive";
      savings = Math.round(shippingCost - fuelCost);
      cheaperMethodLabel = "Road Trip";
      cheaperText = `Road trip saves £${savings} vs £${shippingCost.toFixed(2)} postage (+ in-person check)`;
      cheaperCalloutClass = "bg-primary/10 text-primary border border-primary/25";
      cheaperIcon = "car";
      bestLandedCost = landedDriveCost;
    } else if (shippingCost < fuelCost) {
      cheaperMethod = "ship";
      savings = Math.round(fuelCost - shippingCost);
      cheaperMethodLabel = "Seller Delivery";
      cheaperText = `Delivery (${shippingCost === 0 ? 'FREE' : '£' + shippingCost.toFixed(2)}) saves £${savings} vs petrol`;
      cheaperCalloutClass = "bg-emerald-500/10 text-emerald-300 border border-emerald-500/25";
      cheaperIcon = "package";
      bestLandedCost = landedShipCost;
    } else {
      cheaperMethod = "equal";
      savings = 0;
      cheaperMethodLabel = "Drive or Deliver";
      cheaperText = `Identical cost (£${fuelCost}) — road trip allows in-person testing`;
      cheaperCalloutClass = "bg-secondary text-foreground/80 border border-border";
      cheaperIcon = "scale";
      bestLandedCost = landedDriveCost;
    }
  } else {
    cheaperMethod = "drive_only";
    savings = 0;
    cheaperMethodLabel = "Collection Only";
    cheaperText = `Collection in person only (no seller delivery listed)`;
    cheaperCalloutClass = "bg-secondary text-muted-foreground border border-border";
    cheaperIcon = "car";
    bestLandedCost = landedDriveCost;
  }

  // True Landed Cost is defined as the best (most economical) route
  const trueLandedCost = bestLandedCost;

  // Left-Handed Detection
  const isLefty = (listing.is_left_handed !== undefined)
    ? Boolean(listing.is_left_handed)
    : /\b(left[\s-]?hand(ed)?|lh|lefty|southpaw)\b/i.test(`${listing.title} ${listing.era_notes || ''}`);

  // Grade Evaluation (shadcn Vintage Sunburst Badges)
  let grade = "B";
  let gradePillClass = "bg-secondary/95 text-foreground border border-border font-semibold";
  let verdict = "Grade B • Fair Buy";
  let notes = "Good candidate for negotiation.";

  // Exceeds travel cap check (allow up to 4.5h for Holy Grail steals)
  const isGrailCandidate = (listing.brand_tier.includes("Gibson USA") && (trueLandedCost <= 2000 || (trueLandedCost <= 2050 && (listing.era_boost || 0) >= 1.0)));
  const effectiveMaxHours = isGrailCandidate ? 4.5 : maxDriveHours;

  if (driveHours > effectiveMaxHours && !shippingAvailable) {
    grade = "C";
    gradePillClass = "bg-background/90 text-muted-foreground border border-border font-medium";
    verdict = "Too Far";
    notes = `Drive time (${driveHours}h) exceeds the current ${effectiveMaxHours}h radius limit, and seller does not offer shipping.`;
  } else if (listing.has_repair) {
    if (trueLandedCost <= 1450) {
      grade = "B+";
      gradePillClass = "bg-primary text-primary-foreground font-semibold";
      verdict = "Fair Repaired Player";
      notes = "Priced well for a repaired neck (−35% market value). Great player grade.";
    } else {
      grade = "C";
      gradePillClass = "bg-cherry/90 text-white border border-cherry font-semibold";
      verdict = "Caution • Overpriced Repair";
      notes = `Repaired guitar landed at £${trueLandedCost}; above £1,450 safe threshold.`;
    }
  } else if (listing.brand_tier.includes("Gibson USA")) {
    if (trueLandedCost < 2000 || (trueLandedCost <= 2050 && (listing.era_boost || 0) >= 1.0)) {
      grade = "A+";
      gradePillClass = "bg-emerald-500 text-background font-bold shadow-sm";
      verdict = "Grade A+ • Holy Grail";
      notes = `True landed at £${trueLandedCost}. Rare sub-£2k threshold for authentic Gibson USA ES-335.`;
    } else if (trueLandedCost <= 2150) {
      grade = "A";
      gradePillClass = "bg-primary text-primary-foreground font-bold shadow-sm";
      verdict = "Grade A • Prime Target";
      notes = `Landed at £${trueLandedCost}. Below the £2,200 standard market floor.`;
    } else if (trueLandedCost <= 2350) {
      grade = "B+";
      gradePillClass = "bg-card/95 text-foreground border border-primary/40 font-semibold";
      verdict = "Grade B+ • Solid Buy";
      notes = "Fair market price. Very solid pick.";
    } else {
      grade = "B";
      gradePillClass = "bg-background/90 text-muted-foreground border border-border font-medium";
      verdict = "Grade B • Make Offer";
      notes = "Slightly high for travel pickup. Negotiate a travel discount.";
    }
  } else if (listing.brand_tier.includes("Orville")) {
    if (trueLandedCost <= 1250) {
      grade = "A+";
      gradePillClass = "bg-emerald-500 text-background font-bold";
      verdict = "Grade A+ • Orville Steal";
      notes = `Landed at £${trueLandedCost}. Top Terada/FujiGen build at a steal price.`;
    } else if (trueLandedCost <= 1500) {
      grade = "A";
      gradePillClass = "bg-primary text-primary-foreground font-bold";
      verdict = "Grade A • Fair Orville";
      notes = "Great alternative to modern Gibson with vintage specs.";
    } else {
      grade = "B";
      gradePillClass = "bg-background/90 text-muted-foreground border border-border font-medium";
      verdict = "Grade B";
      notes = "Over £1,500 approaches Gibson USA territory.";
    }
  } else if (listing.brand_tier.includes("Heritage")) {
    if (trueLandedCost <= 1550) {
      grade = "A+";
      gradePillClass = "bg-emerald-500 text-background font-bold";
      verdict = "Grade A+ • Kalamazoo Steal";
      notes = "Built in historic Gibson Parsons St factory by original luthiers.";
    } else {
      grade = "A";
      gradePillClass = "bg-primary text-primary-foreground font-bold";
      verdict = "Grade A • Kalamazoo Craft";
      notes = "Outstanding build quality and Seymour Duncan pickups.";
    }
  } else if (listing.brand_tier.includes("Tokai")) {
    if (trueLandedCost <= 1100) {
      grade = "A+";
      gradePillClass = "bg-emerald-500 text-background font-bold";
      verdict = "Grade A+ • Tokai MIJ";
      notes = "Exceptional Japanese semi-hollow construction.";
    } else {
      grade = "A";
      gradePillClass = "bg-primary text-primary-foreground font-bold";
      verdict = "Grade A • Fair Tokai";
      notes = "Solid Japanese vintage-spec alternative.";
    }
  }

  // Recommended Offer amounts
  const suggestedDriveOffer = Math.max(Math.round((listing.price - fuelCost - 50) / 25) * 25, Math.round(listing.price * 0.88));
  const suggestedShipOffer = Math.max(Math.round((listing.price * 0.92) / 25) * 25, Math.round(listing.price * 0.88));

  return {
    oneWayMiles,
    roundTripMiles,
    driveHours,
    fuelCost,
    casePenalty,
    landedDriveCost,
    shippingAvailable,
    shippingCost,
    shippingCarrier,
    landedShipCost,
    cheaperMethod,
    cheaperMethodLabel,
    cheaperText,
    cheaperCalloutClass,
    cheaperIcon,
    savings,
    bestLandedCost,
    trueLandedCost,
    isLefty,
    grade,
    gradePillClass,
    verdict,
    notes,
    suggestedDriveOffer,
    suggestedShipOffer
  };
}

// Render Listings into DOM
function renderListings() {
  const container = document.getElementById("listingsGrid");
  const priceSlider = document.getElementById("priceSlider");
  const maxPrice = priceSlider ? parseFloat(priceSlider.value) : 5000;
  const mpg = parseFloat(document.getElementById("mpgSlider").value);
  const fuelPrice = parseFloat(document.getElementById("fuelSlider").value);
  const maxDriveHours = parseFloat(document.getElementById("driveSlider").value);
  const sortMode = document.getElementById("sortSelect").value;

  // 1. Filter listings by Brand & Max Price
  let activeListings = rawListings.filter(item => {
    // Strictly exclude any Epiphone models unless Elitist MIJ
    const titleLow = (item.title || "").toLowerCase();
    const brandLow = (item.brand_tier || "").toLowerCase();
    if (brandLow.includes("epiphone") || (titleLow.includes("epiphone") && !titleLow.includes("elitist"))) {
      return false;
    }

    // Strictly exclude non-335 Tokai models (Love Rock, Goldstar, LS/ULS/LC solid bodies)
    if (brandLow.includes("tokai") || titleLow.includes("tokai")) {
      if (/(love rock|goldstar|breezysound|silver star|springy sound|talbo|reborn|\b(u?ls|lc|sg|lp|st|te)[\s-]?\d{2,3})/i.test(titleLow)) {
        return false;
      }
      if (!/(\bes[\s-]?\d{2,3}|335|semi)/i.test(titleLow)) {
        return false;
      }
    }

    // Brand filter
    if (filteredBrand !== "all" && !item.brand_tier.toLowerCase().includes(filteredBrand.toLowerCase())) {
      return false;
    }

    // Source filter (Indie Shops / eBay UK / Reverb / Gumtree)
    if (filteredSource !== "all") {
      const idStr = (item.id || "").toLowerCase();
      const srcStr = (item.source || "").toLowerCase();
      if (filteredSource === "indie" && !idStr.startsWith("indie_") && item.source_type !== "indie") return false;
      if (filteredSource === "ebay" && !idStr.startsWith("ebay_") && !srcStr.includes("ebay")) return false;
      if (filteredSource === "reverb" && !idStr.startsWith("reverb_")) return false;
      if (filteredSource === "gumtree" && !idStr.startsWith("gumtree_") && !srcStr.includes("gumtree")) return false;
    }

    // Keyword Search filter
    if (searchQuery) {
      const haystack = `${item.title || ""} ${item.source || ""} ${item.brand_tier || ""} ${item.era_badge || ""} ${item.postcode || ""} ${item.year || ""}`.toLowerCase();
      if (!haystack.includes(searchQuery)) return false;
    }

    // Hidden & Shortlist filters
    if (hiddenIds.has(item.id)) return false;
    if (showShortlistOnly && !shortlistedIds.has(item.id)) return false;

    // Activity filter (New Today / Price Drops / 30+ Days on Market)
    if (filteredActivity === "new" && !item.is_new_today) return false;
    if (filteredActivity === "drops" && !(Number(item.price_drop || 0) > 0)) return false;
    if (filteredActivity === "stale" && !(Number(item.days_on_market || 0) >= 30)) return false;

    // Max Asking Price filter (slider values < 5000 restrict the price)
    if (maxPrice < 5000 && item.price > maxPrice) {
      return false;
    }

    return true;
  });

  // 2. Calculate metrics for each listing
  let enriched = activeListings.map(item => {
    const metrics = computeListingMetrics(item, mpg, fuelPrice, maxDriveHours);
    return { ...item, metrics };
  });

  // 3. Filter by Dexterity (Left-Handed vs Right-Handed)
  if (filteredDexterity === "right") {
    enriched = enriched.filter(item => !item.metrics.isLefty);
  } else if (filteredDexterity === "left") {
    enriched = enriched.filter(item => item.metrics.isLefty);
  }
  // "all" keeps both

  // 4. Sort
  enriched.sort((a, b) => {
    if (sortMode === "true_cost_asc") return a.metrics.trueLandedCost - b.metrics.trueLandedCost;
    if (sortMode === "price_asc") return a.price - b.price;
    if (sortMode === "distance_asc") return a.metrics.driveHours - b.metrics.driveHours;
    if (sortMode === "days_desc") return (b.days_on_market || 0) - (a.days_on_market || 0);
    if (sortMode === "days_asc") return (a.days_on_market ?? 9999) - (b.days_on_market ?? 9999);
    if (sortMode === "year_desc") return (b.year || 0) - (a.year || 0);
    if (sortMode === "grade") {
      const order = { "A+": 1, "A": 2, "B+": 3, "B": 4, "C": 5 };
      return (order[a.metrics.grade] || 99) - (order[b.metrics.grade] || 99);
    }
    return 0;
  });

  // Save for Interactive UK Map Modal
  lastRenderedListings = enriched;

  // Update live results counter badge
  const countBadge = document.getElementById("resultsCountBadge");
  if (countBadge) {
    countBadge.textContent = `${enriched.length} of ${rawListings.length} guitars`;
  }

  container.innerHTML = "";

  if (enriched.length === 0) {
    container.className = "grid grid-cols-1 gap-5";
    container.innerHTML = `
      <div class="col-span-full py-16 text-center bg-card border border-border rounded-xl p-8 space-y-2">
        <div class="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-secondary border border-border text-muted-foreground">
          <i data-lucide="search-x" class="w-5 h-5"></i>
        </div>
        <p class="text-sm font-semibold text-foreground">No guitars match the selected filters</p>
        <p class="text-xs text-muted-foreground max-w-md mx-auto">
          Try raising the Max Asking Price slider (currently £${maxPrice.toLocaleString()}), clearing the Shortlist/Search filter, or switching Dexterity to "All".
        </p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  // Compact shadcn Data Table View
  if (viewMode === "table") {
    container.className = "block";
    const rowsHtml = enriched.map(item => {
      const m = item.metrics;
      const isSaved = shortlistedIds.has(item.id);
      const priceDrop = Number(item.price_drop || 0);
      const days = typeof item.days_on_market === "number" ? item.days_on_market : null;
      return `
        <tr class="border-b border-border hover:bg-accent/50 transition-colors">
          <td class="py-2.5 pl-4 pr-2 whitespace-nowrap">
            <span class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold ${m.gradePillClass}">${m.grade}</span>
          </td>
          <td class="py-2.5 px-2 max-w-[280px]">
            <div class="flex items-center gap-2.5">
              <img src="${item.image_url}" alt="" class="w-10 h-10 rounded-md object-cover border border-border shrink-0 bg-background">
              <div class="min-w-0">
                <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="font-semibold text-foreground hover:text-primary transition-colors block truncate" title="${escapeQuotes(item.title)}">${item.title}</a>
                <div class="text-[11px] text-muted-foreground truncate">${item.brand_tier} • ${item.source}</div>
              </div>
            </div>
          </td>
          <td class="py-2.5 px-2 whitespace-nowrap text-muted-foreground tabular-nums">
            <div>${item.postcode}</div>
            <div class="text-[10px]">${m.oneWayMiles} mi (${m.driveHours}h)</div>
          </td>
          <td class="py-2.5 px-2 whitespace-nowrap tabular-nums">
            <div class="font-semibold text-foreground">£${item.price.toLocaleString()}</div>
            ${priceDrop > 0 ? `<div class="text-[10px] font-semibold text-emerald-400">↓ −£${Math.round(priceDrop)}</div>` : ''}
          </td>
          <td class="py-2.5 px-2 whitespace-nowrap tabular-nums">
            <div class="${m.cheaperMethod === 'ship' ? 'text-emerald-400 font-medium' : 'text-primary font-medium'}">${m.cheaperMethodLabel}</div>
            <div class="text-[10px] text-muted-foreground">${m.cheaperMethod === 'ship' ? (m.shippingCost === 0 ? 'Free Delivery' : '+£' + m.shippingCost.toFixed(0) + ' post') : '+£' + m.fuelCost + ' petrol'}</div>
          </td>
          <td class="py-2.5 px-2 whitespace-nowrap font-bold text-primary text-sm tabular-nums">
            £${m.trueLandedCost.toLocaleString()}
          </td>
          <td class="py-2.5 px-2 whitespace-nowrap text-muted-foreground tabular-nums">
            ${days !== null ? (days >= 30 ? `<span class="text-primary font-semibold">${days}d</span>` : `${days}d`) : '—'}
          </td>
          <td class="py-2.5 pl-2 pr-4 whitespace-nowrap text-right">
            <div class="inline-flex items-center gap-1">
              <button onclick="toggleShortlist('${escapeQuotes(item.id)}')" class="h-7 w-7 inline-flex items-center justify-center rounded-md border border-border ${isSaved ? 'bg-cherry/20 text-cherry border-cherry/40' : 'bg-secondary text-muted-foreground hover:text-foreground'}" title="${isSaved ? 'Remove from Shortlist' : 'Save to Shortlist'}">
                <i data-lucide="heart" class="w-3.5 h-3.5 ${isSaved ? 'fill-current' : ''}"></i>
              </button>
              <button onclick="hideListing('${escapeQuotes(item.id)}')" class="h-7 w-7 inline-flex items-center justify-center rounded-md border border-border bg-secondary text-muted-foreground hover:text-foreground" title="Hide listing">
                <i data-lucide="eye-off" class="w-3.5 h-3.5"></i>
              </button>
              <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="h-7 px-2.5 inline-flex items-center gap-1 rounded-md bg-primary text-primary-foreground text-[11px] font-semibold hover:bg-primary/90">
                <span>View</span>
                <i data-lucide="external-link" class="w-3 h-3"></i>
              </a>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <div class="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        <div class="overflow-x-auto custom-scrollbar">
          <table class="w-full text-left text-xs">
            <thead class="border-b border-border bg-secondary/70 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              <tr>
                <th class="py-3 pl-4 pr-2">Grade</th>
                <th class="py-3 px-2">Guitar &amp; Source</th>
                <th class="py-3 px-2">Location</th>
                <th class="py-3 px-2">Asking</th>
                <th class="py-3 px-2">Best Route</th>
                <th class="py-3 px-2">Landed</th>
                <th class="py-3 px-2">Age</th>
                <th class="py-3 pl-2 pr-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  // Card Grid View
  container.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5";

  enriched.forEach(item => {
    const m = item.metrics;
    const card = document.createElement("article");
    card.className = "group rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:border-[#42352C] transition-all flex flex-col justify-between overflow-hidden";

    // Clean era label (strip leading emojis for crisp shadcn badge look)
    const cleanEra = (item.era_badge || "ERA UNKNOWN").replace(/^[^\w\d]+/u, "").trim() || item.era_badge;
    const daysOnMarket = typeof item.days_on_market === "number" ? item.days_on_market : null;
    const priceDrop = Number(item.price_drop || 0);
    const isNewToday = Boolean(item.is_new_today);

    const marketBadgeHtml = daysOnMarket !== null
      ? (daysOnMarket >= 30
          ? `<span class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold bg-primary/15 text-primary border border-primary/30 tabular-nums" title="Listed ${daysOnMarket} days ago — strong negotiation leverage"><i data-lucide="clock" class="w-2.5 h-2.5"></i>${daysOnMarket}d • Negotiate</span>`
          : (isNewToday
              ? `<span class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">NEW</span>`
              : `<span class="inline-flex items-center gap-1 text-[10px] text-muted-foreground/80 tabular-nums"><i data-lucide="clock" class="w-2.5 h-2.5"></i>${daysOnMarket}d</span>`))
      : "";

    card.innerHTML = `
      <div>
        <!-- Image & Overlay Badges -->
        <div class="relative aspect-[16/10] w-full bg-background overflow-hidden border-b border-border">
          <img src="${item.image_url}" alt="${escapeQuotes(item.title)}" class="w-full h-full object-cover object-center group-hover:scale-[1.02] transition-transform duration-300">
          <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/85 via-transparent to-background/30"></div>

          <!-- Top Left Badges: Deal Grade, Price Drop & Lefty -->
          <div class="absolute top-3 left-3 flex flex-wrap gap-1.5 items-center">
            <span class="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] tracking-tight backdrop-blur-md ${m.gradePillClass}">
              ${m.verdict}
            </span>
            ${priceDrop > 0 ? `
              <span class="inline-flex items-center gap-0.5 rounded-md px-2 py-0.5 text-[10px] font-bold bg-emerald-500 text-background shadow-sm tabular-nums">
                <i data-lucide="trending-down" class="w-3 h-3"></i>
                <span>−£${Math.round(priceDrop).toLocaleString()}</span>
              </span>
            ` : ''}
            ${m.isLefty ? `
              <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-semibold bg-purple-600/90 text-white border border-purple-400/50 backdrop-blur-md">
                <span>LEFT-HANDED</span>
              </span>
            ` : ''}
          </div>

          <!-- Top Right Badge: Era -->
          <div class="absolute top-3 right-3">
            <span class="inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium bg-background/85 backdrop-blur-md text-primary border border-border">
              ${cleanEra}
            </span>
          </div>

          <!-- Bottom Location Pill -->
          <div class="absolute bottom-2.5 left-3 inline-flex items-center gap-1.5 rounded-md bg-background/85 backdrop-blur-md border border-border px-2 py-0.5 text-[11px] font-medium text-foreground/90 tabular-nums">
            <i data-lucide="map-pin" class="w-3 h-3 text-primary"></i>
            <span>${item.postcode} • ${m.oneWayMiles} mi (${m.driveHours}h from ${currentHub})</span>
          </div>

          <!-- Bottom Right: Shortlist & Hide Quick Actions -->
          <div class="absolute bottom-2.5 right-3 flex items-center gap-1.5">
            <button
              onclick="toggleShortlist('${escapeQuotes(item.id)}')"
              class="h-7 w-7 inline-flex items-center justify-center rounded-md backdrop-blur-md border transition-colors ${shortlistedIds.has(item.id) ? 'bg-cherry text-white border-cherry shadow-sm' : 'bg-background/85 text-muted-foreground hover:text-foreground border-border'}"
              title="${shortlistedIds.has(item.id) ? 'Remove from Shortlist' : 'Save to Shortlist'}">
              <i data-lucide="heart" class="w-3.5 h-3.5 ${shortlistedIds.has(item.id) ? 'fill-current' : ''}"></i>
            </button>
            <button
              onclick="hideListing('${escapeQuotes(item.id)}')"
              class="h-7 w-7 inline-flex items-center justify-center rounded-md bg-background/85 backdrop-blur-md border border-border text-muted-foreground hover:text-foreground transition-colors"
              title="Hide listing">
              <i data-lucide="eye-off" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>

        <!-- Card Content -->
        <div class="p-4 space-y-3.5">
          <div class="space-y-1">
            <div class="flex items-center justify-between gap-2 text-[11px] font-medium text-muted-foreground">
              <span class="truncate">${item.brand_tier} • ${item.source}</span>
              <div class="flex items-center gap-1.5 shrink-0">
                ${marketBadgeHtml}
                ${m.isLefty ? '<span class="text-purple-300 font-semibold">Lefty</span>' : ''}
              </div>
            </div>
            <h3 class="text-sm font-semibold text-foreground leading-snug line-clamp-2" title="${escapeQuotes(item.title)}">
              ${item.title}
            </h3>
          </div>

          <!-- Price & Route Comparison Panel -->
          <div class="rounded-lg border border-border bg-background/70 p-3 space-y-2.5 text-xs">
            <div class="flex justify-between items-baseline">
              <span class="text-muted-foreground">Asking Price</span>
              <div class="flex items-baseline gap-2 tabular-nums">
                ${priceDrop > 0 && item.initial_price ? `<span class="text-[11px] text-muted-foreground line-through">£${Number(item.initial_price).toLocaleString()}</span>` : ''}
                <span class="text-foreground font-semibold text-sm">£${item.price.toLocaleString()}</span>
              </div>
            </div>

            <!-- Route Comparison Split -->
            <div class="grid grid-cols-2 gap-2 pt-2 border-t border-border text-[11px]">
              <!-- Road Trip Option -->
              <div class="p-2.5 rounded-md border ${m.cheaperMethod === 'drive' ? 'bg-primary/10 border-primary/40' : 'bg-card/80 border-border'}">
                <div class="flex items-center justify-between gap-1 font-semibold ${m.cheaperMethod === 'drive' ? 'text-primary' : 'text-muted-foreground'}">
                  <span class="inline-flex items-center gap-1"><i data-lucide="car" class="w-3 h-3"></i> Road Trip</span>
                  ${m.cheaperMethod === 'drive' ? '<span class="rounded bg-primary text-primary-foreground text-[9px] font-bold px-1.5 py-0.2">BEST</span>' : ''}
                </div>
                <div class="text-muted-foreground mt-1.5 tabular-nums">Petrol: <strong class="text-foreground">+£${m.fuelCost}</strong></div>
                <div class="text-[10px] text-muted-foreground/80 tabular-nums">${m.roundTripMiles} mi round</div>
                <div class="text-foreground font-semibold mt-1 tabular-nums">£${m.landedDriveCost.toLocaleString()}</div>
              </div>

              <!-- Seller Delivery Option -->
              <div class="p-2.5 rounded-md border ${m.cheaperMethod === 'ship' ? 'bg-emerald-500/10 border-emerald-500/40' : 'bg-card/80 border-border'}">
                <div class="flex items-center justify-between gap-1 font-semibold ${m.cheaperMethod === 'ship' ? 'text-emerald-400' : 'text-muted-foreground'}">
                  <span class="inline-flex items-center gap-1"><i data-lucide="package" class="w-3 h-3"></i> Delivery</span>
                  ${m.cheaperMethod === 'ship' ? '<span class="rounded bg-emerald-500 text-background text-[9px] font-bold px-1.5 py-0.2">BEST</span>' : ''}
                </div>
                <div class="text-muted-foreground mt-1.5 tabular-nums">Fee: <strong class="${m.shippingCost === 0 && m.shippingAvailable ? 'text-emerald-400' : 'text-foreground'}">${m.shippingAvailable ? (m.shippingCost === 0 ? 'FREE' : '+£' + m.shippingCost.toFixed(2)) : 'N/A'}</strong></div>
                <div class="text-[10px] text-muted-foreground/80 truncate" title="${escapeQuotes(m.shippingCarrier)}">${m.shippingCarrier}</div>
                <div class="text-foreground font-semibold mt-1 tabular-nums">${m.shippingAvailable ? '£' + m.landedShipCost.toLocaleString() : 'Collection only'}</div>
              </div>
            </div>

            <!-- Cheaper Route Callout -->
            <div class="px-2.5 py-1.5 rounded-md text-[11px] font-medium flex items-center gap-1.5 ${m.cheaperCalloutClass}">
              <i data-lucide="${m.cheaperIcon}" class="w-3.5 h-3.5 shrink-0"></i>
              <span class="leading-tight">${m.cheaperText}</span>
            </div>

            ${item.has_case ? '' : `
            <div class="flex justify-between items-baseline text-[11px] text-cherry font-medium">
              <span>Missing Hard Case Penalty</span>
              <span class="tabular-nums">+£150</span>
            </div>
            `}

            <!-- Final Best Landed Cost -->
            <div class="border-t border-border pt-2.5 flex justify-between items-baseline">
              <div>
                <span class="font-medium text-foreground">True Landed Cost</span>
                <span class="text-[10px] text-muted-foreground block">via ${m.cheaperMethodLabel}</span>
              </div>
              <span class="text-lg font-bold tracking-tight text-primary tabular-nums">£${m.trueLandedCost.toLocaleString()}</span>
            </div>
          </div>

          <!-- Valuation Notes -->
          <p class="text-[11px] text-muted-foreground leading-relaxed">
            ${m.notes}
          </p>
        </div>
      </div>

      <!-- Card Footer Actions -->
      <div class="p-4 pt-0 space-y-2">
        <div class="grid ${m.shippingAvailable ? 'grid-cols-2' : 'grid-cols-1'} gap-2">
          <button
            onclick="generateRoadTripOffer('${escapeQuotes(item.title)}', ${item.price}, ${m.suggestedDriveOffer}, ${m.roundTripMiles}, '${currentHub}', ${m.fuelCost})"
            class="h-8 px-2.5 inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary/70 hover:bg-accent hover:border-primary/40 text-foreground text-[11px] font-medium transition-colors tabular-nums"
            title="Copy Road Trip discount offer message to clipboard">
            <i data-lucide="car" class="w-3 h-3 text-primary"></i>
            <span>Offer £${m.suggestedDriveOffer}</span>
          </button>

          ${m.shippingAvailable ? `
          <button
            onclick="generateShippedOffer('${escapeQuotes(item.title)}', ${item.price}, ${m.suggestedShipOffer}, '${escapeQuotes(m.shippingCarrier)}')"
            class="h-8 px-2.5 inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary/70 hover:bg-accent hover:border-emerald-500/40 text-foreground text-[11px] font-medium transition-colors tabular-nums"
            title="Copy Seller Delivery discount offer message to clipboard">
            <i data-lucide="package" class="w-3 h-3 text-emerald-400"></i>
            <span>Ship £${m.suggestedShipOffer}</span>
          </button>
          ` : ''}
        </div>

        <a
          href="${item.url}"
          target="_blank"
          rel="noopener noreferrer"
          class="w-full h-9 inline-flex items-center justify-center gap-1.5 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs transition-colors shadow-sm">
          <span class="truncate max-w-[85%]">View on ${item.source}</span>
          <i data-lucide="external-link" class="w-3.5 h-3.5 shrink-0"></i>
        </a>
      </div>
    `;

    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

// Interactive Dark-Mode UK Deal Map (Leaflet)
function renderUkMap() {
  const mapEl = document.getElementById("ukMapContainer");
  if (!mapEl || typeof L === "undefined") return;

  if (!ukMapInstance) {
    ukMapInstance = L.map("ukMapContainer", { zoomControl: true }).setView([53.0, -1.5], 6);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap &copy; CARTO",
      subdomains: "abcd",
      maxZoom: 18
    }).addTo(ukMapInstance);
    ukMapLayerGroup = L.layerGroup().addTo(ukMapInstance);
  }

  ukMapLayerGroup.clearLayers();

  const maxDriveHours = parseFloat(document.getElementById("driveSlider")?.value || "3");
  const radiusMeters = ((maxDriveHours * 50) / 1.25) * 1609.34;

  // Plot Hull & Somerset Hubs + Active Hub Radius Circle
  Object.entries(HUBS).forEach(([key, h]) => {
    const isActive = (key === currentHub);
    if (isActive) {
      L.circle([h.lat, h.lng], {
        radius: radiusMeters,
        color: "#E59A28",
        weight: 1.5,
        dashArray: "6 6",
        fillColor: "#E59A28",
        fillOpacity: 0.06
      }).addTo(ukMapLayerGroup);
    }
    L.circleMarker([h.lat, h.lng], {
      radius: isActive ? 8 : 6,
      color: "#FFFFFF",
      weight: 2,
      fillColor: isActive ? "#3B82F6" : "#64748B",
      fillOpacity: 1
    }).bindPopup(`<div class="text-xs"><strong class="text-primary">${h.name} (${h.postcode})</strong><br><span class="text-muted-foreground">${isActive ? 'Active Home Hub • ' + maxDriveHours + 'h drive ring' : 'Secondary Hub'}</span></div>`).addTo(ukMapLayerGroup);
  });

  // Plot every filtered guitar with subtle deterministic jitter for overlapping postcodes
  const coordCounts = {};
  let plotted = 0;
  lastRenderedListings.forEach(item => {
    if (!item.coords || item.coords.length !== 2) return;
    const m = item.metrics;
    const cKey = `${item.coords[0].toFixed(3)},${item.coords[1].toFixed(3)}`;
    const idx = coordCounts[cKey] || 0;
    coordCounts[cKey] = idx + 1;

    const angle = idx * 2.39996; // golden angle spread
    const spread = idx === 0 ? 0 : Math.min(0.06, 0.012 * Math.sqrt(idx));
    const lat = item.coords[0] + Math.sin(angle) * spread;
    const lng = item.coords[1] + Math.cos(angle) * spread * 1.4;

    let color = "#A69A8E";
    let radius = 6;
    if (m.grade === "A+") { color = "#10B981"; radius = 8; }
    else if (m.grade === "A") { color = "#E59A28"; radius = 7; }
    else if (m.grade === "C") { color = "#57534E"; radius = 5; }

    const popupHtml = `
      <div style="width:230px;font-family:Inter,sans-serif;">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
          <img src="${item.image_url}" style="width:48px;height:48px;object-fit:cover;border-radius:6px;border:1px solid #2A221D;">
          <div style="min-width:0;">
            <div style="font-size:10px;font-weight:700;color:${color};">${m.verdict}</div>
            <div style="font-size:12px;font-weight:600;color:#F5EFE6;line-height:1.25;margin-top:2px;">${item.title}</div>
          </div>
        </div>
        <div style="font-size:11px;color:#A69A8E;line-height:1.45;margin-bottom:8px;">
          <div>${item.source} • <strong>${item.postcode}</strong> (${m.driveHours}h)</div>
          <div>Ask: <strong style="color:#F5EFE6;">£${item.price.toLocaleString()}</strong> • Landed: <strong style="color:#E59A28;">£${m.trueLandedCost.toLocaleString()}</strong></div>
          <div>Best: ${m.cheaperMethodLabel}</div>
        </div>
        <a href="${item.url}" target="_blank" rel="noopener noreferrer" style="display:block;text-align:center;background:#E59A28;color:#0B0908;font-weight:700;font-size:11px;padding:6px 10px;border-radius:6px;text-decoration:none;">
          View Live Listing &rarr;
        </a>
      </div>
    `;

    L.circleMarker([lat, lng], {
      radius,
      color: "#0B0908",
      weight: 1.5,
      fillColor: color,
      fillOpacity: 0.92
    }).bindPopup(popupHtml).addTo(ukMapLayerGroup);
    plotted++;
  });

  const sub = document.getElementById("mapSubtitle");
  if (sub) {
    sub.textContent = `Plotting ${plotted} filtered guitars • ${currentHub} ${maxDriveHours}h drive-time radius ring`;
  }
  setTimeout(() => ukMapInstance.invalidateSize(), 120);
}

function escapeQuotes(str) {
  return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// 1-Click Road Trip Offer Generator with Clipboard Copy
function generateRoadTripOffer(title, askingPrice, suggestedOffer, roundTripMiles, hub, fuelCost) {
  const message = `Hi! I'm very interested in your "${title}". I'm based in ${hub} and would be making the ~${roundTripMiles} mile round-trip drive to collect in person with cash or instant bank transfer. Would you consider £${suggestedOffer} to help offset the petrol cost (£${fuelCost})? I can collect this week/weekend at your convenience. Thanks!`;

  navigator.clipboard.writeText(message).then(() => {
    showToast(`🚗 Copied Road Trip offer of £${suggestedOffer} to clipboard!`);
  }).catch(() => {
    prompt("Copy your Road Trip offer message:", message);
  });
}

// 1-Click Shipped Offer Generator with Clipboard Copy
function generateShippedOffer(title, askingPrice, suggestedOffer, carrier) {
  const message = `Hi! I'm very interested in your "${title}". Would you accept £${suggestedOffer} fully inclusive of insured delivery via ${carrier}? I can send the payment via instant bank transfer/PayPal right away. Thanks!`;

  navigator.clipboard.writeText(message).then(() => {
    showToast(`📦 Copied Shipped offer of £${suggestedOffer} to clipboard!`);
  }).catch(() => {
    prompt("Copy your Shipped delivery offer message:", message);
  });
}

function showToast(text) {
  const toast = document.getElementById("toast");
  const msg = document.getElementById("toastMsg");
  msg.textContent = text;
  toast.classList.remove("translate-y-24", "opacity-0");
  toast.classList.add("translate-y-0", "opacity-100");
  setTimeout(() => {
    toast.classList.add("translate-y-24", "opacity-0");
    toast.classList.remove("translate-y-0", "opacity-100");
  }, 2800);
}

// Fetch deals from server or fallback
async function loadDeals() {
  try {
    // 1. Try /api/deals with timestamp cache buster
    let res = await fetch("/api/deals?_t=" + Date.now());
    let text = "";
    if (res.ok) {
      text = await res.text();
    }
    // 2. If /api/deals returned HTML or didn't start with '[', fetch static 'deals.json' directly
    if (!text || !text.trim().startsWith("[")) {
      res = await fetch("deals.json?_t=" + Date.now());
      if (res.ok) {
        text = await res.text();
      }
    }

    if (text && text.trim().startsWith("[")) {
      const data = JSON.parse(text);
      if (Array.isArray(data) && data.length > 0) {
        rawListings = data;
        renderListings();
        return;
      }
    }
  } catch (err) {
    console.warn("Could not load dynamic deals.json feed, using fallback:", err);
  }

  // Load fallback seed data
  rawListings = FALLBACK_LISTINGS;
  renderListings();
}

// Setup Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  // Hub Switchers
  const hubHullBtn = document.getElementById("hubHull");
  const hubSomersetBtn = document.getElementById("hubSomerset");
  const activeHubBadge = document.getElementById("activeHubBadge");

  hubHullBtn.addEventListener("click", () => {
    currentHub = "Hull";
    hubHullBtn.className = "hub-btn inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 bg-primary text-primary-foreground font-semibold shadow-sm transition-all";
    hubSomersetBtn.className = "hub-btn inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-muted-foreground hover:text-foreground transition-all";
    activeHubBadge.textContent = "Hub: Hull HQ (HU1)";
    const fbLink = document.getElementById("fbMarketplaceLink");
    const fbSub = document.getElementById("fbMarketplaceSub");
    if (fbLink) fbLink.href = "https://www.facebook.com/marketplace/hull/search?query=gibson%20335";
    if (fbSub) fbSub.textContent = "Hull Radius";
    const gtLink = document.getElementById("gumtreeLink");
    const gtSub = document.getElementById("gumtreeSub");
    if (gtLink) gtLink.href = "https://www.gumtree.com/search?search_category=guitars&search_location=Hull&distance=100&q=gibson+335";
    if (gtSub) gtSub.textContent = "Hull 100mi";
    renderListings();
  });

  hubSomersetBtn.addEventListener("click", () => {
    currentHub = "Somerset";
    hubSomersetBtn.className = "hub-btn inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 bg-primary text-primary-foreground font-semibold shadow-sm transition-all";
    hubHullBtn.className = "hub-btn inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-muted-foreground hover:text-foreground transition-all";
    activeHubBadge.textContent = "Hub: Somerset (TA8)";
    const fbLink = document.getElementById("fbMarketplaceLink");
    const fbSub = document.getElementById("fbMarketplaceSub");
    if (fbLink) fbLink.href = "https://www.facebook.com/marketplace/bristol/search?query=gibson%20335";
    if (fbSub) fbSub.textContent = "Bristol & Somerset";
    const gtLink = document.getElementById("gumtreeLink");
    const gtSub = document.getElementById("gumtreeSub");
    if (gtLink) gtLink.href = "https://www.gumtree.com/search?search_category=guitars&search_location=Bristol&distance=50&q=gibson+335";
    if (gtSub) gtSub.textContent = "Somerset 50mi";
    renderListings();
  });

  // Price Slider
  const priceSlider = document.getElementById("priceSlider");
  const priceVal = document.getElementById("priceVal");
  if (priceSlider && priceVal) {
    priceSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      if (val >= 5000) {
        priceVal.textContent = "£5,000+ (No Limit)";
      } else {
        priceVal.textContent = `£${val.toLocaleString()}`;
      }
      renderListings();
    });
  }

  // Sliders
  const mpgSlider = document.getElementById("mpgSlider");
  const fuelSlider = document.getElementById("fuelSlider");
  const driveSlider = document.getElementById("driveSlider");

  mpgSlider.addEventListener("input", (e) => {
    document.getElementById("mpgVal").textContent = `${e.target.value} MPG`;
    renderListings();
  });

  fuelSlider.addEventListener("input", (e) => {
    document.getElementById("fuelVal").textContent = `£${parseFloat(e.target.value).toFixed(2)} / L`;
    renderListings();
  });

  driveSlider.addEventListener("input", (e) => {
    document.getElementById("driveVal").textContent = `${parseFloat(e.target.value).toFixed(1)} Hours (4.5h for A+)`;
    renderListings();
  });

  // Dexterity Filter Buttons
  document.querySelectorAll(".filter-dex-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const targetBtn = e.target.closest(".filter-dex-btn");
      if (!targetBtn) return;
      document.querySelectorAll(".filter-dex-btn").forEach(b => {
        b.className = "filter-dex-btn inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-muted-foreground hover:text-foreground font-medium transition-all";
      });
      targetBtn.className = "filter-dex-btn inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 bg-primary text-primary-foreground font-semibold shadow-sm transition-all";
      filteredDexterity = targetBtn.getAttribute("data-dex");
      renderListings();
    });
  });

  // Source Filter Buttons
  document.querySelectorAll(".filter-source-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const targetBtn = e.target.closest(".filter-source-btn");
      if (!targetBtn) return;
      document.querySelectorAll(".filter-source-btn").forEach(b => {
        b.className = "filter-source-btn rounded-md px-2.5 py-1 text-muted-foreground hover:text-foreground transition-all";
      });
      targetBtn.className = "filter-source-btn rounded-md px-2.5 py-1 bg-primary text-primary-foreground font-semibold shadow-sm transition-all";
      filteredSource = targetBtn.getAttribute("data-source");
      renderListings();
    });
  });

  // Keyword Search Input
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      renderListings();
    });
  }

  // Activity Filter Buttons (New Today / Price Drops / 30+ Days)
  document.querySelectorAll(".filter-activity-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const targetBtn = e.target.closest(".filter-activity-btn");
      if (!targetBtn) return;
      document.querySelectorAll(".filter-activity-btn").forEach(b => {
        b.className = "filter-activity-btn rounded-md px-2.5 py-1 text-muted-foreground hover:text-foreground transition-all";
      });
      targetBtn.className = "filter-activity-btn rounded-md px-2.5 py-1 bg-card text-foreground font-semibold shadow-sm border border-border transition-all";
      filteredActivity = targetBtn.getAttribute("data-activity");
      renderListings();
    });
  });

  // Brand Filter Buttons
  document.querySelectorAll(".filter-brand-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".filter-brand-btn").forEach(b => {
        b.className = "filter-brand-btn rounded-md px-2.5 py-1 text-muted-foreground hover:text-foreground transition-all";
      });
      e.target.className = "filter-brand-btn rounded-md px-2.5 py-1 bg-card text-foreground font-semibold shadow-sm border border-border transition-all";
      filteredBrand = e.target.getAttribute("data-brand");
      renderListings();
    });
  });

  // Sort Dropdown
  document.getElementById("sortSelect").addEventListener("change", renderListings);

  // Shortlist Filter Toggle
  const shortlistFilterBtn = document.getElementById("shortlistFilterBtn");
  if (shortlistFilterBtn) {
    shortlistFilterBtn.addEventListener("click", () => {
      showShortlistOnly = !showShortlistOnly;
      shortlistFilterBtn.className = showShortlistOnly
        ? "inline-flex h-8 items-center gap-1.5 rounded-md border border-cherry/50 bg-cherry/15 px-2.5 text-xs font-semibold text-foreground transition-colors"
        : "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-secondary px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors";
      renderListings();
    });
  }

  // Restore Hidden Listings Button
  const restoreHiddenBtn = document.getElementById("restoreHiddenBtn");
  if (restoreHiddenBtn) {
    restoreHiddenBtn.addEventListener("click", restoreHiddenListings);
  }

  // Card Grid <-> Compact Data Table Toggle
  const viewGridBtn = document.getElementById("viewGridBtn");
  const viewTableBtn = document.getElementById("viewTableBtn");
  if (viewGridBtn && viewTableBtn) {
    viewGridBtn.addEventListener("click", () => {
      viewMode = "grid";
      viewGridBtn.className = "inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-semibold bg-card text-foreground shadow-sm border border-border transition-all";
      viewTableBtn.className = "inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-medium text-muted-foreground hover:text-foreground transition-all";
      renderListings();
    });
    viewTableBtn.addEventListener("click", () => {
      viewMode = "table";
      viewTableBtn.className = "inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-semibold bg-card text-foreground shadow-sm border border-border transition-all";
      viewGridBtn.className = "inline-flex h-7 items-center gap-1 rounded px-2 text-[11px] font-medium text-muted-foreground hover:text-foreground transition-all";
      renderListings();
    });
  }

  // Interactive UK Deal Map Modal
  const mapModal = document.getElementById("mapModal");
  const openMapBtn = document.getElementById("openMapBtn");
  const closeMapBtn = document.getElementById("closeMapBtn");
  if (mapModal && openMapBtn && closeMapBtn) {
    openMapBtn.addEventListener("click", () => {
      mapModal.classList.remove("hidden");
      renderUkMap();
      if (window.lucide) lucide.createIcons();
    });
    closeMapBtn.addEventListener("click", () => mapModal.classList.add("hidden"));
    mapModal.addEventListener("click", (e) => {
      if (e.target === mapModal) mapModal.classList.add("hidden");
    });
  }

  // Checklist Dialog
  const modal = document.getElementById("checklistModal");
  document.getElementById("openChecklistBtn").addEventListener("click", () => modal.classList.remove("hidden"));
  document.getElementById("closeChecklistBtn").addEventListener("click", () => modal.classList.add("hidden"));
  document.getElementById("dismissChecklistBtn").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!modal.classList.contains("hidden")) modal.classList.add("hidden");
      if (mapModal && !mapModal.classList.contains("hidden")) mapModal.classList.add("hidden");
    }
  });

  updateShortlistHiddenUI();

  // Deal Importer (Facebook Marketplace & Gumtree)
  const fbForm = document.getElementById("fbImportForm");
  if (fbForm) {
    fbForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const urlInput = document.getElementById("fbUrlInput");
      const locInput = document.getElementById("fbLocInput");
      const btn = document.getElementById("fbImportBtn");

      const targetUrl = urlInput.value.trim();
      const loc = locInput.value.trim() || "Hull";
      if (!targetUrl) return;

      const origBtn = btn.innerHTML;
      btn.innerHTML = `<span>⏳ Extracting...</span>`;
      btn.disabled = true;

      try {
        const resp = await fetch(`/api/import_fb?url=${encodeURIComponent(targetUrl)}&location=${encodeURIComponent(loc)}`);
        const text = await resp.text();
        let result = null;
        try {
          if (text && (text.trim().startsWith("{") || text.trim().startsWith("["))) {
            result = JSON.parse(text);
          }
        } catch (e) {
          result = null;
        }

        if (result && result.status === "ok" && result.item) {
          rawListings.unshift(result.item);
          renderListings();
          urlInput.value = "";
          showToast(`✅ Added Deal: ${result.item.title}`);
        } else if (result && result.message) {
          showToast(`❌ ${result.message}`);
        } else {
          showToast(`❌ Could not parse listing. Meta / 2FA checkpoint blocked the page.`);
        }
      } catch (err) {
        showToast(`❌ Connection error: ${err.message}`);
      } finally {
        btn.innerHTML = origBtn;
        btn.disabled = false;
      }
    });
  }

  // Manual Scan Trigger Button
  const scanNowBtn = document.getElementById("scanNowBtn");
  const scanSpinner = document.getElementById("scanSpinner");
  const scanBtnText = document.getElementById("scanBtnText");
  if (scanNowBtn) {
    scanNowBtn.addEventListener("click", async () => {
      if (window.location.hostname.includes("github.io")) {
        await loadDeals();
        showToast("Feed refreshed! Cloud auto-scans run every 30 mins via GitHub Actions.");
        return;
      }
      scanNowBtn.disabled = true;
      if (scanSpinner) scanSpinner.classList.add("animate-spin");
      if (scanBtnText) scanBtnText.textContent = "Scanning UK Feed...";
      showToast("Sweeping Indie Shops, eBay UK & Reverb in background...");
      try {
        await fetch("/api/scan_now");
        // Poll for fresh results after 4s and 8s
        setTimeout(loadDeals, 4000);
        setTimeout(() => {
          loadDeals();
          showToast("✅ Scan complete! Latest deals updated.");
          if (scanSpinner) scanSpinner.classList.remove("animate-spin");
          if (scanBtnText) scanBtnText.textContent = "Scan Live Deals";
          scanNowBtn.disabled = false;
        }, 8000);
      } catch (err) {
        showToast("❌ Could not trigger scan: " + err.message);
        if (scanSpinner) scanSpinner.classList.remove("animate-spin");
        if (scanBtnText) scanBtnText.textContent = "Scan Live Deals";
        scanNowBtn.disabled = false;
      }
    });
  }

  // Auto-refresh feed quietly in background every 60 seconds
  setInterval(() => {
    loadDeals();
  }, 60000);

  // Initialize
  loadDeals();
});
