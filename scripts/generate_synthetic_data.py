"""Generate synthetic GoDesi sales data, Jan 2024 - Dec 2025.

Real anchor: the GoDesi products found in the Open Food Facts extract (real
barcodes and names). Everything else (prices, customers, orders, stores,
stock) is invented with a fixed seed, so every run gives identical files.

Two load batches, to practise incremental models and snapshots in dbt:
  batch_1  everything up to 2025-11-30 (order statuses as of that moment)
  batch_2  December 2025 + status updates for older orders + product price changes

Output:
  data/raw/synthetic/batch_<n>/<schema>/<table>.csv.gz
  load/02_load_synthetic_batch_1.sql   (create raw tables + COPY batch 1)
  load/03_load_synthetic_batch_2.sql   (COPY batch 2 into the same tables)

Usage (from the project root):
    .venv/Scripts/python.exe scripts/generate_synthetic_data.py
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
rng = np.random.default_rng(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "synthetic"
SQL_DIR = ROOT / "load"

START = date(2024, 1, 1)
END = date(2025, 12, 31)
CUTOFF = datetime(2025, 12, 1)            # batch_1 = before, batch_2 = from here
END_TS = datetime(2025, 12, 31, 23, 59, 59)

STAGE = "@GODESI_RAW.ERP.SYNTHETIC_STAGE"
FILE_FORMAT = "GODESI_RAW.ERP.SYNTH_CSV_FORMAT"

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------
# name, category, sub_category, pack_size, mrp_inr, barcode (None = invented), launch_date, popularity
PRODUCTS = [
    # Real GoDesi products (names + barcodes from Open Food Facts)
    ("Desi Popz Tangy Imli",      "Candy",   "Lollipop",     "32g (4 pcs)",   40,  "8906108890050", "2021-06-01", 10),
    ("Desi Popz Real Aam",        "Candy",   "Lollipop",     "32g (4 pcs)",   40,  "8906108891767", "2022-03-01", 8),
    ("Desi Popz Imli Jar",        "Candy",   "Lollipop",     "80g",           99,  "8906108890173", "2021-06-01", 5),
    ("Desi Popz Assorted",        "Candy",   "Lollipop",     "160g (20 pcs)", 199, "8906108890005", "2021-09-01", 6),
    ("Go Desi Ice Popz",          "Frozen",  "Ice Pop",      "6 x 60ml",      180, "8906108893549", "2024-04-01", 3),
    ("Kaju Katli",                "Mithai",  "Barfi",        "180g",          299, "8906108893525", "2022-10-01", 6),
    ("Ghee Mysore Pak",           "Mithai",  "Barfi",        "200g",          249, "8906108893792", "2023-09-01", 4),
    ("Dates Dry Fruit Laddu",     "Laddu",   "Dry Fruit",    "200g",          299, "8906108895581", "2025-09-15", 3),
    ("Bombay Bhel",               "Namkeen", "Ready to Eat", "150g",          99,  "8906108895147", "2025-10-01", 3),
    # Invented line extensions
    ("Desi Popz Kala Khatta",     "Candy",   "Lollipop",     "32g (4 pcs)",   40,  None, "2022-06-01", 6),
    ("Desi Popz Jamun",           "Candy",   "Lollipop",     "32g (4 pcs)",   40,  None, "2023-04-01", 4),
    ("Desi Popz Kaccha Aam",      "Candy",   "Lollipop",     "32g (4 pcs)",   40,  None, "2024-03-01", 5),
    ("Desi Popz Masala Imli",     "Candy",   "Lollipop",     "32g (4 pcs)",   40,  None, "2022-01-01", 5),
    ("Desi Popz Variety Jar",     "Candy",   "Lollipop",     "500g",          449, None, "2023-10-01", 3),
    ("Imli Goli",                 "Candy",   "Goli",         "100g",          60,  None, "2021-11-01", 5),
    ("Aam Goli",                  "Candy",   "Goli",         "100g",          60,  None, "2022-02-01", 4),
    ("Kokum Candy",               "Candy",   "Goli",         "100g",          70,  None, "2024-07-01", 2),
    ("Aam Papad",                 "Fruit Bar", "Papad",      "100g",          80,  None, "2021-08-01", 6),
    ("Aam Papad Family Pack",     "Fruit Bar", "Papad",      "250g",          180, None, "2022-08-01", 3),
    ("Imli Papad",                "Fruit Bar", "Papad",      "100g",          80,  None, "2022-05-01", 3),
    ("Mixed Fruit Papad",         "Fruit Bar", "Papad",      "100g",          90,  None, "2024-09-01", 2),
    ("Peanut Chikki",             "Chikki",  "Bar",          "100g",          50,  None, "2021-10-01", 6),
    ("Til Chikki",                "Chikki",  "Bar",          "100g",          60,  None, "2021-10-01", 4),
    ("Dry Fruit Chikki",          "Chikki",  "Bar",          "150g",          199, None, "2022-11-01", 3),
    ("Chikki Bites",              "Chikki",  "Bites",        "200g",          149, None, "2023-06-01", 4),
    ("Soan Papdi",                "Mithai",  "Flaky",        "250g",          149, None, "2022-09-01", 4),
    ("Besan Laddu",               "Laddu",   "Classic",      "250g",          229, None, "2022-09-01", 4),
    ("Dodha Barfi",               "Mithai",  "Barfi",        "250g",          279, None, "2023-09-01", 2),
    ("Kaju Roll",                 "Mithai",  "Roll",         "200g",          349, None, "2024-10-01", 2),
    ("Mithai Gift Box",           "Mithai",  "Gift Box",     "500g",          599, None, "2023-10-01", 3),
    ("Coconut Barfi",             "Mithai",  "Barfi",        "200g",          199, None, "2024-02-01", 2),
    ("Ragi Laddu",                "Laddu",   "Millet",       "200g",          199, None, "2024-06-01", 3),
    ("Til Laddu",                 "Laddu",   "Classic",      "200g",          179, None, "2023-01-01", 2),
    ("Bhel Puri Kit",             "Namkeen", "Ready to Eat", "150g",          89,  None, "2023-03-01", 3),
    ("Masala Peanuts",            "Namkeen", "Nuts",         "150g",          79,  None, "2022-04-01", 4),
    ("Khakhra Masala",            "Namkeen", "Khakhra",      "200g",          99,  None, "2024-05-01", 2),
    ("Ice Popz Kala Khatta",      "Frozen",  "Ice Pop",      "6 x 60ml",      180, None, "2024-04-01", 2),
    ("Ice Popz Mango",            "Frozen",  "Ice Pop",      "6 x 60ml",      180, None, "2025-03-15", 2),
    # Launched in December 2025: appear only in batch_2
    ("Desi Popz Gud Imli",        "Candy",   "Lollipop",     "32g (4 pcs)",   45,  None, "2025-12-05", 5),
    ("Til Gud Chikki Winter Pack", "Chikki", "Bar",          "300g",          249, None, "2025-12-10", 3),
]
PRICE_CHANGES = {  # product name -> new MRP from CUTOFF (captured by the dbt snapshot)
    "Desi Popz Tangy Imli": 45, "Desi Popz Real Aam": 45, "Kaju Katli": 329,
    "Aam Papad": 90, "Peanut Chikki": 55,
}
CATEGORY_SEASON = {  # month multipliers per category
    "Frozen": {1: .3, 2: .5, 3: 1.2, 4: 1.9, 5: 2.1, 6: 1.6, 7: .9, 8: .8, 9: .8, 10: .6, 11: .4, 12: .3},
    "Chikki": {1: 1.6, 2: 1.3, 3: 1, 4: .7, 5: .6, 6: .7, 7: .8, 8: .9, 9: 1, 10: 1.1, 11: 1.4, 12: 1.7},
    "Mithai": {1: .8, 2: .8, 3: 1.1, 4: .8, 5: .8, 6: .8, 7: .8, 8: 1.3, 9: 1, 10: 1.6, 11: 1.7, 12: 1.1},
}

# canonical city, state, region, weight, pincode prefix, is_metro, messy spellings
CITIES = [
    ("Bengaluru", "Karnataka", "South", 18, "560", True, ["Bengaluru", "Bangalore", "bengaluru", "BANGALORE", "Bengaluru "]),
    ("Mumbai", "Maharashtra", "West", 13, "400", True, ["Mumbai", "Bombay", "mumbai"]),
    ("New Delhi", "Delhi", "North", 12, "110", True, ["New Delhi", "Delhi", "delhi", "NEW DELHI"]),
    ("Hyderabad", "Telangana", "South", 8, "500", True, ["Hyderabad", "hyderabad"]),
    ("Chennai", "Tamil Nadu", "South", 7, "600", True, ["Chennai", "Madras"]),
    ("Pune", "Maharashtra", "West", 6, "411", True, ["Pune", "Poona"]),
    ("Kolkata", "West Bengal", "East", 5, "700", True, ["Kolkata", "Calcutta"]),
    ("Gurugram", "Haryana", "North", 5, "122", True, ["Gurugram", "Gurgaon"]),
    ("Ahmedabad", "Gujarat", "West", 4, "380", False, ["Ahmedabad", "Amdavad"]),
    ("Jaipur", "Rajasthan", "North", 3, "302", False, ["Jaipur"]),
    ("Lucknow", "Uttar Pradesh", "North", 3, "226", False, ["Lucknow"]),
    ("Kochi", "Kerala", "South", 3, "682", False, ["Kochi", "Cochin"]),
    ("Mysuru", "Karnataka", "South", 3, "570", False, ["Mysuru", "Mysore"]),
    ("Chandigarh", "Chandigarh", "North", 2, "160", False, ["Chandigarh"]),
    ("Indore", "Madhya Pradesh", "Central", 2, "452", False, ["Indore"]),
    ("Coimbatore", "Tamil Nadu", "South", 2, "641", False, ["Coimbatore"]),
    ("Nagpur", "Maharashtra", "West", 2, "440", False, ["Nagpur"]),
    ("Bhubaneswar", "Odisha", "East", 1, "751", False, ["Bhubaneswar", "Bhubaneshwar"]),
    ("Guwahati", "Assam", "East", 1, "781", False, ["Guwahati", "Gauhati"]),
    ("Visakhapatnam", "Andhra Pradesh", "South", 2, "530", False, ["Visakhapatnam", "Vizag"]),
]
REGION_WAREHOUSE = {"South": "WH-BLR", "West": "WH-MUM", "Central": "WH-MUM", "North": "WH-DEL", "East": "WH-DEL"}

FESTIVALS = {  # date -> (name, demand amplitude in the 2 weeks before)
    date(2024, 3, 25): ("Holi", 0.5), date(2025, 3, 14): ("Holi", 0.5),
    date(2024, 8, 19): ("Raksha Bandhan", 0.7), date(2025, 8, 9): ("Raksha Bandhan", 0.7),
    date(2024, 11, 1): ("Diwali", 1.6), date(2025, 10, 20): ("Diwali", 1.6),
}
MONTH_SEASON = {1: 1.0, 2: .95, 3: 1.05, 4: 1.0, 5: 1.0, 6: .95, 7: .82, 8: .88, 9: .95, 10: 1.1, 11: 1.12, 12: 1.05}
HOUR_P = np.array([1, .5, .3, .2, .2, .3, .8, 1.5, 2.5, 3, 3.5, 4, 4.5, 4, 3.5, 3.5, 4, 5, 6.5, 7.5, 8, 7, 5, 2.5])
HOUR_P = HOUR_P / HOUR_P.sum()


@dataclass
class Channel:
    name: str
    base: float          # orders/day in Jan 2024
    growth: float        # yearly growth
    extra_lines: float   # Poisson mean of lines beyond the first
    extra_qty: float     # Poisson mean of units beyond the first
    cancel: float
    ret: float
    weekend: float
    quick: bool
    commission: float = 0.0


CHANNELS = [
    Channel("website", 14, 0.30, 1.2, 0.6, 0.04, 0.03, 1.15, False),
    Channel("amazon", 22, 0.20, 0.4, 0.4, 0.05, 0.04, 1.05, False, 0.18),
    Channel("flipkart", 12, 0.08, 0.4, 0.4, 0.06, 0.05, 1.05, False, 0.20),
    Channel("blinkit", 9, 0.95, 0.8, 0.5, 0.02, 0.01, 1.25, True, 0.22),
    Channel("zepto", 4, 1.30, 0.8, 0.5, 0.02, 0.01, 1.25, True, 0.22),
    Channel("swiggy_instamart", 6, 0.70, 0.8, 0.5, 0.02, 0.01, 1.25, True, 0.22),
]

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
city_w = np.array([c[3] for c in CITIES], dtype=float)
metro_idx = [i for i, c in enumerate(CITIES) if c[5]]


def pick_city(metro_only: bool = False) -> int:
    if metro_only:
        w = city_w[metro_idx]
        return metro_idx[rng.choice(len(metro_idx), p=w / w.sum())]
    return int(rng.choice(len(CITIES), p=city_w / city_w.sum()))


def messy_city(i: int) -> str:
    """Canonical spelling 80% of the time, a variant otherwise."""
    variants = CITIES[i][6]
    return variants[0] if rng.random() < 0.8 else variants[int(rng.integers(len(variants)))]


def pincode(i: int, null_rate: float = 0.03) -> str | None:
    return None if rng.random() < null_rate else f"{CITIES[i][4]}{int(rng.integers(1, 100)):03d}"


def season(d: date) -> float:
    m = MONTH_SEASON[d.month]
    for f, (_, amp) in FESTIVALS.items():
        delta = (f - d).days
        if -1 <= delta <= 14:
            m += amp * (1 - max(delta, 0) / 15)
    return m


def ts_on(d: date) -> datetime:
    h = int(rng.choice(24, p=HOUR_P))
    return datetime(d.year, d.month, d.day, h, int(rng.integers(60)), int(rng.integers(60)))


def fmt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def timeline(placed: datetime, ch: Channel) -> list[tuple[str, datetime]]:
    ev = [("placed", placed)]
    if rng.random() < ch.cancel:
        ev.append(("cancelled", placed + timedelta(hours=float(rng.uniform(0.2, 20)))))
    else:
        if ch.quick:
            ev.append(("delivered", placed + timedelta(minutes=float(rng.uniform(8, 35)))))
        else:
            shipped = placed + timedelta(hours=float(rng.uniform(6, 40)))
            ev.append(("shipped", shipped))
            ev.append(("delivered", shipped + timedelta(hours=float(rng.uniform(30, 120)))))
        if rng.random() < ch.ret:
            ev.append(("returned", ev[-1][1] + timedelta(days=float(rng.uniform(2, 9)))))
    return [e for e in ev if e[1] <= END_TS]


def status_rows(ev: list[tuple[str, datetime]]) -> list[tuple[int, str, datetime]]:
    """Order-header rows per batch: state as of the cutoff, then the final state."""
    rows = []
    before = [e for e in ev if e[1] < CUTOFF]
    after = [e for e in ev if e[1] >= CUTOFF]
    if before:
        rows.append((1, *before[-1]))
    if after:
        rows.append((2, *after[-1]))
    return rows


def batch_of(ts: datetime | date) -> int:
    ts = ts if isinstance(ts, datetime) else datetime(ts.year, ts.month, ts.day)
    return 1 if ts < CUTOFF else 2


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------
def build_products() -> pd.DataFrame:
    rows = []
    for i, (name, cat, sub, pack, mrp, barcode, launch, pop) in enumerate(PRODUCTS, start=1):
        rows.append(dict(
            sku_id=f"GD-{i:04d}", barcode=barcode or f"89061088990{i:02d}", product_name=name,
            category=cat, sub_category=sub, pack_size=pack, mrp_inr=float(mrp),
            cost_inr=round(mrp * float(rng.uniform(0.42, 0.58)), 2),
            launch_date=date.fromisoformat(launch), popularity=pop,
        ))
    return pd.DataFrame(rows)


def build_promotions() -> pd.DataFrame:
    rows = []
    for f, (fest, _) in sorted(FESTIVALS.items()):
        tag = {"Holi": "HOLI", "Raksha Bandhan": "RAKHI", "Diwali": "DIWALI"}[fest] + str(f.year)[2:]
        s, e = f - timedelta(days=12), f + timedelta(days=1)
        rows += [
            (tag, f"{fest} Sale {f.year} (website)", "website", 20 if fest == "Diwali" else 15, s, e),
            (f"{tag}-AMZ", f"{fest} Deals {f.year} (Amazon)", "amazon", 15, s, e),
            (f"{tag}-FK", f"{fest} Deals {f.year} (Flipkart)", "flipkart", 15, s, e),
            (f"{tag}-QC", f"{fest} Quick Treats {f.year}", "quick_commerce", 10, f - timedelta(days=5), e),
        ]
    for y in (2024, 2025):
        yy = str(y)[2:]
        rows += [
            (f"REPUBLIC{yy}", f"Republic Day Sale {y}", "all", 10, date(y, 1, 20), date(y, 1, 26)),
            (f"FREEDOM{yy}", f"Independence Day Sale {y}", "all", 10, date(y, 8, 10), date(y, 8, 15)),
            (f"MONSOON{yy}", f"Monsoon Munchies {y}", "website", 10, date(y, 7, 1), date(y, 7, 31)),
        ]
    return pd.DataFrame(rows, columns=["promo_code", "promo_name", "channel", "discount_pct", "start_date", "end_date"])


def active_promo(promos: pd.DataFrame, d: date, ch: Channel) -> tuple[str | None, float]:
    targets = {ch.name, "all"} | ({"quick_commerce"} if ch.quick else set())
    m = promos[(promos.start_date <= d) & (promos.end_date >= d) & promos.channel.isin(targets)]
    if m.empty:
        return None, 0.0
    best = m.sort_values("discount_pct", ascending=False).iloc[0]
    return str(best["promo_code"]), float(best["discount_pct"]) / 100


def build_distributors_stores() -> tuple[pd.DataFrame, pd.DataFrame]:
    dist_rows, store_rows = [], []
    did = 0
    city_dists: dict[int, list[str]] = defaultdict(list)
    for ci, c in enumerate(CITIES):
        for _ in range(max(1, round(c[3] / 6))):
            did += 1
            d_id = f"DST-{did:03d}"
            city_dists[ci].append(d_id)
            dist_rows.append(dict(
                distributor_id=d_id,
                distributor_name=f"{fake.last_name()} {rng.choice(['Traders', 'Distributors', 'Enterprises', 'Agencies'])}",
                city=c[0], state=c[1], region=c[2],
                onboarded_date=(date(2021, 1, 1) + timedelta(days=int(rng.integers(0, 1000)))).isoformat(),
            ))
    for s in range(1, 2001):
        ci = pick_city()
        store_rows.append(dict(
            store_id=f"ST-{s:05d}",
            store_name=f"{fake.first_name()} {rng.choice(['Stores', 'General Store', 'Supermart', 'Kirana', 'Sweets'])}",
            store_type=str(rng.choice(["Kirana", "Modern Trade", "Sweet Shop"], p=[.75, .15, .10])),
            distributor_id=str(rng.choice(city_dists[ci])), city=messy_city(ci), state=CITIES[ci][1],
            pincode=pincode(ci), opened_date=(date(2015, 1, 1) + timedelta(days=int(rng.integers(0, 3600)))).isoformat(),
            city_idx=ci,
        ))
    return pd.DataFrame(dist_rows), pd.DataFrame(store_rows)


# --------------------------------------------------------------------------
# Main simulation
# --------------------------------------------------------------------------
def main() -> None:
    products = build_products()
    promos = build_promotions()
    distributors, stores = build_distributors_stores()
    store_w = np.where(stores.store_type == "Modern Trade", 4.0, 1.0)
    store_w = store_w / store_w.sum()
    store_recs = stores.to_dict("records")

    sku_ids = products.sku_id.to_numpy()
    sku_pop = products.popularity.to_numpy()
    sku_barcode = dict(zip(products.sku_id, products.barcode))
    sku_cat = dict(zip(products.sku_id, products.category))
    sku_launch = dict(zip(products.sku_id, products.launch_date))
    base_mrp = dict(zip(products.sku_id, products.mrp_inr))
    new_mrp = {products.loc[products.product_name == n, "sku_id"].item(): float(p) for n, p in PRICE_CHANGES.items()}

    def mrp_at(sku: str, d: date) -> float:
        return new_mrp[sku] if (sku in new_mrp and d >= CUTOFF.date()) else base_mrp[sku]

    def sku_weights(d: date) -> tuple[np.ndarray, np.ndarray]:
        idx = np.array([i for i, s in enumerate(sku_ids) if sku_launch[s] <= d])
        w = np.array([
            sku_pop[i] * CATEGORY_SEASON.get(sku_cat[sku_ids[i]], {}).get(d.month, 1.0)
            * min(1.0, 0.3 + (d - sku_launch[sku_ids[i]]).days / 90)
            for i in idx
        ])
        return idx, w / w.sum()

    customers: list[dict] = []
    ticket_pool: list[int] = []       # customer index repeated per order -> repeat buyers get picked more
    d2c_orders, d2c_items, d2c_returns = [], [], []
    mp_orders, mp_items = [], []
    inv_hdr, inv_lines = [], []
    demand: dict[tuple, int] = defaultdict(int)   # (date, warehouse, sku) -> units
    counters: dict[str, int] = defaultdict(int)

    def new_customer(signup: datetime) -> int:
        ci = pick_city()
        first, last = fake.first_name(), fake.last_name()
        email = f"{first}.{last}{int(rng.integers(1, 999))}@{rng.choice(['gmail.com', 'yahoo.co.in', 'outlook.com', 'rediffmail.com'])}".lower()
        if rng.random() < 0.02:
            email = email.upper()
        num = f"{int(rng.choice([6, 7, 8, 9]))}{int(rng.integers(0, 10**9)):09d}"
        phone = str(rng.choice([f"+91 {num}", num, f"0{num}", f"+91-{num[:5]}-{num[5:]}"], p=[.5, .3, .1, .1]))
        customers.append(dict(
            customer_id=f"C{len(customers) + 1:06d}", full_name=f"{first} {last}", email=email, phone=phone,
            city=messy_city(ci), state=CITIES[ci][1], pincode=pincode(ci), signup_at=fmt(signup),
            acquisition_source=str(rng.choice(["organic", "instagram", "google_ads", "referral", "influencer"], p=[.35, .25, .2, .12, .08])),
            city_idx=ci,
        ))
        return len(customers) - 1

    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    for di, d in enumerate(days):
        s = season(d)
        idx, w = sku_weights(d)
        weekend = d.weekday() >= 5
        p_repeat = 0.18 + 0.27 * di / len(days)

        for ch in CHANNELS:
            lam = ch.base * (1 + ch.growth) ** (di / 365) * s * (ch.weekend if weekend else 1.0)
            day_promo, day_pct = active_promo(promos, d, ch)
            for _ in range(rng.poisson(lam)):
                placed = ts_on(d)
                ev = timeline(placed, ch)
                promo_code, pct = day_promo, day_pct
                if promo_code and rng.random() > (0.45 if ch.name == "website" else 0.6):
                    promo_code, pct = None, 0.0
                k = min(len(idx), 1 + rng.poisson(ch.extra_lines))
                skus = sku_ids[rng.choice(idx, size=k, replace=False, p=w)]

                if ch.name == "website":
                    counters["d2c"] += 1
                    oid = f"D2C-{counters['d2c']:07d}"
                    if ticket_pool and rng.random() < p_repeat:
                        cidx = ticket_pool[int(rng.integers(len(ticket_pool)))]
                    else:
                        cidx = new_customer(placed - timedelta(minutes=float(rng.uniform(1, 600))))
                        ticket_pool.append(cidx)
                    ticket_pool.append(cidx)
                    cust = customers[cidx]
                    ci = cust["city_idx"]
                    subtotal, lines = 0.0, []
                    for ln, sku in enumerate(skus, start=1):
                        qty = 1 + int(rng.poisson(ch.extra_qty))
                        price = mrp_at(sku, d)
                        disc = round(price * qty * pct, 2)
                        subtotal += price * qty - disc
                        price_txt = f"{price:.2f}"
                        r = rng.random()
                        if r < 0.015:
                            price_txt = f"₹{price:.2f}"
                        elif r < 0.03:
                            price_txt = f"Rs. {price:.0f}"
                        lines.append(dict(order_item_id=f"{oid}-{ln}", order_id=oid, sku_id=sku, quantity=qty,
                                          unit_price_inr=price_txt, discount_inr=f"{disc:.2f}"))
                        if ev[-1][0] != "cancelled":
                            demand[(d, REGION_WAREHOUSE[CITIES[ci][2]], sku)] += qty
                    shipping = 0.0 if subtotal >= 499 else 49.0
                    first_batch = None
                    for b, status, upd in status_rows(ev):
                        first_batch = first_batch or b
                        order_ts = fmt(placed) if rng.random() > 0.05 else placed.strftime("%d/%m/%Y %H:%M")
                        d2c_orders.append(dict(
                            order_id=oid, customer_id=cust["customer_id"], order_ts=order_ts, status=status,
                            payment_method=str(rng.choice(["UPI", "Card", "COD", "Wallet"], p=[.55, .2, .18, .07])),
                            promo_code=promo_code, shipping_city=messy_city(ci), shipping_state=CITIES[ci][1],
                            shipping_pincode=pincode(ci), shipping_fee_inr=f"{shipping:.2f}", updated_at=fmt(upd), _batch=b))
                    for line in lines:
                        d2c_items.append({**line, "_batch": first_batch})
                    if ev[-1][0] == "returned":
                        ret_ts = ev[-1][1]
                        for line in lines[: int(rng.integers(1, len(lines) + 1))]:
                            counters["ret"] += 1
                            refund = mrp_at(line["sku_id"], d) * line["quantity"] - float(line["discount_inr"])
                            d2c_returns.append(dict(
                                return_id=f"RET-{counters['ret']:06d}", order_item_id=line["order_item_id"], return_ts=fmt(ret_ts),
                                reason=str(rng.choice(["Damaged in transit", "Expired / near expiry", "Wrong item", "Taste not as expected", "Melted"], p=[.35, .15, .2, .2, .1])),
                                refund_inr=f"{refund:.2f}", _batch=batch_of(ret_ts)))
                else:
                    counters[ch.name] += 1
                    n = counters[ch.name]
                    oid = {
                        "amazon": f"402-{n:07d}-{int(rng.integers(10**6, 10**7))}",
                        "flipkart": f"OD{3300000000 + n * 7}",
                        "blinkit": f"BLK{n:08d}", "zepto": f"ZPT{n:08d}", "swiggy_instamart": f"SIM{n:08d}",
                    }[ch.name]
                    ci = pick_city(metro_only=ch.quick)
                    first_batch = None
                    for b, status, upd in status_rows(ev):
                        first_batch = first_batch or b
                        order_date = placed.strftime("%Y-%m-%dT%H:%M:%S+05:30") if ch.name == "amazon" else fmt(placed)
                        mp_orders.append(dict(
                            marketplace_order_id=oid, channel=ch.name, order_date=order_date,
                            status=status.upper() if ch.name == "flipkart" else status,
                            buyer_city=messy_city(ci), buyer_state=CITIES[ci][1], buyer_pincode=pincode(ci, 0.05),
                            updated_at=fmt(upd), _batch=b))
                    for ln, sku in enumerate(skus, start=1):
                        qty = 1 + int(rng.poisson(ch.extra_qty))
                        price = round(mrp_at(sku, d) * float(rng.uniform(0.85, 1.0)))
                        disc = round(price * qty * pct, 2)
                        seller_sku = sku_barcode[sku] if not ch.quick else str(rng.choice([sku, sku.lower(), f"{sku.lower()} "], p=[.8, .1, .1]))
                        mp_items.append(dict(
                            marketplace_order_id=oid, line_number=ln, seller_sku=seller_sku, quantity=qty,
                            selling_price_inr=f"{price:.2f}", platform_discount_inr=f"{disc:.2f}",
                            commission_inr=f"{(price * qty - disc) * ch.commission:.2f}", _batch=first_batch))
                        if ev[-1][0] != "cancelled":
                            demand[(d, REGION_WAREHOUSE[CITIES[ci][2]], sku)] += qty

        # Offline: distributor -> store invoices (Mon-Sat)
        if d.weekday() < 6:
            for _ in range(rng.poisson(9 * (1.15 ** (di / 365)) * s)):
                counters["inv"] += 1
                inv_id = f"INV-{counters['inv']:06d}"
                st = store_recs[int(rng.choice(len(store_recs), p=store_w))]
                inv_hdr.append(dict(invoice_id=inv_id, distributor_id=st["distributor_id"], store_id=st["store_id"],
                                    invoice_date=d.strftime("%d-%m-%Y"),
                                    payment_terms=str(rng.choice(["Cash", "7 days", "15 days", "30 days"])),
                                    _batch=batch_of(d)))
                k = min(len(idx), int(rng.integers(2, 7)))
                for ln, sku in enumerate(sku_ids[rng.choice(idx, size=k, replace=False, p=w)], start=1):
                    case = 6 if sku_cat[sku] in ("Mithai", "Laddu", "Frozen") else 12
                    qty = case * (1 + int(rng.poisson(0.5)))
                    tp = round(mrp_at(sku, d) * 0.72, 2)
                    inv_lines.append(dict(invoice_id=inv_id, line_no=ln, sku_id=sku, quantity_units=qty, unit_price_inr=f"{tp:.2f}",
                                          scheme_discount_inr=f"{tp * qty * float(rng.choice([0, 0, 0.02, 0.05])):.2f}",
                                          _batch=batch_of(d)))
                    demand[(d, REGION_WAREHOUSE[CITIES[st["city_idx"]][2]], sku)] += qty

    # ---------------- Inventory: daily closing stock per warehouse x SKU ----------------
    inv_rows = []
    for wh in ["WH-BLR", "WH-MUM", "WH-DEL"]:
        for sku in sku_ids:
            series = np.array([demand.get((d, wh, sku), 0) for d in days], dtype=float)
            live = [i for i, d in enumerate(days) if d >= sku_launch[sku]]
            if not live:
                continue
            avg0 = max(5.0, series[live[0]: live[0] + 30].mean())
            stock, pending = avg0 * 35, []
            for i in live:
                trailing = max(5.0, series[max(live[0], i - 30): i + 1].mean())
                stock += sum(q for (arr, q) in pending if arr == i)
                pending = [(a, q) for (a, q) in pending if a > i]
                stock = max(0.0, stock - series[i])
                if stock < trailing * 12 and not pending:
                    pending.append((i + int(rng.integers(4, 10)), round(trailing * 40)))
                inv_rows.append(dict(snapshot_date=days[i].isoformat(), warehouse_id=wh, sku_id=sku,
                                     on_hand_units=int(stock), _batch=batch_of(days[i])))

    # ---------------- Deliberate data-quality issues for dbt to catch ----------------
    d2c_orders_df = pd.DataFrame(d2c_orders)
    dupes = d2c_orders_df[d2c_orders_df._batch == 1].sample(frac=0.005, random_state=SEED)
    d2c_orders_df = pd.concat([d2c_orders_df, dupes], ignore_index=True)           # exact duplicate rows
    d2c_items_df = pd.DataFrame(d2c_items)
    orphan = d2c_items_df[d2c_items_df._batch == 1].sample(5, random_state=SEED).index
    d2c_items_df.loc[orphan, "sku_id"] = "GD-9999"                                   # SKU not in products
    mp_items_df = pd.DataFrame(mp_items)
    mp_items_df = pd.concat([mp_items_df, mp_items_df[mp_items_df._batch == 1].sample(frac=0.003, random_state=SEED)],
                            ignore_index=True)                                       # duplicate lines

    # Products: batch_1 = as of Nov 2025; batch_2 = only changed + newly launched SKUs
    prod_cols = ["sku_id", "barcode", "product_name", "category", "sub_category", "pack_size", "mrp_inr", "cost_inr",
                 "launch_date", "is_active", "updated_at"]
    products["is_active"] = "Y"
    products["updated_at"] = products.launch_date.map(lambda x: f"{max(x, date(2023, 12, 31))} 10:00:00")
    p1 = products[products.launch_date < CUTOFF.date()].copy()
    p1.loc[p1.index[:2], "product_name"] = p1.product_name.iloc[:2] + "  "          # trailing spaces
    p1.loc[p1.product_name == "Imli Goli", "category"] = "candy"                    # inconsistent casing
    changed = products.sku_id.isin(list(new_mrp))
    launched = products.launch_date >= CUTOFF.date()
    p2 = products[changed | launched].copy()
    p2.loc[changed, "mrp_inr"] = p2.loc[changed, "sku_id"].map(new_mrp)
    p2.loc[changed, "updated_at"] = "2025-12-01 09:00:00"
    p2.loc[launched, "updated_at"] = p2.loc[launched, "launch_date"].map(lambda x: f"{x} 09:00:00")
    for df in (p1, p2):
        df["launch_date"] = df.launch_date.astype(str)
        df["mrp_inr"] = df.mrp_inr.map(lambda x: f"{x:.2f}")

    # extra sign-ups that never ordered
    for _ in range(int(len(customers) * 0.15)):
        new_customer(ts_on(START + timedelta(days=int(rng.integers(0, len(days))))))
    customers_df = pd.DataFrame(customers)
    customers_df["_batch"] = customers_df.signup_at.map(lambda x: batch_of(datetime.fromisoformat(x)))

    stores_df = stores.assign(_batch=1)
    distributors_df = distributors.assign(_batch=1)
    promos_df = promos.assign(start_date=promos.start_date.astype(str), end_date=promos.end_date.astype(str), _batch=1)

    # ---------------- Write files ----------------
    tables = [
        # schema, table, dataframe, columns
        ("erp", "products", None, prod_cols),
        ("erp", "distributors", distributors_df, ["distributor_id", "distributor_name", "city", "state", "region", "onboarded_date"]),
        ("erp", "stores", stores_df, ["store_id", "store_name", "store_type", "distributor_id", "city", "state", "pincode", "opened_date"]),
        ("erp", "promotions", promos_df, ["promo_code", "promo_name", "channel", "discount_pct", "start_date", "end_date"]),
        ("erp", "invoices", pd.DataFrame(inv_hdr), ["invoice_id", "distributor_id", "store_id", "invoice_date", "payment_terms"]),
        ("erp", "invoice_lines", pd.DataFrame(inv_lines), ["invoice_id", "line_no", "sku_id", "quantity_units", "unit_price_inr", "scheme_discount_inr"]),
        ("ecom", "customers", customers_df, ["customer_id", "full_name", "email", "phone", "city", "state", "pincode", "signup_at", "acquisition_source"]),
        ("ecom", "orders", d2c_orders_df, ["order_id", "customer_id", "order_ts", "status", "payment_method", "promo_code", "shipping_city", "shipping_state", "shipping_pincode", "shipping_fee_inr", "updated_at"]),
        ("ecom", "order_items", d2c_items_df, ["order_item_id", "order_id", "sku_id", "quantity", "unit_price_inr", "discount_inr"]),
        ("ecom", "returns", pd.DataFrame(d2c_returns), ["return_id", "order_item_id", "return_ts", "reason", "refund_inr"]),
        ("marketplace", "orders", pd.DataFrame(mp_orders), ["marketplace_order_id", "channel", "order_date", "status", "buyer_city", "buyer_state", "buyer_pincode", "updated_at"]),
        ("marketplace", "order_items", mp_items_df, ["marketplace_order_id", "line_number", "seller_sku", "quantity", "selling_price_inr", "platform_discount_inr", "commission_inr"]),
        ("inventory", "stock_daily", pd.DataFrame(inv_rows), ["snapshot_date", "warehouse_id", "sku_id", "on_hand_units"]),
    ]
    counts: dict[tuple[str, str, int], int] = {}
    for schema, table, df, cols in tables:
        for b in (1, 2):
            part = (p1 if b == 1 else p2) if table == "products" else df[df._batch == b]
            if part.empty:
                continue
            path = OUT / f"batch_{b}" / schema / f"{table}.csv.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            part[cols].to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
            counts[(schema, table, b)] = len(part)

    write_sql(tables, counts)

    # ---------------- Summary ----------------
    print(f"{'table':<28}{'batch_1':>10}{'batch_2':>10}")
    for schema, table, _, _ in tables:
        print(f"{schema + '.' + table:<28}{counts.get((schema, table, 1), 0):>10,}{counts.get((schema, table, 2), 0):>10,}")
    total = sum(f.stat().st_size for f in OUT.rglob("*.csv.gz"))
    print(f"\nwritten to {OUT.relative_to(ROOT)}  ({total / 1e6:.1f} MB gzipped)")


# --------------------------------------------------------------------------
# SQL generation
# --------------------------------------------------------------------------
def write_sql(tables, counts) -> None:
    def copy_stmt(schema: str, table: str, cols: list[str], b: int) -> str:
        sel = ",\n    ".join(f"${i}" for i in range(1, len(cols) + 1))
        return (
            f"COPY INTO GODESI_RAW.{schema.upper()}.{table.upper()} (\n    {', '.join(cols)},\n"
            f"    _source_file, _source_row_number, _loaded_at\n)\n"
            f"FROM (\n  SELECT\n    {sel},\n    METADATA$FILENAME, METADATA$FILE_ROW_NUMBER, CURRENT_TIMESTAMP()\n"
            f"  FROM {STAGE}/batch_{b}/{schema}/{table}.csv.gz\n)\n"
            f"FILE_FORMAT = (FORMAT_NAME = '{FILE_FORMAT}')\nON_ERROR = 'ABORT_STATEMENT';\n"
        )

    def verify(cumulative: bool) -> str:
        parts = []
        for schema, table, _, _ in tables:
            n = counts.get((schema, table, 1), 0) + (counts.get((schema, table, 2), 0) if cumulative else 0)
            parts.append(f"SELECT '{schema}.{table}' AS table_name, COUNT(*) AS actual_rows, {n} AS expected_rows "
                         f"FROM GODESI_RAW.{schema.upper()}.{table.upper()}")
        return "\nUNION ALL ".join(parts) + "\nORDER BY table_name;\n"

    n1 = sum(1 for k in counts if k[2] == 1)
    n2 = sum(1 for k in counts if k[2] == 2)
    header = "/* GENERATED by scripts/generate_synthetic_data.py — edit the script, not this file. */\n\n"
    b1 = [header, f"""/* =====================================================================
   GoDesi Analytics — Phase 2b: synthetic data, BATCH 1 (Jan 2024 - Nov 2025)
   ---------------------------------------------------------------------
   1. Run section 1 (file format + stage).
   2. Upload the files from Git Bash (see load/README.md, Phase 2b).
   3. Run sections 2-4.
   ===================================================================== */

