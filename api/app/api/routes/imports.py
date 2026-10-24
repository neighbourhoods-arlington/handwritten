from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.services.import_service import process_and_save_upload

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.post("/")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    try:
        content = await file.read()
        # process_and_save_upload artık async olduğu için await ekledik:
        result = await process_and_save_upload(db, content, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
