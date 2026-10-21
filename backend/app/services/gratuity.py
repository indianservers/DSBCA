from decimal import Decimal, ROUND_HALF_UP


def gratuity(monthly_basic: Decimal, years: Decimal):
    if monthly_basic <= 0 or years < 0 or years > 80:
        raise ValueError("Basic salary must be positive; service must be 0–80 years")
    daily = monthly_basic / 30
    first = daily * 21 * min(years, Decimal(5)) if years >= 1 else Decimal(0)
    later = daily * 30 * max(years - 5, Decimal(0)) if years >= 1 else Decimal(0)
    rounded = lambda x: str(x.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
    return {
        "first_five": rounded(first),
        "later_years": rounded(later),
        "total": rounded(min(first + later, monthly_basic * 24)),
        "assumptions": "Standard UAE private-sector foreign full-time worker; eligible service excluding unpaid absence; no DIFC/ADGM or alternative savings scheme. Two-year basic wage cap applied.",
    }
