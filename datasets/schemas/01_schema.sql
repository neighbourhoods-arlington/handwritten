-- Phoenix Bikes: küçük bağışçı teşekkür notları
-- Tüm veri kurgusaldır. Gerçek bağışçı verisi yüklemeden önce erişim/yedekleme planını düşünün.

CREATE TABLE import_batches (
    batch_id        SERIAL PRIMARY KEY,
    source_file     TEXT        NOT NULL,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_read       INT         NOT NULL DEFAULT 0,
    donors_inserted INT         NOT NULL DEFAULT 0,
    gifts_inserted  INT         NOT NULL DEFAULT 0
);

CREATE TABLE donors (
    donor_id       SERIAL PRIMARY KEY,
    account_number TEXT        NOT NULL UNIQUE,   -- Bloomerang hesap numarası
    first_name     TEXT        NOT NULL,
    last_name      TEXT        NOT NULL,
    email          TEXT,
    address_line   TEXT,
    city           TEXT,
    state          TEXT,
    zip            TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE gifts (
    gift_id        SERIAL PRIMARY KEY,
    donor_id       INT           NOT NULL REFERENCES donors(donor_id) ON DELETE CASCADE,
    gift_date      DATE          NOT NULL,
    amount         NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    fund           TEXT,
    campaign       TEXT,
    appeal         TEXT,
    payment_method TEXT,
    receipt_note   TEXT,          -- bağışçının notu / anma-onur notu vb.
    -- Raise + Ride kampanyası "raise_ride", geri kalanı "direct" sayılır.
    -- Bloomerang'daki gerçek kampanya adı farklıysa sadece bu ifadeyi değiştirin.
    channel        TEXT GENERATED ALWAYS AS (
                       CASE WHEN lower(campaign) LIKE 'raise + ride%'
                            THEN 'raise_ride' ELSE 'direct' END
                   ) STORED,
    -- Aynı export tekrar yüklenirse aynı bağış ikinci kez eklenmez
    source_hash    TEXT          NOT NULL UNIQUE,
    batch_id       INT           REFERENCES import_batches(batch_id)
);

CREATE INDEX gifts_donor_idx ON gifts (donor_id);
CREATE INDEX gifts_date_idx  ON gifts (gift_date);

CREATE TABLE thank_you_notes (
    note_id     SERIAL PRIMARY KEY,
    donor_id    INT  NOT NULL REFERENCES donors(donor_id) ON DELETE CASCADE,
    gift_id     INT  REFERENCES gifts(gift_id) ON DELETE SET NULL,
    batch_week  DATE NOT NULL,                      -- notun ait olduğu haftanın pazartesisi
    body        TEXT,
    status      TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'approved', 'rejected', 'sent')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    sent_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Personel onayı olmadan "approved" veya "sent" olamaz
    CONSTRAINT approval_required
        CHECK (status NOT IN ('approved', 'sent') OR approved_by IS NOT NULL)
);

-- Aynı bağış için (reddedilenler hariç) tek not
CREATE UNIQUE INDEX one_active_note_per_gift
    ON thank_you_notes (gift_id) WHERE status <> 'rejected';
CREATE INDEX notes_donor_idx ON thank_you_notes (donor_id, status);
