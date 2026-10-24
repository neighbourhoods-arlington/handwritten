import hashlib
import csv
import io
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.donor import Donor
from app.models.gift import Gift
from app.models.import_batch import ImportBatch

async def process_and_save_upload(db: AsyncSession, file_content: bytes, filename: str):
    decoded = file_content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    # 1. Create Import Batch record
    batch = ImportBatch(
        source_file=filename,
        rows_read=0,
        donors_inserted=0,
        gifts_inserted=0
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    rows_read = 0
    donors_inserted = 0
    gifts_inserted = 0

    for row in reader:
        rows_read += 1
        
        account_number = row.get("account_number")
        first_name = row.get("first_name")
        last_name = row.get("last_name")
        email = row.get("email")
        
        if not account_number or not first_name or not last_name:
            continue

        # Find donor using select()
        result = await db.execute(select(Donor).filter(Donor.account_number == account_number))
        donor = result.scalars().first()

        if not donor:
            donor = Donor(
                account_number=account_number,
                first_name=first_name,
                last_name=last_name,
                email=email,
                address_line=row.get("address_line"),
                city=row.get("city"),
                state=row.get("state"),
                zip=row.get("zip")
            )
            db.add(donor)
            await db.commit()
            await db.refresh(donor)
            donors_inserted += 1

        # Parse date and amount properly to prevent type mismatch errors
        gift_date_str = row.get("gift_date")
        amount_str = row.get("amount")

        gift_date = None
        if gift_date_str:
            try:
                gift_date = datetime.strptime(gift_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                continue

        amount = None
        if amount_str:
            try:
                amount = float(amount_str)
            except ValueError:
                continue

        if gift_date and amount:
            # Add gift data (using source_hash to prevent duplicates)
            raw_hash_str = f"{account_number}{gift_date_str}{amount_str}"
            source_hash = hashlib.sha256(raw_hash_str.encode('utf-8')).hexdigest()

            gift_result = await db.execute(select(Gift).filter(Gift.source_hash == source_hash))
            existing_gift = gift_result.scalars().first()

            if not existing_gift:
                gift = Gift(
                    donor_id=donor.donor_id,
                    gift_date=gift_date,
                    amount=amount,
                    fund=row.get("fund"),
                    campaign=row.get("campaign"),
                    appeal=row.get("appeal"),
                    payment_method=row.get("payment_method"),
                    receipt_note=row.get("receipt_note"),
                    source_hash=source_hash,
                    batch_id=batch.batch_id
                )
                db.add(gift)
                await db.commit()
                gifts_inserted += 1

    # Update batch statistics
    batch.rows_read = rows_read
    batch.donors_inserted = donors_inserted
    batch.gifts_inserted = gifts_inserted
    await db.commit()

    return {
        "status": "success",
        "batch_id": batch.batch_id,
        "rows_read": rows_read,
        "donors_inserted": donors_inserted,
        "gifts_inserted": gifts_inserted
    }