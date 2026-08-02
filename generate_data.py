import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

rng = np.random.default_rng(42)
random.seed(42)

# ----------------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------------
N_CUSTOMERS = 1000
N_ORDERS = 5000
N_INACTIVE = 100          # customers with zero orders
N_ACTIVE = N_CUSTOMERS - N_INACTIVE

DATE_START = date(2024, 1, 1)
DATE_END = date(2025, 12, 31)
TOTAL_DAYS = (DATE_END - DATE_START).days

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def random_unique_ids(n, low, high):
    return rng.choice(np.arange(low, high), size=n, replace=False)

def rand_date_between(start: date, end: date):
    span = (end - start).days
    if span <= 0:
        return start
    return start + timedelta(days=int(rng.integers(0, span + 1)))

# ----------------------------------------------------------------------------
# CUSTOMERS TABLE
# ----------------------------------------------------------------------------
customer_ids = random_unique_ids(N_CUSTOMERS, 100000, 999999)
rng.shuffle(customer_ids)

first_names_m = ["James","John","Robert","Michael","William","David","Richard","Joseph",
                  "Thomas","Charles","Daniel","Matthew","Anthony","Mark","Paul","Steven",
                  "Andrew","Kenneth","Joshua","Kevin","Brian","George","Timothy","Ronald",
                  "Jason","Edward","Jeffrey","Ryan","Jacob","Gary","Nicholas","Eric","Carlos",
                  "Raj","Wei","Hiroshi","Omar","Liam","Noah","Ethan","Mateo"]
first_names_f = ["Mary","Patricia","Jennifer","Linda","Elizabeth","Barbara","Susan","Jessica",
                  "Sarah","Karen","Lisa","Nancy","Betty","Sandra","Margaret","Ashley","Emily",
                  "Kimberly","Donna","Michelle","Amanda","Melissa","Deborah","Stephanie","Rebecca",
                  "Laura","Priya","Mei","Fatima","Sofia","Olivia","Emma","Ava","Isabella","Mia",
                  "Camila","Ingrid","Yuki","Chen","Aaliyah"]
last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez",
              "Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor",
              "Moore","Jackson","Martin","Lee","Perez","Thompson","White","Harris","Sanchez",
              "Clark","Ramirez","Lewis","Robinson","Walker","Young","Allen","King","Wright",
              "Scott","Torres","Nguyen","Hill","Flores","Green","Adams","Nelson","Baker","Hall",
              "Rivera","Campbell","Mitchell","Carter","Roberts","Patel","Kim","Chen","Singh"]

genders = rng.choice(["Female", "Male", "Non-binary"], size=N_CUSTOMERS, p=[0.49, 0.48, 0.03])
first_names = []
for g in genders:
    if g == "Female":
        first_names.append(random.choice(first_names_f))
    elif g == "Male":
        first_names.append(random.choice(first_names_m))
    else:
        first_names.append(random.choice(first_names_f + first_names_m))
last_names_pick = [random.choice(last_names) for _ in range(N_CUSTOMERS)]

# age: right-skewed, centered ~34, range 18-78
ages = np.clip(rng.gamma(shape=6.0, scale=5.5, size=N_CUSTOMERS) + 16, 18, 78).round().astype(int)

