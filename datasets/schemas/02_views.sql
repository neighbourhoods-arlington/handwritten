-- Bağışçı başına özet: filtreleme mantığının temeli
CREATE VIEW donor_summary AS
SELECT
    d.donor_id,
    d.account_number,
    d.first_name,
    d.last_name,
    count(g.gift_id)                                     AS gift_count,
    count(g.gift_id) FILTER (WHERE g.channel = 'direct') AS direct_gift_count,
    sum(g.amount)                                        AS total_given,
    sum(g.amount) FILTER (WHERE g.channel = 'direct')    AS direct_total,
    max(g.gift_date)                                     AS last_gift_date,
    -- Hiç doğrudan bağışı yoksa (yalnızca Raise + Ride) true
    (count(g.gift_id) FILTER (WHERE g.channel = 'direct') = 0) AS raise_ride_only,
    (SELECT max(n.sent_at) FROM thank_you_notes n
      WHERE n.donor_id = d.donor_id AND n.status = 'sent') AS last_note_sent_at
FROM donors d
LEFT JOIN gifts g ON g.donor_id = d.donor_id
GROUP BY d.donor_id;

-- Haftalık aday listesi: her uygun bağışçı için teşekkür edilecek TEK bağış.
-- Eşikler parametre; ekip kendi tanımlarına göre ayarlayabilir.
CREATE OR REPLACE FUNCTION eligible_gifts(
    p_gift_window_days    INT     DEFAULT 30,   -- son kaç gündeki bağışlar
    p_max_amount          NUMERIC DEFAULT 100,  -- "küçük" bağış üst sınırı
    p_max_direct_gifts    INT     DEFAULT 3,    -- "seyrek": ömür boyu doğrudan bağış sayısı
    p_min_days_since_note INT     DEFAULT 180,  -- son gönderilen nottan bu yana en az kaç gün
    p_today               DATE    DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    donor_id          INT,
    gift_id           INT,
    first_name        TEXT,
    last_name         TEXT,
    gift_date         DATE,
    amount            NUMERIC,
    fund              TEXT,
    campaign          TEXT,
    appeal            TEXT,
    receipt_note      TEXT,
    direct_gift_count BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT DISTINCT ON (d.donor_id)
           d.donor_id, g.gift_id, d.first_name, d.last_name, g.gift_date, g.amount,
           g.fund, g.campaign, g.appeal, g.receipt_note, s.direct_gift_count
    FROM donors d
    JOIN gifts g          ON g.donor_id = d.donor_id AND g.channel = 'direct'  -- Raise + Ride dışarıda
    JOIN donor_summary s  ON s.donor_id = d.donor_id
    WHERE g.gift_date BETWEEN p_today - p_gift_window_days AND p_today
      AND g.amount <= p_max_amount
      AND s.direct_gift_count <= p_max_direct_gifts
      AND coalesce(d.address_line, '') <> ''                                   -- posta adresi şart
      -- bu bağış için daha önce (reddedilmiş dahil) not açılmış mı?
      AND NOT EXISTS (SELECT 1 FROM thank_you_notes n WHERE n.gift_id = g.gift_id)
      -- bu bağışçıda bekleyen taslak/onaylı not var mı, veya yakın zamanda not gitti mi?
      AND NOT EXISTS (
            SELECT 1 FROM thank_you_notes n
             WHERE n.donor_id = d.donor_id
               AND (n.status IN ('draft', 'approved')
                    OR (n.status = 'sent'
                        AND n.sent_at::date > p_today - p_min_days_since_note)))
    ORDER BY d.donor_id, g.gift_date DESC, g.amount DESC
$$;
