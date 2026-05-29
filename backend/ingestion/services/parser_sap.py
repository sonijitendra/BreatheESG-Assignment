import csv
import io
import re
from datetime import datetime

# Mapping of technical or German names to standardized internal names
SAP_FIELD_MAP = {
    'ebeln': 'po_number',
    'einkaufsbeleg': 'po_number',
    'purchasing document': 'po_number',
    'matnr': 'material_number',
    'materialnummer': 'material_number',
    'material': 'material_number',
    'txz01': 'description',
    'kurztext': 'description',
    'short text': 'description',
    'werks': 'plant_code',
    'werk': 'plant_code',
    'plant': 'plant_code',
    'menge': 'quantity',
    'bestellmenge': 'quantity',
    'po quantity': 'quantity',
    'meins': 'unit_of_measure',
    'mengeneinheit': 'unit_of_measure',
    'order unit': 'unit_of_measure',
    'netpr': 'net_price',
    'nettopreis': 'net_price',
    'net price': 'net_price',
    'netwr': 'net_value',
    'nettowert': 'net_value',
    'net value': 'net_value',
    'waers': 'currency',
    'währung': 'currency',
    'currency': 'currency',
    'lifnr': 'vendor_code',
    'lieferant': 'vendor_code',
    'vendor': 'vendor_code',
    'name1': 'vendor_name',
    'name 1': 'vendor_name',
    'vendor name': 'vendor_name',
    'matkl': 'material_group',
    'warengruppe': 'material_group',
    'material group': 'material_group',
    'bedat': 'document_date',
    'bestelldatum': 'document_date',
    'po date': 'document_date',
    'bukrs': 'company_code',
    'buchungskreis': 'company_code',
    'company code': 'company_code',
    'loekz': 'deletion_indicator',
    'löschkennzeichen': 'deletion_indicator',
    'deletion ind.': 'deletion_indicator',
    'stblg': 'reversal_indicator',
    'stornobeleg': 'reversal_indicator',
    'reversal doc': 'reversal_indicator',
}

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    
    # Try DD.MM.YYYY (German standard)
    german_match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', date_str)
    if german_match:
        day, month, year = german_match.groups()
        return f"{year}-{month}-{day}"
        
    # Try YYYY-MM-DD (ISO)
    iso_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if iso_match:
        return date_str
        
    # Try MM/DD/YYYY
    us_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
    if us_match:
        month, day, year = us_match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Try YYYYMMDD
    internal_match = re.match(r'^(\d{4})(\d{2})(\d{2})$', date_str)
    if internal_match:
        return f"{internal_match.group(1)}-{internal_match.group(2)}-{internal_match.group(3)}"

    # If it is just a year
    if re.match(r'^\d{4}$', date_str):
        return f"{date_str}-01-01"
        
    return None