USE ROLE LOADER;
USE WAREHOUSE GODESI_WH;

/* ---- 1. File format + stage ------------------------------------------ */
CREATE OR REPLACE FILE FORMAT {FILE_FORMAT}
  TYPE                         = CSV
  FIELD_DELIMITER              = ','
  SKIP_HEADER                  = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  EMPTY_FIELD_AS_NULL          = TRUE
  ENCODING                     = 'UTF8'
  COMPRESSION                  = AUTO
  COMMENT                      = 'Synthetic GoDesi CSV exports';

CREATE STAGE IF NOT EXISTS {STAGE[1:]}
  FILE_FORMAT = {FILE_FORMAT}
  DIRECTORY   = (ENABLE = TRUE)
  ENCRYPTION  = (TYPE = 'SNOWFLAKE_SSE')
  COMMENT     = 'Landing area for synthetic GoDesi files (batch_1/, batch_2/)';

-- >>> Now upload, in Git Bash:
-- >>> .venv/Scripts/python.exe scripts/upload_to_stage.py data/raw/synthetic {STAGE}

/* ---- 2. Check the files arrived: {n1} under batch_1/ and {n2} under batch_2/ */
LIST {STAGE};

/* ---- 3. Raw tables (all VARCHAR) + load batch 1 ---------------------- */
"""]
    for schema, table, _, cols in tables:
        ddl = ",\n".join(f"    {c:<24} VARCHAR" for c in cols)
        b1.append(
            f"CREATE OR REPLACE TABLE GODESI_RAW.{schema.upper()}.{table.upper()} (\n{ddl},\n"
            f"    {'_source_file':<24} VARCHAR,\n    {'_source_row_number':<24} NUMBER,\n    {'_loaded_at':<24} TIMESTAMP_LTZ\n);\n\n"
        )
        b1.append(copy_stmt(schema, table, cols, 1) + "\n")
    b1.append("/* ---- 4. Verify: actual_rows must equal expected_rows on every line */\n" + verify(False))
    (SQL_DIR / "02_load_synthetic_batch_1.sql").write_text("".join(b1), encoding="utf-8")

    b2 = [header, """/* =====================================================================
   GoDesi Analytics — synthetic data, BATCH 2 (December 2025)
   ---------------------------------------------------------------------
   Run this LATER, in Phase 4, after your first dbt build. It appends December
   orders, newer statuses for older orders, product price changes and two new
   SKUs, so you can watch incremental models and snapshots pick up changes.
   The files are already in the stage once you upload data/raw/synthetic.
   ===================================================================== */

USE ROLE LOADER;
USE WAREHOUSE GODESI_WH;

"""]
    for schema, table, _, cols in tables:
        if counts.get((schema, table, 2)):
            b2.append(copy_stmt(schema, table, cols, 2) + "\n")
    b2.append("/* Verify: actual_rows = batch 1 + batch 2 */\n" + verify(True))
    (SQL_DIR / "03_load_synthetic_batch_2.sql").write_text("".join(b2), encoding="utf-8")


if __name__ == "__main__":
    main()
