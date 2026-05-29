import csv
import io
import re

TRAVEL_FIELD_MAP = {
    'employee_id': 'employee_id',
    'employee id': 'employee_id',
    'emp_id': 'employee_id',
    'employee_name': 'employee_name',
    'employee name': 'employee_name',
    'department': 'department',
    'dept': 'department',
    'cost_center': 'cost_center',
    'cost center': 'cost_center',
    
    'expense_date': 'expense_date',
    'transaction date': 'expense_date',
    'travel date': 'expense_date',
    'date': 'expense_date',
    
    'expense_type': 'expense_type',
    'category': 'expense_type',
    'expense type': 'expense_type',
    
    'vendor': 'vendor_name',
    'vendor name': 'vendor_name',
    'merchant name': 'vendor_name',
    'merchant': 'vendor_name',
    
    'description': 'description',
    'memo': 'description',
    
    'amount': 'amount',
    'total': 'amount',
    
    'currency': 'currency',
    'curr': 'currency',
    
    'origin': 'origin',
    'from': 'origin',
    'departure': 'origin',
    
    'destination': 'destination',
    'to': 'destination',
    'arrival': 'destination',
    
    'cabin_class': 'cabin_class',
    'class': 'cabin_class',
    'cabin class': 'cabin_class',
    'travel class': 'cabin_class',
    
    'trip_id': 'trip_id',
    'trip id': 'trip_id',
    'report id': 'trip_id',
    
    'distance': 'distance',
    'distance_km': 'distance',
    'miles': 'distance',
    
    'approval_status': 'approval_status',
    'status': 'approval_status',
    'approval status': 'approval_status',
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

def parse_travel_csv(file_content):
    """
    Parses a CSV file containing corporate travel data.
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
        mapped_h = TRAVEL_FIELD_MAP.get(clean_h, clean_h)
        normalized_headers.append(mapped_h)

    for i, row in enumerate(reader, start=2):
        if not row:
            continue
            
        if len(row) < len(normalized_headers):
            row = row + [''] * (len(normalized_headers) - len(row))
            
        raw_record = {normalized_headers[j]: row[j].strip() for j in range(len(normalized_headers))}
        
        row_errors = []
        
        # Expense date and type are mandatory
        expense_date_str = raw_record.get('expense_date', '')
        parsed_date = parse_date(expense_date_str)
        if not parsed_date:
            row_errors.append({'row': i, 'field': 'expense_date', 'message': f'Invalid or missing expense date: {expense_date_str}'})
            
        expense_type = raw_record.get('expense_type', '')
        if not expense_type:
            row_errors.append({'row': i, 'field': 'expense_type', 'message': 'Expense type/category is required'})
            
        # Amount parsing
        amount_str = raw_record.get('amount', '0')
        amount_str = amount_str.replace(',', '').replace('$', '').strip()
        try:
            amount = float(amount_str) if amount_str else 0.0
            if amount <= 0 and not row_errors:
                # Travel credit can be negative, so we don't block, but log it
                pass
        except ValueError:
            amount = 0.0
            row_errors.append({'row': i, 'field': 'amount', 'message': f'Invalid numeric amount: {amount_str}'})

        # Distance parsing (if present)
        dist_str = raw_record.get('distance', '')
        try:
            distance = float(dist_str) if dist_str else None
        except ValueError:
            distance = None
            row_errors.append({'row': i, 'field': 'distance', 'message': f'Invalid numeric distance: {dist_str}'})

        if row_errors:
            errors.extend(row_errors)
            
        records.append({
            'row_number': i,
            'raw_data': {headers[j]: row[j] for j in range(min(len(headers), len(row)))},
            'mapped_data': {
                'employee_id': raw_record.get('employee_id', ''),
                'employee_name': raw_record.get('employee_name', ''),
                'department': raw_record.get('department', ''),
                'cost_center': raw_record.get('cost_center', ''),
                'expense_date': parsed_date,
                'expense_type': expense_type,
                'vendor_name': raw_record.get('vendor_name', ''),
                'description': raw_record.get('description', ''),
                'amount': amount,
                'currency': raw_record.get('currency', 'USD'),
                'origin': raw_record.get('origin', ''),
                'destination': raw_record.get('destination', ''),
                'cabin_class': raw_record.get('cabin_class', ''),
                'trip_id': raw_record.get('trip_id', ''),
                'distance': distance,
                'approval_status': raw_record.get('approval_status', ''),
            },
            'is_valid': len(row_errors) == 0,
            'errors': row_errors
        })

    return records, errors