# US-weighted geography with some international presence
geo_pool = [
    ("New York","NY","USA",0.07), ("Los Angeles","CA","USA",0.06), ("Chicago","IL","USA",0.045),
    ("Houston","TX","USA",0.04), ("Phoenix","AZ","USA",0.03), ("Philadelphia","PA","USA",0.028),
    ("San Antonio","TX","USA",0.025), ("San Diego","CA","USA",0.025), ("Dallas","TX","USA",0.03),
    ("Austin","TX","USA",0.025), ("San Jose","CA","USA",0.02), ("Columbus","OH","USA",0.018),
    ("Charlotte","NC","USA",0.018), ("San Francisco","CA","USA",0.025), ("Seattle","WA","USA",0.025),
    ("Denver","CO","USA",0.02), ("Boston","MA","USA",0.022), ("Atlanta","GA","USA",0.025),
    ("Miami","FL","USA",0.03), ("Portland","OR","USA",0.015), ("Las Vegas","NV","USA",0.015),
    ("Nashville","TN","USA",0.015), ("Detroit","MI","USA",0.015), ("Minneapolis","MN","USA",0.015),
    ("Orlando","FL","USA",0.014), ("Toronto","ON","Canada",0.03), ("Vancouver","BC","Canada",0.018),
    ("Montreal","QC","Canada",0.015), ("London","England","UK",0.03), ("Manchester","England","UK",0.012),
    ("Sydney","NSW","Australia",0.018), ("Melbourne","VIC","Australia",0.014),
    ("Berlin","Berlin","Germany",0.015), ("Mexico City","CDMX","Mexico",0.02),
]
geo_names = [g[:3] for g in geo_pool]
geo_weights = np.array([g[3] for g in geo_pool])
geo_weights = geo_weights / geo_weights.sum()
geo_idx = rng.choice(len(geo_names), size=N_CUSTOMERS, p=geo_weights)
cities = [geo_names[i][0] for i in geo_idx]
states = [geo_names[i][1] for i in geo_idx]
countries = [geo_names[i][2] for i in geo_idx]

signup_dates = [rand_date_between(date(2023, 6, 1), date(2025, 11, 1)) for _ in range(N_CUSTOMERS)]

# loyalty tier: earlier signup -> higher chance of higher tier
def loyalty_for_signup(d):
    tenure_days = (date(2025, 12, 31) - d).days
    if tenure_days > 700:
        p = [0.15, 0.30, 0.35, 0.20]
    elif tenure_days > 400:
        p = [0.30, 0.35, 0.25, 0.10]
    elif tenure_days > 150:
        p = [0.50, 0.30, 0.15, 0.05]
    else:
        p = [0.75, 0.18, 0.06, 0.01]
    return rng.choice(["Bronze", "Silver", "Gold", "Platinum"], p=p)

loyalty_tiers = [loyalty_for_signup(d) for d in signup_dates]

acquisition_channels = rng.choice(
    ["Organic Search", "Paid Social", "Email Campaign", "Referral", "Direct", "Affiliate", "Influencer"],
    size=N_CUSTOMERS, p=[0.22, 0.20, 0.13, 0.12, 0.18, 0.08, 0.07]
)

marketing_opt_in = rng.choice([True, False], size=N_CUSTOMERS, p=[0.62, 0.38])

customers = pd.DataFrame({
    "customer_id": customer_ids,
    "first_name": first_names,
    "last_name": last_names_pick,
    "age": ages,
    "gender": genders,
    "email": [f"{fn.lower()}.{ln.lower()}{rng.integers(1,999)}@{random.choice(['gmail.com','yahoo.com','outlook.com','hotmail.com','icloud.com'])}"
              for fn, ln in zip(first_names, last_names_pick)],
    "phone_number": [f"({rng.integers(200,999)}) {rng.integers(200,999)}-{rng.integers(1000,9999)}" for _ in range(N_CUSTOMERS)],
    "signup_date": signup_dates,
    "loyalty_tier": loyalty_tiers,
    "city": cities,
    "state": states,
    "country": countries,
    "acquisition_channel": acquisition_channels,
    "marketing_opt_in": marketing_opt_in,
})

# Introduce realistic missingness
age_missing_idx = rng.choice(N_CUSTOMERS, size=int(N_CUSTOMERS * 0.035), replace=False)
customers.loc[age_missing_idx, "age"] = np.nan

gender_missing_idx = rng.choice(N_CUSTOMERS, size=int(N_CUSTOMERS * 0.02), replace=False)
customers.loc[gender_missing_idx, "gender"] = np.nan

