#!/usr/bin/env python3
"""Kurgusal Bloomerang export'u üretir. Gerçek kişi/veri yoktur (e-postalar example.com).

Veri, filtrenin her kuralını sınayacak şekilde bilerek karışık kurulur:
  A  küçük + seyrek doğrudan bağışçı (24 yakın tarihli, 31 eski)   -> aday / aday değil
  B  yalnızca Raise + Ride                                         -> HARİÇ
  C  Raise + Ride + küçük doğrudan bağış                           -> aday
  D  aylık düzenli (sık) bağışçı                                   -> HARİÇ (seyrek değil)
  E  yakın zamanda zaten not gönderilmiş                           -> HARİÇ (geçmiş kaydı)
  F  tek seferlik orta boy bağış (100$ üstü)                       -> HARİÇ (küçük değil)
Ayrıca birkaç bağışçının posta adresi boştur (el yazısı not gidemez).

Tarihler "bugüne göre" üretilir; bu yüzden dosya varsa yeniden üretilmez (--force ile zorlanır),
aksi halde aynı bağışlar kaydırılmış tarihlerle ikinci kez yüklenirdi.
"""
import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(42)
TODAY = date.today()

FIRST = ["Maya", "Luis", "Priya", "Jamal", "Elena", "Tyrone", "Sofia", "Kenji", "Aaliyah", "Marcus",
         "Rosa", "Daniel", "Naomi", "Hector", "Grace", "Omar", "Lucia", "Ethan", "Imani", "Carlos",
         "Hannah", "Diego", "Tamika", "Noah", "Alma", "Victor", "Brianna", "Mateo", "Leah", "Andre",
         "Gabriela", "Wes", "Camila", "Isaiah", "Yuki", "Rafael", "Dana", "Jonah", "Marisol", "Theo"]
LAST = ["Alvarez", "Brooks", "Chen", "Delgado", "Ellison", "Fischer", "Garcia", "Hawkins", "Ibarra",
        "Jackson", "Kim", "Lopez", "Mitchell", "Nguyen", "Ortiz", "Patel", "Quintero", "Reyes",
        "Sandoval", "Thompson", "Underwood", "Vega", "Whitaker", "Xiong", "Young", "Zamora",
        "Baker", "Castillo", "Dawson", "Escobar", "Flores", "Gonzales", "Harris", "Jimenez",
        "Kowalski", "Lindgren", "Morales", "Navarro", "Okafor", "Perez"]
STREETS = ["E Roosevelt St", "N Central Ave", "W Camelback Rd", "S Mill Ave", "E Apache Blvd",
           "N 7th St", "W McDowell Rd", "E Thomas Rd", "S 16th St", "N Scottsdale Rd",
           "W Indian School Rd", "E University Dr", "S Dobson Rd", "N 24th St"]
CITIES = [("Phoenix", ["85003", "85008", "85016", "85020"]), ("Tempe", ["85281", "85282"]),
          ("Mesa", ["85201", "85204"]), ("Scottsdale", ["85251"]),
          ("Glendale", ["85301"]), ("Chandler", ["85224"])]

SMALL = [10, 15, 20, 25, 25, 30, 35, 40, 50, 50, 60, 75]
NOTES = ["In memory of my dad, who taught me to ride", "Keep up the great work!",
         "I got my first bike fixed at your shop", "Happy birthday to my niece Maya!",
         "I ride to work every day, thank you", "For the kids' Earn-a-Bike classes"]
FUNDS = ["General Operating", "Earn-a-Bike Youth Program", "Community Bike Shop"]

_used_names = set()
_counter = 0


def new_donor(blank_address=False):
    global _counter
    while True:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        if (first, last) not in _used_names:
            _used_names.add((first, last))
            break
    _counter += 1
    city, zips = rng.choice(CITIES)
    email = f"{first}.{last}{rng.randint(1, 99)}@example.com".lower() if rng.random() > 0.12 else ""
    return {
        "Account Number": f"PB-{_counter:05d}", "First Name": first, "Last Name": last, "Email": email,
        "Address": "" if blank_address else f"{rng.randint(100, 9899)} {rng.choice(STREETS)}",
        "City": city, "State": "AZ", "Zip": rng.choice(zips),
    }


