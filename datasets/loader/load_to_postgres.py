#!/usr/bin/env python3
"""Bloomerang export CSV'sini Postgres'e yükler.

- Yeniden çalıştırmak güvenlidir: aynı bağış (source_hash) ikinci kez eklenmez.
- Bağışçılar account_number ile upsert edilir; boş gelen alan eski değeri silmez.
- Gerçek export başlıkları farklıysa yalnızca COLUMN_MAP değiştirilir.
"""
import argparse
import csv
import hashlib
import os
import re
import sys
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2.extras import execute_values

# CSV başlığı -> iç alan adı
COLUMN_MAP = {
    "Account Number": "account_number", "First Name": "first_name", "Last Name": "last_name",
    "Email": "email", "Address": "address_line", "City": "city", "State": "state", "Zip": "zip",
    "Date": "gift_date", "Amount": "amount", "Fund": "fund", "Campaign": "campaign",
    "Appeal": "appeal", "Method": "payment_method", "Note": "receipt_note",
}
REQUIRED_HEADERS = ["Account Number", "First Name", "Last Name", "Date", "Amount"]
DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y")


def connect(dsn, tries=20):
    for i in range(1, tries + 1):
        try:
            return psycopg2.connect(dsn)
        except psycopg2.OperationalError as e:
            print(f"Veritabanı hazır değil ({i}/{tries}): {str(e).strip()}")
            time.sleep(2)
    sys.exit("Veritabanına bağlanılamadı.")


def parse_date(s):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"tanınmayan tarih: {s!r}")


def parse_amount(s):
    try:
        value = Decimal(re.sub(r"[^0-9.\-]", "", s))
    except InvalidOperation:
        raise ValueError(f"tanınmayan tutar: {s!r}")
    if value <= 0:
        raise ValueError(f"tutar pozitif değil: {s!r}")
    return value


def read_export(path):
    rows, bad = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [h for h in REQUIRED_HEADERS if h not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"CSV'de zorunlu sütun(lar) yok: {missing}. COLUMN_MAP'i kontrol edin.")
        for line_no, raw in enumerate(reader, start=2):
            r = {internal: (raw.get(header) or "").strip() for header, internal in COLUMN_MAP.items()}
            try:
                if not r["account_number"]:
                    raise ValueError("hesap numarası boş")
                r["gift_date"] = parse_date(r["gift_date"])
                r["amount"] = parse_amount(r["amount"])
                rows.append(r)
            except ValueError as e:
                bad.append((line_no, str(e)))
    return rows, bad