phone_missing_idx = rng.choice(N_CUSTOMERS, size=int(N_CUSTOMERS * 0.06), replace=False)
customers.loc[phone_missing_idx, "phone_number"] = np.nan

# International customers with USA-only state codes cleaned: keep as-is (states are region names)
customers["age"] = customers["age"].astype("Int64")

# ----------------------------------------------------------------------------
# ORDERS TABLE
# ----------------------------------------------------------------------------
active_customers = customers.iloc[:N_ACTIVE].copy()  # first N_ACTIVE will get orders
inactive_customers = customers.iloc[N_ACTIVE:].copy()  # last N_INACTIVE stay order-less

# Repeat-customer skew: number of orders per active customer follows a long tail
# Use a mixture: most customers 1-4 orders, a smaller "VIP" group 8-20 orders
n_active = len(active_customers)
base_counts = rng.negative_binomial(n=2, p=0.35, size=n_active) + 1  # skewed small counts
vip_mask = rng.random(n_active) < 0.08
base_counts[vip_mask] = base_counts[vip_mask] + rng.integers(6, 16, size=vip_mask.sum())

# scale so total ~ N_ORDERS
scale_factor = N_ORDERS / base_counts.sum()
order_counts = np.maximum(1, np.round(base_counts * scale_factor)).astype(int)

# adjust to hit exactly N_ORDERS (loop until totals match, respecting min of 1 order)
diff = N_ORDERS - order_counts.sum()
guard = 0
while diff != 0 and guard < 100000:
    i = rng.integers(0, n_active)
    if diff > 0:
        order_counts[i] += 1
        diff -= 1
    elif diff < 0 and order_counts[i] > 1:
        order_counts[i] -= 1
        diff += 1
    guard += 1

customer_id_for_orders = np.repeat(active_customers["customer_id"].values, order_counts)
signup_for_orders = np.repeat(pd.to_datetime(active_customers["signup_date"]).values, order_counts)
state_for_orders = np.repeat(active_customers["state"].values, order_counts)
country_for_orders = np.repeat(active_customers["country"].values, order_counts)

rng.shuffle(customer_id_for_orders)  # NOTE: shuffle only this would break alignment; do a joint shuffle instead
perm = rng.permutation(len(customer_id_for_orders))
customer_id_for_orders = customer_id_for_orders[perm]
signup_for_orders = signup_for_orders[perm]
state_for_orders = state_for_orders[perm]
country_for_orders = country_for_orders[perm]

n_rows = len(customer_id_for_orders)
assert n_rows == N_ORDERS

order_ids = random_unique_ids(N_ORDERS, 1000000, 9999999)
rng.shuffle(order_ids)

# --- Seasonal order-date generation ---
month_weights = {
    1: 0.7, 2: 0.65, 3: 0.75, 4: 0.8, 5: 0.85, 6: 0.9,
    7: 0.95, 8: 1.05, 9: 1.0, 10: 1.1, 11: 1.55, 12: 1.9
}
days_index = pd.date_range(DATE_START, DATE_END, freq="D")
day_w = np.array([month_weights[d.month] for d in days_index], dtype=float)
# extra bump around Black Friday / Cyber Monday and Dec holidays, dip early Jan
for i, d in enumerate(days_index):
    if d.month == 11 and 22 <= d.day <= 30:
        day_w[i] *= 1.8
    if d.month == 12 and 1 <= d.day <= 20:
        day_w[i] *= 1.3
    if d.month == 1 and d.day <= 10:
        day_w[i] *= 0.6
day_w = day_w / day_w.sum()

order_dates_raw = rng.choice(days_index, size=N_ORDERS, p=day_w)
order_dates = pd.to_datetime(order_dates_raw)

