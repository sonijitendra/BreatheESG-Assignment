from decimal import Decimal
from django.db.models import Q
from ..models import EmissionFactor

def get_emission_factor(tenant, category: str, subcategory: str, activity_date, region: str = ''):
    """
    Looks up the best matching emission factor.
    First checks tenant-specific factors, then falls back to system defaults (tenant=None).
    Validates date range (valid_from <= activity_date <= valid_to).
    """
    if not activity_date:
        raise ValueError("Activity date is required for emission factor lookup.")

    # Base query for date range compatibility
    base_query = Q(
        category=category,
        subcategory=subcategory,
        valid_from__lte=activity_date
    ) & (Q(valid_to__isnull=True) | Q(valid_to__gte=activity_date))

    # 1. Tenant-specific factor
    if tenant:
        tenant_factors = EmissionFactor.objects.filter(base_query, tenant=tenant)
        if region:
            region_factor = tenant_factors.filter(region__iexact=region).first()
            if region_factor:
                return region_factor
        # Fallback to no-region or first matching tenant factor
        tenant_factor = tenant_factors.filter(Q(region='') | Q(region__isnull=True)).first() or tenant_factors.first()
        if tenant_factor:
            return tenant_factor

    # 2. System default factor (tenant is NULL)
    system_factors = EmissionFactor.objects.filter(base_query, tenant__isnull=True)
    if region:
        region_factor = system_factors.filter(region__iexact=region).first()
        if region_factor:
            return region_factor
            
    system_factor = system_factors.filter(Q(region='') | Q(region__isnull=True)).first() or system_factors.first()
    
    if not system_factor:
        raise ValueError(
            f"No matching emission factor found for category='{category}', "
            f"subcategory='{subcategory}', date='{activity_date}', region='{region}'"
        )
        
    return system_factor

def calculate_emissions(quantity, factor: EmissionFactor):
    """
    Calculates emissions: co2e_kg and co2e_tonnes.
    Formula: co2e_kg = quantity * factor_value
    co2e_tonnes = co2e_kg / 1000
    Returns (co2e_kg, co2e_tonnes) as Decimals.
    """
    if quantity is None:
        return Decimal('0.0'), Decimal('0.0')

    # Convert to Decimal for precision
    qty_dec = Decimal(str(quantity))
    factor_val_dec = factor.factor_value

    co2e_kg = qty_dec * factor_val_dec
    co2e_tonnes = co2e_kg / Decimal('1000.0')

    return co2e_kg.quantize(Decimal('0.0001')), co2e_tonnes.quantize(Decimal('0.000001'))
