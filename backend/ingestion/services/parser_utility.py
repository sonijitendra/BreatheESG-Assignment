import csv
import io
import re

UTILITY_FIELD_MAP = {
    'account_number': 'account_number',
    'account #': 'account_number',
    'acct no.': 'account_number',
    'account id': 'account_number',
    
    'meter_number': 'meter_number',
    'meter #': 'meter_number',
    'meter id': 'meter_number',
    'meter no.': 'meter_number',
    
    'service_address': 'service_address',
    'location': 'service_address',
    'premise address': 'service_address',
    'service addr': 'service_address',
    
    'billing_period_start': 'billing_start',
    'start date': 'billing_start',
    'from': 'billing_start',
    'period start': 'billing_start',
    'bill start': 'billing_start',
    
    'billing_period_end': 'billing_end',
    'end date': 'billing_end',
    'to': 'billing_end',
    'period end': 'billing_end',
    'bill end': 'billing_end',
    
    'usage_kwh': 'usage_kwh',
    'usage': 'usage_kwh',
    'kwh used': 'usage_kwh',
    'consumption': 'usage_kwh',
    'total kwh': 'usage_kwh',
    'kwh_used': 'usage_kwh',
    
    'demand_kw': 'demand_kw',
    'demand': 'demand_kw',
    'peak kw': 'demand_kw',
    'max demand': 'demand_kw',
    'demand kw': 'demand_kw',
    
    'total_cost': 'total_cost',
    'total amount': 'total_cost',
    'amount due': 'total_cost',
    'bill amount': 'total_cost',
    
    'read_type': 'read_type',
    'read type': 'read_type',
    'meter read type': 'read_type',
    
    'provider': 'provider',
    'provider name': 'provider',
    'utility': 'provider',
}

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    
    # Try YYYY-MM-DD (ISO)
    iso_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if iso_match:
        return date_str
        
    # Try MM/DD/YYYY
    us_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
    if us_match:
        month, day, year = us_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Try DD.MM.YYYY
    german_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', date_str)
    if german_match:
        day, month, year = german_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    return None

def parse_utility_csv(file_content):
    """
    Parses a CSV file containing electricity utility bill data.
    """
    records = []
    errors = []
    
    if isinstance(file_content, bytes):
        try:
            content_str = file_content.decode('utf-8')
        except UnicodeDecodeError:
            content_str = file_content.decode('latin-1')
    else:
        content_str = file_content
        
    f = io.StringIO(content_str)
    try:
        sample = content_str[:2048]
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.reader(f, dialect)
    except Exception:
        f.seek(0)
        reader = csv.reader(f)

    try:
        headers = next(reader)
    except StopIteration:
        return [], [{'row': 0, 'field': 'file', 'message': 'Empty file'}]

    normalized_headers = []
    for h in headers:
        clean_h = h.strip().lower()
        mapped_h = UTILITY_FIELD_MAP.get(clean_h, clean_h)
        normalized_headers.append(mapped_h)

    for i, row in enumerate(reader, start=2):
        if not row:
            continue
            
        if len(row) < len(normalized_headers):
            row = row + [''] * (len(normalized_headers) - len(row))
            
        raw_record = {normalized_headers[j]: row[j].strip() for j in range(len(normalized_headers))}
        
        row_errors = []
        
        # Account and meter numbers
        acct = raw_record.get('account_number', '')
        meter = raw_record.get('meter_number', '')
        if not acct:
            row_errors.append({'row': i, 'field': 'account_number', 'message': 'Account number is required'})
            
        # Parse usage (kWh)
        usage_str = raw_record.get('usage_kwh', '')
        try:
            usage = float(usage_str) if usage_str else 0.0
            # A utility adjustment can be negative, so we allow negative usage for credits, but warn
        except ValueError:
            usage = 0.0
            row_errors.append({'row': i, 'field': 'usage_kwh', 'message': f'Invalid numeric usage: {usage_str}'})

        # Parse demand (kW)
        demand_str = raw_record.get('demand_kw', '')
        try:
            demand = float(demand_str) if (demand_str and demand_str != '-') else None
        except ValueError:
            demand = None
            
        # Parse total cost
        cost_str = raw_record.get('total_cost', '0')
        cost_str = cost_str.replace('$', '').replace(',', '').strip()
        try:
            cost = float(cost_str) if cost_str else 0.0
        except ValueError:
            cost = 0.0
            row_errors.append({'row': i, 'field': 'total_cost', 'message': f'Invalid cost: {cost_str}'})

        # Parse dates
        start_str = raw_record.get('billing_start', '')
        end_str = raw_record.get('billing_end', '')
        
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)
        
        if not start_date:
            row_errors.append({'row': i, 'field': 'billing_start', 'message': f'Invalid start date: {start_str}'})
        if not end_date:
            row_errors.append({'row': i, 'field': 'billing_end', 'message': f'Invalid end date: {end_str}'})
            
        if start_date and end_date:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d')
            dt_end = datetime.strptime(end_date, '%Y-%m-%d')
            if dt_start >= dt_end:
                row_errors.append({'row': i, 'field': 'billing_end', 'message': f'End date ({end_date}) must be after start date ({start_date})'})

        if row_errors:
            errors.extend(row_errors)
            
        records.append({
            'row_number': i,
            'raw_data': {headers[j]: row[j] for j in range(min(len(headers), len(row)))},
            'mapped_data': {
                'account_number': acct,
                'meter_number': meter,
                'service_address': raw_record.get('service_address', ''),
                'billing_start': start_date,
                'billing_end': end_date,
                'usage_kwh': usage,
                'demand_kw': demand,
                'total_cost': cost,
                'read_type': raw_record.get('read_type', 'actual').lower(),
                'provider': raw_record.get('provider', ''),
            },
            'is_valid': len(row_errors) == 0,
            'errors': row_errors
        })

    return records, errors
from datetime import datetime