# ensure order_date >= signup_date (customers can't order before signing up)
signup_dt = pd.to_datetime(signup_for_orders)
order_dates = pd.to_datetime(np.where(order_dates < signup_dt,
                                       signup_dt + pd.to_timedelta(rng.integers(0, 30, size=N_ORDERS), unit="D"),
                                       order_dates))
order_dates = pd.to_datetime(np.minimum(order_dates.values, np.datetime64(DATE_END)))

# --- Product catalog ---
catalog = {
    "Electronics": {
        "products": ["Wireless Earbuds", "Bluetooth Speaker", "4K Smart TV", "Laptop Stand",
                     "Noise-Cancelling Headphones", "Smartphone Case", "Portable Charger",
                     "Mechanical Keyboard", "Wireless Mouse", "Streaming Media Player"],
        "price_range": (15, 1200), "qty_lambda": 1.3, "weight": 0.16
    },
    "Clothing": {
        "products": ["Men's Denim Jacket", "Women's Yoga Pants", "Cotton T-Shirt", "Running Shoes",
                     "Wool Sweater", "Summer Dress", "Rain Jacket", "Slim Fit Jeans", "Baseball Cap",
                     "Winter Parka"],
        "price_range": (10, 180), "qty_lambda": 2.0, "weight": 0.18
    },
    "Home & Kitchen": {
        "products": ["Non-Stick Frying Pan", "Stand Mixer", "Air Fryer", "Cotton Bed Sheets",
                     "Ceramic Dinnerware Set", "Vacuum Cleaner", "Memory Foam Pillow",
                     "Coffee Maker", "Cutlery Set", "LED Desk Lamp"],
        "price_range": (12, 350), "qty_lambda": 1.5, "weight": 0.15
    },
    "Books": {
        "products": ["Mystery Novel", "Cookbook: Weeknight Dinners", "Self-Help Guide",
                     "Children's Picture Book", "Science Fiction Epic", "Historical Biography",
                     "Personal Finance 101", "Fantasy Trilogy Box Set", "Graphic Novel", "Poetry Collection"],
        "price_range": (6, 45), "qty_lambda": 2.2, "weight": 0.09
    },
    "Beauty & Personal Care": {
        "products": ["Facial Moisturizer", "Vitamin C Serum", "Electric Toothbrush", "Hair Dryer",
                     "Shampoo & Conditioner Set", "Perfume", "Makeup Palette", "Sunscreen SPF50",
                     "Electric Razor", "Skincare Gift Set"],
        "price_range": (5, 95), "qty_lambda": 1.8, "weight": 0.11
    },
    "Sports & Outdoors": {
        "products": ["Yoga Mat", "Adjustable Dumbbell Set", "Camping Tent", "Insulated Water Bottle",
                     "Mountain Bike Helmet", "Hiking Backpack", "Resistance Bands Set",
                     "Fishing Rod", "Basketball", "Fitness Tracker Watch"],
        "price_range": (10, 300), "qty_lambda": 1.3, "weight": 0.1
    },
    "Toys & Games": {
        "products": ["Building Block Set", "Board Game Classic", "Remote Control Car", "Puzzle 1000pc",
                     "Action Figure", "Plush Teddy Bear", "Card Game Deck", "Educational STEM Kit",
                     "Doll House", "Outdoor Water Blaster"],
        "price_range": (6, 110), "qty_lambda": 1.6, "weight": 0.07
    },
    "Grocery": {
        "products": ["Organic Coffee Beans", "Mixed Nuts Pack", "Extra Virgin Olive Oil",
                     "Protein Bar Box", "Green Tea Bags", "Pasta Variety Pack", "Sparkling Water Case",
                     "Dark Chocolate Bar", "Granola Cereal", "Honey Jar"],
        "price_range": (3, 55), "qty_lambda": 3.0, "weight": 0.08
    },
    "Office Supplies": {
        "products": ["Ballpoint Pen Pack", "Notebook Set", "Desk Organizer", "Printer Paper Ream",
                     "Sticky Notes Pack", "Stapler", "Whiteboard", "Label Maker",
                     "File Folders Pack", "Ergonomic Office Chair"],
        "price_range": (4, 220), "qty_lambda": 2.5, "weight": 0.04
    },
    "Pet Supplies": {
        "products": ["Dog Chew Toy", "Cat Scratching Post", "Pet Food Bowl Set", "Dog Leash",
                     "Aquarium Filter", "Cat Litter Box", "Pet Grooming Brush", "Dog Bed",
                     "Bird Cage", "Training Treats"],
        "price_range": (5, 150), "qty_lambda": 1.7, "weight": 0.02
    },
}

