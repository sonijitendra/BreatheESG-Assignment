import math
from decimal import Decimal
from datetime import datetime
from ..models import EmissionRecord, EmissionFactor
from ingestion.models import RawRecord, DataSource
from .calculator import get_emission_factor, calculate_emissions

# Simple IATA airport coordinates database for realistic flight distance calculation
IATA_AIRPORTS = {
    'JFK': (40.6413, -73.7781),
    'LHR': (51.4700, -0.4543),
    'CDG': (49.0097, 2.5479),
    'BOM': (19.0896, 72.8656),
    'DEL': (28.5562, 77.1000),
    'DXB': (25.2532, 55.3657),
    'ORD': (41.9742, -87.9073),
    'LAX': (33.9416, -118.4085),
    'SFO': (37.6213, -122.3790),
    'SIN': (1.3644, 103.9915),
    'SYD': (-33.9461, 151.1772),
    'HND': (35.5494, 139.7798),
    'FRA': (50.0379, 8.5622),
    'AMS': (52.3105, 4.7683),
}

def calculate_haversine_distance(origin_code, dest_code):
    """
    Calculates great circle distance between two airport codes in km
    with a standard 8% routing efficiency uplift.
    """
    orig = IATA_AIRPORTS.get(origin_code.upper().strip())
    dest = IATA_AIRPORTS.get(dest_code.upper().strip())
    
    if not orig or not dest:
        return None
        
    lat1, lon1 = orig
    lat2, lon2 = dest
    
    R = 6371.0 # Earth's radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    # 8% uplift for routing / queuing / runway holding (standard DEFRA/GHG practice)
    distance_uplifted = distance * 1.08
    return round(distance_uplifted, 2)