def gift_hash(r):
    parts = [r["account_number"], r["gift_date"].isoformat(), str(r["amount"]),
             r["campaign"], r["fund"], r["payment_method"]]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def load_export(conn, path):
    rows, bad = read_export(path)
    for line_no, msg in bad[:10]:
        print(f"  atlandı (satır {line_no}): {msg}")
    if len(bad) > 10:
        print(f"  ... ve {len(bad) - 10} satır daha")

    with conn, conn.cursor() as cur:
        cur.execute("INSERT INTO import_batches (source_file, rows_read) VALUES (%s, %s) RETURNING batch_id",
                    (os.path.basename(path), len(rows)))
        batch_id = cur.fetchone()[0]

        # Dosya tarihe göre sıralıysa son satır = en güncel iletişim bilgisi
        latest = {r["account_number"]: r for r in rows}
        donor_vals = [(r["account_number"], r["first_name"], r["last_name"], r["email"] or None,
                       r["address_line"] or None, r["city"] or None, r["state"] or None, r["zip"] or None)
                      for r in latest.values()]
        res = execute_values(cur, """
            INSERT INTO donors (account_number, first_name, last_name, email, address_line, city, state, zip)
            VALUES %s
            ON CONFLICT (account_number) DO UPDATE SET
                first_name   = EXCLUDED.first_name,
                last_name    = EXCLUDED.last_name,
                email        = COALESCE(EXCLUDED.email, donors.email),
                address_line = COALESCE(EXCLUDED.address_line, donors.address_line),
                city         = COALESCE(EXCLUDED.city, donors.city),
                state        = COALESCE(EXCLUDED.state, donors.state),
                zip          = COALESCE(EXCLUDED.zip, donors.zip),
                updated_at   = now()
            RETURNING donor_id, account_number, (xmax = 0) AS inserted
        """, donor_vals, page_size=1000, fetch=True)
        ids = {acct: donor_id for donor_id, acct, _ in res}
        donors_inserted = sum(1 for _, _, ins in res if ins)

        gift_vals = [(ids[r["account_number"]], r["gift_date"], r["amount"], r["fund"] or None,
                      r["campaign"] or None, r["appeal"] or None, r["payment_method"] or None,
                      r["receipt_note"] or None, gift_hash(r), batch_id) for r in rows]
        inserted = execute_values(cur, """
            INSERT INTO gifts (donor_id, gift_date, amount, fund, campaign, appeal,
                               payment_method, receipt_note, source_hash, batch_id)
            VALUES %s ON CONFLICT (source_hash) DO NOTHING RETURNING gift_id
        """, gift_vals, page_size=1000, fetch=True)

        cur.execute("UPDATE import_batches SET donors_inserted = %s, gifts_inserted = %s WHERE batch_id = %s",
                    (donors_inserted, len(inserted), batch_id))
    print(f"Export: {len(rows)} satır okundu, {donors_inserted} yeni bağışçı, "
          f"{len(inserted)} yeni bağış ({len(rows) - len(inserted)} zaten vardı), {len(bad)} satır atlandı.")


def load_history(conn, path):
    """Daha önce gönderilmiş notları 'sent' olarak kaydeder (geçmiş alıcı takibi için)."""
    n = 0
    with open(path, newline="", encoding="utf-8") as f, conn, conn.cursor() as cur:
        for row in csv.DictReader(f):
            cur.execute("""
                INSERT INTO thank_you_notes
                    (donor_id, gift_id, batch_week, body, status, approved_by, approved_at, sent_at)
                SELECT d.donor_id, g.gift_id, date_trunc('week', %(sent)s::date)::date, %(body)s,
                       'sent', %(by)s, %(sent)s::timestamptz, %(sent)s::timestamptz
                FROM donors d
                JOIN LATERAL (SELECT gift_id FROM gifts
                               WHERE donor_id = d.donor_id AND channel = 'direct'
                               ORDER BY gift_date ASC LIMIT 1) g ON true
                WHERE d.account_number = %(acct)s
                ON CONFLICT DO NOTHING
            """, {"sent": row["sent_at"], "body": row["body"], "by": row["approved_by"],
                  "acct": row["account_number"]})
            n += cur.rowcount
    print(f"Geçmiş: {n} gönderilmiş not kaydedildi.")


def print_summary(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT (SELECT count(*) FROM donors), (SELECT count(*) FROM gifts),
                              (SELECT count(*) FROM donor_summary WHERE raise_ride_only),
                              (SELECT count(*) FROM thank_you_notes WHERE status = 'sent'),
                              (SELECT count(*) FROM eligible_gifts())""")
        donors, gifts, rr_only, sent, eligible = cur.fetchone()
    print(f"\nÖzet: {donors} bağışçı, {gifts} bağış | yalnızca Raise + Ride: {rr_only} | "
          f"gönderilmiş not: {sent}\nBu hafta varsayılan eşiklerle aday sayısı: {eligible}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Bloomerang export CSV yolu")
    ap.add_argument("--history-csv", help="(isteğe bağlı) geçmiş gönderilmiş notlar CSV'si")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"), help="varsayılan: $DATABASE_URL")
    args = ap.parse_args()
    if not args.dsn:
        sys.exit("DATABASE_URL tanımlı değil.")

    conn = connect(args.dsn)
    load_export(conn, args.csv)
    if args.history_csv and os.path.exists(args.history_csv):
        load_history(conn, args.history_csv)
    print_summary(conn)
    conn.close()


if __name__ == "__main__":
    main()