def parse_sap_csv(file_content):
    """
    Parses a CSV file containing SAP fuel & procurement data.
    Filters out deleted/reversed entries and maps technical/German fields.
    Returns (records, errors) where records is a list of standardized dicts 
    and errors is a list of dicts with keys: row, field, message.
    """
    records = []
    errors = []
    
    # Decodes content if passed as bytes
    if isinstance(file_content, bytes):
        try:
            content_str = file_content.decode('utf-8')
        except UnicodeDecodeError:
            content_str = file_content.decode('latin-1')
    else:
        content_str = file_content
        
    f = io.StringIO(content_str)
    # Detect dialect or fallback to comma
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

    # Normalize headers
    normalized_headers = []
    for h in headers:
        clean_h = h.strip().lower()
        mapped_h = SAP_FIELD_MAP.get(clean_h, clean_h)
        normalized_headers.append(mapped_h)

    for i, row in enumerate(reader, start=2):
        if not row:
            continue
            
        # Pad row if columns don't match header length
        if len(row) < len(normalized_headers):
            row = row + [''] * (len(normalized_headers) - len(row))
            
        raw_record = {normalized_headers[j]: row[j].strip() for j in range(len(normalized_headers))}
        
        # Validation checks
        row_errors = []
        
        # Check Deletion Indicator (LOEKZ in SAP is usually 'L' or 'X' if deleted)
        del_ind = raw_record.get('deletion_indicator', '')
        if del_ind and del_ind.upper() in ('L', 'X', 'Y', 'TRUE', '1'):
            # This record is deleted in SAP, we skip storing it as a valid active record or note it.
            # But the requirement says: "Filters out deleted/reversed entries".
            # We filter it by marking it invalid or skipped. Let's mark it as skipped or invalid so normalizer doesn't emit.
            row_errors.append({'row': i, 'field': 'deletion_indicator', 'message': f'Record marked as deleted in SAP (LOEKZ={del_ind})'})
            
        # Check Reversal Document
        rev_ind = raw_record.get('reversal_indicator', '')
        if rev_ind and rev_ind.strip() not in ('', '0000000000', '0'):
            row_errors.append({'row': i, 'field': 'reversal_indicator', 'message': f'Record is a reversed document in SAP (STBLG={rev_ind})'})

        # Quantity parsing
        qty_str = raw_record.get('quantity', '0')
        # Handle European decimal format (e.g. 1.000,50 -> 1000.50)
        if ',' in qty_str and '.' in qty_str:
            if qty_str.find('.') < qty_str.find(','): # dot is thousand separator, comma is decimal
                qty_str = qty_str.replace('.', '').replace(',', '.')
            else: # comma is thousand separator, dot is decimal
                qty_str = qty_str.replace(',', '')
        elif ',' in qty_str:
            # Check if comma is decimal separator (e.g., 2,5 litres or thousand separator 1,000)
            parts = qty_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2: # probably decimal
                qty_str = qty_str.replace(',', '.')
            else: # thousand separator
                qty_str = qty_str.replace(',', '')
                
        try:
            qty = float(qty_str) if qty_str else 0.0
            if qty <= 0 and not row_errors:
                row_errors.append({'row': i, 'field': 'quantity', 'message': 'Quantity must be greater than zero'})
        except ValueError:
            qty = 0.0
            row_errors.append({'row': i, 'field': 'quantity', 'message': f'Invalid numeric quantity: {qty_str}'})

        # Net Price / Value parsing
        net_val_str = raw_record.get('net_value', '')
        try:
            net_val = float(net_val_str) if net_val_str else 0.0
        except ValueError:
            net_val = 0.0
            row_errors.append({'row': i, 'field': 'net_value', 'message': f'Invalid net value: {net_val_str}'})

        # Document date parsing
        doc_date_str = raw_record.get('document_date', '')
        parsed_date = parse_date(doc_date_str)
        if not parsed_date:
            row_errors.append({'row': i, 'field': 'document_date', 'message': f'Could not parse date format: {doc_date_str}'})

        # If we have errors, store them
        if row_errors:
            errors.extend(row_errors)
            
        records.append({
            'row_number': i,
            'raw_data': {headers[j]: row[j] for j in range(min(len(headers), len(row)))},
            'mapped_data': {
                'po_number': raw_record.get('po_number', ''),
                'material_number': raw_record.get('material_number', ''),
                'description': raw_record.get('description', ''),
                'plant_code': raw_record.get('plant_code', ''),
                'quantity': qty,
                'unit_of_measure': raw_record.get('unit_of_measure', ''),
                'net_value': net_val,
                'currency': raw_record.get('currency', ''),
                'vendor_code': raw_record.get('vendor_code', ''),
                'vendor_name': raw_record.get('vendor_name', ''),
                'material_group': raw_record.get('material_group', ''),
                'document_date': parsed_date,
                'company_code': raw_record.get('company_code', ''),
            },
            'is_valid': len(row_errors) == 0,
            'errors': row_errors
        })

    return records, errors
