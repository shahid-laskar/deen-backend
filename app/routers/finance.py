"""Islamic Finance Router"""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from typing import Any
from app.core.dependencies import CurrentUser, DB
from app.schemas.base import MessageResponse
from pydantic import BaseModel

router = APIRouter(prefix="/finance", tags=["finance"])

class ZakatInput(BaseModel):
    nisab_standard: str = "gold"
    assets: dict[str, Any]
    liabilities: dict[str, Any]

class ZakatResponse(BaseModel):
    id: UUID | None = None
    calculation_date: date
    net_zakatable_assets: float
    zakat_due: float
    currency: str

class MortgageInput(BaseModel):
    property_price: float
    deposit: float
    term_years: int
    conventional_rate: float
    islamic_profit_rate: float

class ScreenerInput(BaseModel):
    ticker: str

@router.post("/zakat/calculate", response_model=ZakatResponse)
async def calculate_zakat(payload: ZakatInput, current_user: CurrentUser, db: DB):
    # Mock calculation: Zakat is 2.5% on net assets above nisab.
    # We assume the user inputs amounts in a standard currency.
    def safe_sum(d: dict) -> float:
        total = 0.0
        for v in d.values():
            try:
                total += float(v)
            except (ValueError, TypeError):
                continue
        return total

    total_assets = safe_sum(payload.assets)
    total_liabilities = safe_sum(payload.liabilities)
    
    net_assets = total_assets - total_liabilities
    # Mock nisab value, normally fetched from live metals API
    mock_nisab = 5000.0 if payload.nisab_standard == "gold" else 500.0

    zakat_due = 0.0
    if net_assets >= mock_nisab:
        zakat_due = net_assets * 0.025

    return ZakatResponse(
        calculation_date=date.today(),
        net_zakatable_assets=max(0.0, net_assets),
        zakat_due=zakat_due,
        currency="USD"
    )

@router.post("/screener", response_model=dict)
async def screen_stock(payload: ScreenerInput, current_user: CurrentUser):
    # Mocked Musaffa API response
    status = "halal"
    reason = "Business activity and financial ratios comply with Shariah guidelines."
    if payload.ticker.upper() in ["AAPL", "MSFT"]:
        status = "halal"
    elif payload.ticker.upper() in ["JPM", "BAC"]:
        status = "non-halal"
        reason = "Primary business deeply involves interest (Riba)."
    else:
        status = "doubtful"
        reason = "Financial ratios may borderline exceed allowed debt-to-market cap limits."

    return {
        "ticker": payload.ticker,
        "status": status,
        "reason": reason
    }

@router.post("/mortgage/calculate", response_model=dict)
async def calculate_mortgage(payload: MortgageInput, current_user: CurrentUser):
    # Simplified mock comparison
    loan_amount = payload.property_price - payload.deposit
    months = payload.term_years * 12
    
    # Simple interest formula for illustration purposes
    conv_monthly = (loan_amount * (1 + payload.conventional_rate/100)) / months
    islamic_monthly = (loan_amount * (1 + payload.islamic_profit_rate/100)) / months

    return {
        "conventional": {
            "monthly_payment": round(conv_monthly, 2),
            "total_cost": round(conv_monthly * months, 2),
            "type": "Interest-bearing"
        },
        "islamic": {
            "monthly_payment": round(islamic_monthly, 2),
            "total_cost": round(islamic_monthly * months, 2),
            "type": "Diminishing Musharakah"
        }
    }
