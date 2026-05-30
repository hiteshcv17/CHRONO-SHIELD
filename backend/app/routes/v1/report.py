import os
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.report import ReportResponse, ReportCreate
from app.services.report_service import ReportService, STATIC_REPORTS_DIR
from app.core.auth import require_analyst

router = APIRouter(dependencies=[Depends(require_analyst)])


@router.get("", response_model=List[ReportResponse], status_code=status.HTTP_200_OK)
async def list_generated_reports(
    limit: int = Query(50, ge=1, le=100, description="Log retrieve limit"),
    db: AsyncSession = Depends(get_db_session),
) -> List[ReportResponse]:
    """
    Retrieve all compiled Daily/Weekly executive reports.
    """
    return await ReportService.get_reports(db, limit=limit)


@router.post(
    "/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
async def trigger_report_compilation(
    payload: ReportCreate, db: AsyncSession = Depends(get_db_session)
) -> ReportResponse:
    """
    Queue and compile a new executive platform report.
    Gathers temporal anomalies, prioritize alert counters, and sector health statistics.
    """
    if payload.start_date >= payload.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be strictly before end date.",
        )
    return await ReportService.generate_executive_report(
        db,
        report_type=payload.report_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )


@router.get("/{report_id}/download/{export_format}", status_code=status.HTTP_200_OK)
async def download_compiled_report(
    report_id: str,
    export_format: Literal["pdf", "csv"],
    db: AsyncSession = Depends(get_db_session),
):
    """
    Download a compiled report package in PDF or CSV format.
    """
    reports = await ReportService.get_reports(db)
    target = next((r for r in reports if r.id == report_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found.",
        )

    file_extension = "pdf" if export_format == "pdf" else "csv"
    file_path = os.path.join(STATIC_REPORTS_DIR, f"{report_id}.{file_extension}")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report package file {report_id}.{file_extension} not found on server disk.",
        )

    media_type = "application/pdf" if export_format == "pdf" else "text/csv"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"chronoshield_report_{report_id}.{file_extension}",
    )