cat_names = list(catalog.keys())
cat_weights = np.array([catalog[c]["weight"] for c in cat_names])
cat_weights = cat_weights / cat_weights.sum()
categories = rng.choice(cat_names, size=N_ORDERS, p=cat_weights)

product_names = []
unit_prices = []
quantities = []
for cat in categories:
    info = catalog[cat]
    product_names.append(random.choice(info["products"]))
    lo, hi = info["price_range"]
    # log-normal-ish price within range, skewed toward the lower end
    raw = rng.gamma(shape=2.0, scale=1.0)
    price = lo + (hi - lo) * min(raw / 6.0, 1.0)
    unit_prices.append(round(price, 2))
    qty = max(1, int(round(rng.poisson(info["qty_lambda"]))) or 1)
    quantities.append(min(qty, 12))

unit_prices = np.array(unit_prices)
quantities = np.array(quantities)

# Holiday season -> more likely to have a discount
months = order_dates.month.values
base_discount_p = np.where(np.isin(months, [11, 12]), 0.55, 0.22)
has_discount = rng.random(N_ORDERS) < base_discount_p
discount_choices = np.array([0, 5, 10, 15, 20, 25, 30])
discount_percent = np.where(
    has_discount,
    rng.choice(discount_choices[1:], size=N_ORDERS),
    0
)

subtotal = (quantities * unit_prices * (1 - discount_percent / 100)).round(2)

shipping_methods = rng.choice(
    ["Standard", "Express", "Next-Day", "Free Pickup"],
    size=N_ORDERS, p=[0.55, 0.25, 0.12, 0.08]
)

def shipping_cost(method, sub):
    if method == "Free Pickup":
        return 0.0
    if sub >= 75:
        base = 0.0 if method == "Standard" else (12.99 if method == "Express" else 24.99)
    else:
        base = {"Standard": 5.99, "Express": 14.99, "Next-Day": 27.99}[method]
    return round(base, 2)

shipping_costs = np.array([shipping_cost(m, s) for m, s in zip(shipping_methods, subtotal)])

# state/country-based tax rate approximation
def tax_rate_for(state, country):
    if country != "USA":
        return {"Canada": 0.13, "UK": 0.20, "Australia": 0.10, "Germany": 0.19, "Mexico": 0.16}.get(country, 0.10)
    no_sales_tax = {"OR", "NV"}  # simplification
    high_tax = {"CA": 0.0825, "NY": 0.08, "IL": 0.0825, "WA": 0.065, "TX": 0.0625}
    if state in no_sales_tax:
        return 0.0
    return high_tax.get(state, 0.06)

tax_rates = np.array([tax_rate_for(s, c) for s, c in zip(state_for_orders, country_for_orders)])
tax_amount = (subtotal * tax_rates).round(2)

total_amount = (subtotal + shipping_costs + tax_amount).round(2)

payment_methods = rng.choice(
    ["Credit Card", "Debit Card", "PayPal", "Apple Pay", "Google Pay", "Gift Card"],
    size=N_ORDERS, p=[0.38, 0.22, 0.20, 0.09, 0.07, 0.04]
)

order_channels = rng.choice(["Website", "Mobile App", "Marketplace"], size=N_ORDERS, p=[0.5, 0.35, 0.15])