def direct_gift(gdate, amount=None):
    """Bağış tarihine uygun doğrudan (Raise + Ride dışı) kampanya seç."""
    seasonal = {3: "Spring Appeal", 4: "Spring Appeal", 10: "Fall Appeal",
                11: "Giving Tuesday", 12: "Year-End Appeal"}
    if gdate.month in seasonal and rng.random() < 0.6:
        campaign, appeal = f"{seasonal[gdate.month]} {gdate.year}", "Mail Appeal"
        method = rng.choice(["Check", "Credit Card"])
    elif rng.random() < 0.1:
        campaign, appeal, method = "Shop Donation Jar", "In-Person", "Cash"
    else:
        campaign, appeal = "Online Giving", "Website Donate Page"
        method = rng.choice(["Credit Card", "Credit Card", "PayPal"])
    return {"Date": gdate, "Amount": amount if amount is not None else rng.choice(SMALL),
            "Fund": rng.choice(FUNDS), "Campaign": campaign, "Appeal": appeal, "Method": method,
            "Note": rng.choice(NOTES) if rng.random() < 0.2 else ""}


def raise_ride_gift(amount=None):
    return {"Date": TODAY - timedelta(days=rng.randint(5, 70)),
            "Amount": amount if amount is not None else rng.choice([25, 50, 75, 100, 150, 250]),
            "Fund": "Raise + Ride Event", "Campaign": "Raise + Ride 2026",
            "Appeal": "Peer-to-Peer Fundraiser", "Method": "Credit Card",
            "Note": "Sponsoring a friend's ride" if rng.random() < 0.3 else ""}


def ago(lo, hi):
    return TODAY - timedelta(days=rng.randint(lo, hi))


def build():
    rows, history = [], []

    def add(donor, gifts):
        rows.extend({**donor, **g} for g in gifts)

    # A: küçük + seyrek. 24 yakın tarihli (2'si adressiz), 31 eski
    for i in range(24):
        d = new_donor(blank_address=i in (5, 17))
        gifts = [direct_gift(ago(1, 27))]
        if rng.random() < 0.4:
            gifts.append(direct_gift(ago(60, 600)))
        add(d, gifts)
    for _ in range(31):
        d = new_donor()
        add(d, [direct_gift(ago(40, 700)) for _ in range(rng.randint(1, 3))])

    # B: yalnızca Raise + Ride (HARİÇ)
    for _ in range(20):
        add(new_donor(), [raise_ride_gift() for _ in range(rng.randint(1, 2))])

    # C: Raise + Ride ve küçük doğrudan bağış (aday)
    for _ in range(10):
        add(new_donor(), [raise_ride_gift(), direct_gift(ago(1, 27))])

    # D: aylık düzenli bağışçılar (HARİÇ, seyrek değil)
    for _ in range(10):
        d = new_donor()
        amt = rng.choice([25, 50, 100])
        months = rng.randint(6, 12)
        add(d, [{"Date": TODAY - timedelta(days=30 * m + rng.randint(0, 3)), "Amount": amt,
                 "Fund": "General Operating", "Campaign": "Monthly Giving",
                 "Appeal": "Recurring", "Method": "Credit Card", "Note": ""}
                for m in range(months)])

    # E: yakın zamanda not gönderilmiş (HARİÇ). Eski bağış + 60 gün önce giden not + yeni bağış
    for _ in range(10):
        d = new_donor()
        add(d, [direct_gift(ago(70, 80)), direct_gift(ago(1, 20))])
        history.append({"account_number": d["Account Number"],
                        "sent_at": (TODAY - timedelta(days=rng.randint(55, 65))).isoformat(),
                        "approved_by": "Demo Staff",
                        "body": f"Dear {d['First Name']}, thank you for your gift to Phoenix Bikes. (fake history)"})

    # F: tek seferlik orta boy bağış (HARİÇ, küçük değil)
    for _ in range(6):
        add(new_donor(), [direct_gift(ago(1, 27), amount=rng.choice([150, 200, 250, 300, 400]))])

    rows.sort(key=lambda r: r["Date"])  # son satır = en güncel; yükleyici iletişim bilgisini ondan alır
    return rows, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data", help="CSV'lerin yazılacağı klasör")
    ap.add_argument("--force", action="store_true", help="dosya varsa da yeniden üret")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    export, hist = out / "bloomerang_export_fake.csv", out / "past_notes_fake.csv"
    if export.exists() and not args.force:
        print(f"{export} zaten var, yeniden üretilmedi (--force ile üretilir).")
        return

    rows, history = build()
    fields = ["Account Number", "First Name", "Last Name", "Email", "Address", "City", "State", "Zip",
              "Date", "Amount", "Fund", "Campaign", "Appeal", "Method", "Note"]
    with open(export, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["Date"] = r["Date"].strftime("%m/%d/%Y")  # Bloomerang tarzı
            r["Amount"] = f"${r['Amount']:.2f}"
            w.writerow(r)
    with open(hist, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["account_number", "sent_at", "approved_by", "body"])
        w.writeheader()
        w.writerows(history)
    print(f"{len(rows)} bağış satırı, {_counter} bağışçı, {len(history)} geçmiş not -> {out}")


if __name__ == "__main__":
    main()