def normalize_raw_record(raw_record: RawRecord, data_source: DataSource):
    """
    Normalizes a RawRecord into a validated, calculated, and flagged EmissionRecord.
    """
    tenant = raw_record.tenant
    raw_data = raw_record.raw_data
    
    # Prepare base properties
    scope = 1
    category = ''
    subcategory = ''
    description = ''
    activity_date = None
    reporting_period_start = None
    reporting_period_end = None
    quantity_value = Decimal('0.0')
    quantity_unit = ''
    original_quantity_value = None
    original_quantity_unit = ''
    region = ''
    
    flags = []
    
    # -------------------------------------------------------------------------
    # SOURCE 1: SAP INGESTION NORMALIZATION
    # -------------------------------------------------------------------------
    if data_source.source_type == DataSource.SourceType.SAP:
        # Re-extract mapped fields from parser mapping structure
        # In ingestion_service, the parser mapped data is placed inside mapped_data (which is parsed, but the raw_data holds the exact CSV row string dict)
        # For simplicity, we can fetch from parser output fields or map them again.
        # Let's map from raw_data fields using standard SAP technical names or aliases.
        
        po_num = raw_data.get('EBELN', raw_data.get('Purchasing Document', ''))
        mat_num = raw_data.get('MATNR', raw_data.get('Material', ''))
        short_text = raw_data.get('TXZ01', raw_data.get('Short Text', ''))
        plant = raw_data.get('WERKS', raw_data.get('Plant', ''))
        qty_str = raw_data.get('MENGE', raw_data.get('PO Quantity', '0'))
        uom = raw_data.get('MEINS', raw_data.get('Order Unit', ''))
        net_val_str = raw_data.get('NETWR', raw_data.get('Net Value', '0'))
        waers = raw_data.get('WAERS', raw_data.get('Currency', 'USD'))
        vendor = raw_data.get('NAME1', raw_data.get('Vendor Name', ''))
        mat_group = raw_data.get('MATKL', raw_data.get('Material Group', ''))
        doc_date_str = raw_data.get('BEDAT', raw_data.get('PO Date', ''))
        
        # Determine Date
        activity_date = raw_record.ingestion_job.raw_records.filter(id=raw_record.id).values_list('created_at', flat=True).first().date()
        # Parse doc date if valid
        from .parser_sap import parse_date
        parsed_doc_date = parse_date(doc_date_str)
        if parsed_doc_date:
            activity_date = datetime.strptime(parsed_doc_date, '%Y-%m-%d').date()
            
        # Parse Quantity
        try:
            qty_raw = Decimal(str(qty_str).replace(',', '').strip())
        except Exception:
            qty_raw = Decimal('0.0')
            
        original_quantity_value = qty_raw
        original_quantity_unit = uom.strip().lower()
        
        # Categorize based on Material Group (MATKL) and Description (TXZ01)
        mat_group_clean = mat_group.strip().upper()
        short_text_clean = short_text.strip().lower()
        
        scope = 1
        category = 'fuel'
        
        if 'NAT' in mat_group_clean or 'GAS' in mat_group_clean or 'NATURAL' in short_text_clean:
            subcategory = 'natural_gas'
            quantity_unit = 'm3'
            # Natural gas conversion if units differ
            if original_quantity_unit in ('therm', 'therms'):
                # 1 therm = 2.83 m3 roughly
                quantity_value = qty_raw * Decimal('2.83')
                flags.append("Converted original unit 'therms' to standard 'm3' (1 therm = 2.83 m3)")
            else:
                quantity_value = qty_raw
        elif 'PETROL' in mat_group_clean or 'GASOLINE' in mat_group_clean or 'PETROL' in short_text_clean or 'UNLEADED' in short_text_clean:
            subcategory = 'petrol'
            quantity_unit = 'litre'
            if original_quantity_unit in ('gal', 'gallons', 'gallon'):
                quantity_value = qty_raw * Decimal('3.78541')
                flags.append("Converted unit from gallons to litres (1 gal = 3.78541 litres)")
            else:
                quantity_value = qty_raw
        else:
            # Default to diesel
            subcategory = 'diesel'
            quantity_unit = 'litre'
            if original_quantity_unit in ('gal', 'gallons', 'gallon'):
                quantity_value = qty_raw * Decimal('3.78541')
                flags.append("Converted unit from gallons to litres (1 gal = 3.78541 litres)")
            elif original_quantity_unit in ('kg', 'kgs'):
                # Diesel density roughly 0.832 kg/litre
                quantity_value = qty_raw / Decimal('0.832')
                flags.append("Converted unit from kg to litres using diesel density (0.832 kg/litre)")
            else:
                quantity_value = qty_raw

        description = f"SAP Fuel Purchase PO {po_num}: Material {mat_num} ({short_text}) from {vendor}"
        
        # Plant regional overrides (e.g. WERKS code check)
        region = 'UK' if 'UK' in plant.upper() else ('US' if 'US' in plant.upper() else 'UK')
        
        # SAP specific flags
        if quantity_value > 100000:
            flags.append("Anomaly: Exceptionally large fuel quantity (>100,000 litres)")
            
        try:
            net_val = Decimal(str(net_val_str).replace(',', '').strip())
            if net_val == 0 and quantity_value > 0:
                flags.append("Anomaly: Net purchase value is zero but quantity is non-zero")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # SOURCE 2: UTILITY ELECTRICITY NORMALIZATION
    # -------------------------------------------------------------------------
    elif data_source.source_type == DataSource.SourceType.UTILITY:
        acct_num = raw_data.get('Account Number', raw_data.get('Account #', ''))
        meter_num = raw_data.get('Meter Number', raw_data.get('Meter ID', ''))
        usage_str = raw_data.get('Usage kWh', raw_data.get('Usage', '0'))
        cost_str = raw_data.get('Total Cost', raw_data.get('Total Amount', '0'))
        start_str = raw_data.get('Billing Start', raw_data.get('Start Date', ''))
        end_str = raw_data.get('Billing End', raw_data.get('End Date', ''))
        read_type = raw_data.get('Read Type', 'actual').lower()
        provider = raw_data.get('Provider', '')
        addr = raw_data.get('Service Address', '')

        # Standard date parses
        from .parser_utility import parse_date
        p_start = parse_date(start_str)
        p_end = parse_date(end_str)
        
        if p_start and p_end:
            reporting_period_start = datetime.strptime(p_start, '%Y-%m-%d').date()
            reporting_period_end = datetime.strptime(p_end, '%Y-%m-%d').date()
            # Midpoint as activity date
            days = (reporting_period_end - reporting_period_start).days
            activity_date = reporting_period_start + (reporting_period_end - reporting_period_start) / 2
        else:
            activity_date = raw_record.ingestion_job.raw_records.filter(id=raw_record.id).values_list('created_at', flat=True).first().date()

        try:
            usage = Decimal(str(usage_str).replace(',', '').strip())
        except Exception:
            usage = Decimal('0.0')

        original_quantity_value = usage
        original_quantity_unit = 'kwh'
        
        scope = 2
        category = 'electricity'
        subcategory = 'grid_average'
        quantity_value = usage
        quantity_unit = 'kWh'
        
        # Region selection based on provider / address
        addr_up = addr.upper()
        if 'UK' in addr_up or 'LONDON' in addr_up:
            region = 'UK'
        elif 'IN' in addr_up or 'INDIA' in addr_up or 'MUMBAI' in addr_up or 'DELHI' in addr_up:
            region = 'India'
        elif 'US' in addr_up or 'CA' in addr_up or 'NY' in addr_up or 'TX' in addr_up:
            region = 'US'
        else:
            region = 'US' # Default to US

        description = f"Electricity consumption for Account {acct_num}, Meter {meter_num} ({provider})"
        
        # Quality flags
        if read_type == 'estimated':
            flags.append("Quality Warning: Estimated utility reading rather than actual metered reading")
            
        if p_start and p_end:
            days = (reporting_period_end - reporting_period_start).days
            if days > 45:
                flags.append(f"Anomaly: Billing period of {days} days is unusually long (>45 days)")
            elif days < 15:
                flags.append(f"Anomaly: Billing period of {days} days is unusually short (<15 days)")
                
        try:
            cost = Decimal(str(cost_str).replace('$', '').replace(',', '').strip())
            if usage > 0:
                cost_rate = cost / usage
                if cost_rate > Decimal('0.50'):
                    flags.append(f"Anomaly: High electricity rate of ${cost_rate:.3f}/kWh detected")
                elif cost_rate < Decimal('0.02') and cost > 0:
                    flags.append(f"Anomaly: Implausibly low electricity rate of ${cost_rate:.3f}/kWh")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # SOURCE 3: CORPORATE TRAVEL NORMALIZATION
    # -------------------------------------------------------------------------
    elif data_source.source_type == DataSource.SourceType.TRAVEL:
        emp_name = raw_data.get('Employee Name', '')
        exp_type = raw_data.get('Expense Type', '').lower()
        amount_str = raw_data.get('Amount', '0')
        orig = raw_data.get('Origin', '')
        dest = raw_data.get('Destination', '')
        cabin = raw_data.get('Cabin Class', '').lower()
        dist_str = raw_data.get('Distance', '')
        dept = raw_data.get('Department', '')
        vendor = raw_data.get('Vendor Name', '')

        # Standard date parses
        from .parser_travel import parse_date
        p_exp_date = parse_date(raw_data.get('Expense Date', ''))
        if p_exp_date:
            activity_date = datetime.strptime(p_exp_date, '%Y-%m-%d').date()
        else:
            activity_date = raw_record.ingestion_job.raw_records.filter(id=raw_record.id).values_list('created_at', flat=True).first().date()

        try:
            amount = Decimal(str(amount_str).replace(',', '').strip())
        except Exception:
            amount = Decimal('0.0')

        scope = 3
        
        # Flight logic
        if 'flight' in exp_type or 'air' in exp_type or 'aviation' in exp_type:
            category = 'travel_flight'
            quantity_unit = 'passenger-km'
            
            # Determine distance in km
            flight_dist = None
            if dist_str:
                try:
                    # Let's assume input could be in miles or km
                    flight_dist = float(dist_str)
                    original_quantity_unit = 'miles' if 'mile' in exp_type else 'km'
                    if original_quantity_unit == 'miles':
                        flight_dist = flight_dist * 1.60934
                        flags.append("Converted flight distance from miles to km")
                except Exception:
                    pass
            
            # Calculate distance if missing but IATA codes exist
            if not flight_dist and orig and dest:
                flight_dist = calculate_haversine_distance(orig, dest)
                if flight_dist:
                    flags.append(f"Calculated flight distance from IATA codes {orig} -> {dest} with 8% efficiency uplift ({flight_dist} km)")
                    original_quantity_unit = 'iata_lookup_km'
                else:
                    # Fallback standard distance based on short vs long haul keyword
                    flight_dist = 4000.0 if 'long' in exp_type else 800.0
                    flags.append(f"Missing airport code coordinates. Used fallback flight distance of {flight_dist} km")
                    original_quantity_unit = 'fallback_km'
            elif not flight_dist:
                # Absolute fallback
                flight_dist = 1000.0
                flags.append(f"No distance or airport codes provided. Used default short-haul flight distance of {flight_dist} km")
                original_quantity_unit = 'default_fallback_km'

            original_quantity_value = Decimal(str(flight_dist))
            quantity_value = original_quantity_value

            # Short-haul vs Long-haul classification (DEFRA standard: short < 3700 km, long >= 3700 km)
            is_long_haul = flight_dist >= 3700.0
            
            # Cabin class mapping
            is_business = 'business' in cabin or 'first' in cabin
            
            if is_long_haul:
                subcategory = 'long_haul_business' if is_business else 'long_haul_economy'
            else:
                subcategory = 'short_haul_business' if is_business else 'short_haul_economy'

            if not cabin:
                flags.append("Missing cabin class. Defaulted calculation to economy class (conservative estimate)")

            description = f"Business flight for {emp_name}: {orig} -> {dest} ({subcategory.replace('_', ' ').title()})"
            region = 'UK'

        # Hotel lodging logic
        elif 'hotel' in exp_type or 'lodging' in exp_type or 'stay' in exp_type:
            category = 'travel_hotel'
            subcategory = 'hotel_per_room_night'
            quantity_unit = 'room-night'
            original_quantity_unit = 'spend_usd'
            
            # Room night estimation based on typical rate $150 per night
            original_quantity_value = amount
            nights = math.ceil(float(amount) / 150.0) if amount > 0 else 1
            quantity_value = Decimal(str(nights))
            
            flags.append(f"Spend-based estimation: Estimated {nights} room-night(s) from spend of ${amount} (fallback rate: $150/night)")
            
            description = f"Hotel lodging for {emp_name} at {vendor} (Estimated {nights} room nights)"
            region = 'UK'

        # Taxi, rental car, ground transport
        else:
            category = 'travel_ground'
            quantity_unit = 'km'
            original_quantity_unit = 'spend_usd'
            original_quantity_value = amount
            
            # Spend-based distance calculation
            if 'taxi' in exp_type or 'uber' in exp_type or 'lyft' in exp_type:
                subcategory = 'taxi'
                # Estimate 1 km per $1.50 spent
                est_km = float(amount) / 1.50 if amount > 0 else 5.0
                quantity_value = Decimal(f"{est_km:.2f}")
                flags.append(f"Spend-based estimation: Estimated {quantity_value} km from taxi spend of ${amount} (fallback rate: $1.50/km)")
            else:
                subcategory = 'rental_car_average'
                # Estimate 1 km per $0.50 spent
                est_km = float(amount) / 0.50 if amount > 0 else 50.0
                quantity_value = Decimal(f"{est_km:.2f}")
                flags.append(f"Spend-based estimation: Estimated {quantity_value} km from rental car spend of ${amount} (fallback rate: $0.50/km)")
                
            description = f"Ground transport ({subcategory.replace('_', ' ')}) for {emp_name} via {vendor}"
            region = 'UK'

    # -------------------------------------------------------------------------
    # LOOKUP EMISSION FACTOR & PERFORM CALCULATIONS
    # -------------------------------------------------------------------------
    factor = get_emission_factor(tenant, category, subcategory, activity_date, region)
    co2e_kg, co2e_tonnes = calculate_emissions(quantity_value, factor)
    
    # Create the record in DB
    emission_rec = EmissionRecord.objects.create(
        tenant=tenant,
        raw_record=raw_record,
        data_source=data_source,
        scope=scope,
        category=category,
        description=description,
        activity_date=activity_date,
        reporting_period_start=reporting_period_start,
        reporting_period_end=reporting_period_end,
        quantity_value=quantity_value,
        quantity_unit=quantity_unit,
        original_quantity_value=original_quantity_value,
        original_quantity_unit=original_quantity_unit,
        emission_factor=factor,
        emission_factor_value=factor.factor_value,
        co2e_kg=co2e_kg,
        co2e_tonnes=co2e_tonnes,
        status=EmissionRecord.Status.FLAGGED if flags else EmissionRecord.Status.PENDING,
        flags=flags,
    )
    
    return emission_rec