# order status: recency-aware
days_from_end = (pd.Timestamp(DATE_END) - order_dates).days.values
status = np.empty(N_ORDERS, dtype=object)
for i, d in enumerate(days_from_end):
    if d <= 3:
        p = [0.05, 0.35, 0.40, 0.05, 0.15]  # delivered, shipped, processing, cancelled, returned(unlikely so soon->0)
        p = [0.05, 0.45, 0.45, 0.05, 0.00]
    elif d <= 10:
        p = [0.45, 0.30, 0.12, 0.06, 0.07]
    else:
        p = [0.78, 0.03, 0.01, 0.08, 0.10]
    status[i] = rng.choice(["Delivered", "Shipped", "Processing", "Cancelled", "Returned"], p=p)

discount_codes_pool = ["WELCOME10", "SAVE20", "HOLIDAY25", "FREESHIP", "VIP15", "FLASH30", "SUMMER10"]
coupon_code = np.where(
    discount_percent > 0,
    rng.choice(discount_codes_pool, size=N_ORDERS),
    None
)

estimated_delivery_days = np.select(
    [shipping_methods == "Next-Day", shipping_methods == "Express", shipping_methods == "Free Pickup"],
    [1, 3, 0],
    default=7
)

# customer rating: mostly present only for delivered orders, with some missingness even then
customer_rating = np.full(N_ORDERS, np.nan)
delivered_mask = status == "Delivered"
rating_present_mask = delivered_mask & (rng.random(N_ORDERS) < 0.65)
customer_rating[rating_present_mask] = rng.choice([1, 2, 3, 4, 5], size=rating_present_mask.sum(),
                                                   p=[0.03, 0.05, 0.12, 0.35, 0.45])

return_reason_pool = ["Wrong Size", "Defective Item", "Not as Described", "Changed Mind", "Arrived Late", "Better Price Found"]
return_reason = np.where(
    status == "Returned",
    rng.choice(return_reason_pool, size=N_ORDERS),
    None
)

orders = pd.DataFrame({
    "order_id": order_ids,
    "customer_id": customer_id_for_orders,
    "order_date": order_dates,
    "product_category": categories,
    "product_name": product_names,
    "quantity": quantities,
    "unit_price": unit_prices,
    "discount_percent": discount_percent,
    "subtotal": subtotal,
    "shipping_cost": shipping_costs,
    "tax_amount": tax_amount,
    "total_amount": total_amount,
    "payment_method": payment_methods,
    "order_status": status,
    "shipping_method": shipping_methods,
    "order_channel": order_channels,
    "coupon_code": coupon_code,
    "estimated_delivery_days": estimated_delivery_days,
    "customer_rating": customer_rating,
    "return_reason": return_reason,
})

# A few realistic missing values sprinkled elsewhere
ship_missing_idx = rng.choice(N_ORDERS, size=int(N_ORDERS * 0.01), replace=False)
orders.loc[ship_missing_idx, "shipping_method"] = np.nan

payment_missing_idx = rng.choice(N_ORDERS, size=int(N_ORDERS * 0.008), replace=False)
orders.loc[payment_missing_idx, "payment_method"] = np.nan

orders["order_date"] = orders["order_date"].dt.date

# sort orders by order_date for readability, but keep IDs random/non-sequential
orders = orders.sort_values("order_date").reset_index(drop=True)

# ----------------------------------------------------------------------------
# SAVE
# ----------------------------------------------------------------------------
customers = customers.sort_values("customer_id").reset_index(drop=True)

customers.to_csv("/mnt/user-data/outputs/customers.csv", index=False)
orders.to_csv("/mnt/user-data/outputs/orders.csv", index=False)

print("Customers:", customers.shape)
print("Orders:", orders.shape)
print("Customers with no orders:", N_CUSTOMERS - orders['customer_id'].nunique())
print(orders.head(3).to_string())
print(customers.head(3).to_string())
