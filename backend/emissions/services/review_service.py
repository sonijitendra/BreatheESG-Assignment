from django.db import transaction
from django.utils import timezone
from ..models import EmissionRecord, ReviewAction
from core.models import AuditLog

VALID_TRANSITIONS = {
    # from_status -> set of valid to_status
    EmissionRecord.Status.PENDING: {EmissionRecord.Status.REVIEWED, EmissionRecord.Status.FLAGGED},
    EmissionRecord.Status.FLAGGED: {EmissionRecord.Status.REVIEWED},
    EmissionRecord.Status.REVIEWED: {EmissionRecord.Status.APPROVED, EmissionRecord.Status.REJECTED},
    EmissionRecord.Status.REJECTED: {EmissionRecord.Status.PENDING},
    EmissionRecord.Status.APPROVED: {EmissionRecord.Status.LOCKED},
    # LOCKED is a terminal state, no outgoing transitions
}

def review_record(record: EmissionRecord, action: str, performed_by: str, reason: str = '', changes: dict = None, ip_address: str = None, user_agent: str = None):
    """
    Validates and executes a review workflow state transition on an EmissionRecord.
    Creates a ReviewAction record and an immutable AuditLog entry in a single atomic transaction.
    """
    if not changes:
        changes = {}

    from_status = record.status
    to_status = None

    # Map the action string to the target status
    action_clean = action.strip().lower()
    if action_clean == 'review':
        to_status = EmissionRecord.Status.REVIEWED
    elif action_clean == 'flag':
        to_status = EmissionRecord.Status.FLAGGED
    elif action_clean == 'approve':
        to_status = EmissionRecord.Status.APPROVED
    elif action_clean == 'reject':
        to_status = EmissionRecord.Status.REJECTED
    elif action_clean == 'lock':
        to_status = EmissionRecord.Status.LOCKED
    elif action_clean == 'edit':
        # Analyst edit is allowed in pending or flagged states
        if from_status in (EmissionRecord.Status.PENDING, EmissionRecord.Status.FLAGGED):
            to_status = from_status # Status remains the same, just edits applied
        else:
            raise ValueError(f"Editing is not permitted in status: {from_status}")
    else:
        raise ValueError(f"Unknown review action: {action}")

    # Check state machine validation if status is changing
    if from_status != to_status:
        allowed_targets = VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed_targets:
            raise ValueError(
                f"Invalid workflow transition: cannot move record from '{from_status}' to '{to_status}' "
                f"using action '{action}'."
            )

    with transaction.atomic():
        # Apply field edits if any (e.g. quantity adjust or notes)
        original_values = {}
        updated_values = {}
        
        if changes:
            for field, val in changes.items():
                if hasattr(record, field) and field not in ('id', 'tenant', 'raw_record', 'data_source', 'created_at'):
                    orig_val = getattr(record, field)
                    original_values[field] = str(orig_val)
                    
                    # Convert to Decimal/float where appropriate
                    if field in ('quantity_value', 'co2e_kg', 'co2e_tonnes', 'emission_factor_value'):
                        import decimal
                        setattr(record, field, decimal.Decimal(str(val)))
                    else:
                        setattr(record, field, val)
                        
                    updated_values[field] = str(val)

        # Update status and timestamps
        record.status = to_status
        
        if to_status == EmissionRecord.Status.REVIEWED:
            record.reviewed_by = performed_by
            record.reviewed_at = timezone.now()
        elif to_status == EmissionRecord.Status.APPROVED:
            record.approved_by = performed_by
            record.approved_at = timezone.now()
        elif to_status == EmissionRecord.Status.LOCKED:
            record.locked_at = timezone.now()
            
        if reason:
            # Append reason to analyst notes
            current_notes = record.analyst_notes or ''
            sep = '\n' if current_notes else ''
            record.analyst_notes = f"{current_notes}{sep}[{performed_by} at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}]: {reason}"

        record.save()

        # Create ReviewAction domain record
        ReviewAction.objects.create(
            tenant=record.tenant,
            emission_record=record,
            action=action_clean,
            from_status=from_status,
            to_status=to_status,
            performed_by=performed_by,
            reason=reason,
            changes={
                'edits': {'from': original_values, 'to': updated_values} if changes else {},
                'status_change': {'from': from_status, 'to': to_status}
            }
        )

        # Create immutable system AuditLog entry
        AuditLog.objects.create(
            tenant=record.tenant,
            entity_type='EmissionRecord',
            entity_id=str(record.id),
            action=AuditLog.Action.UPDATE,
            changes={
                'status': {'from': from_status, 'to': to_status},
                'edits': {'from': original_values, 'to': updated_values} if changes else {}
            },
            performed_by=performed_by,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )

    return record

def bulk_review(record_ids: list, action: str, performed_by: str, reason: str = '', ip_address: str = None, user_agent: str = None):
    """
    Applies a review action to multiple records in a single transaction.
    Returns (success_count, error_count, errors_list).
    """
    success_count = 0
    error_count = 0
    errors_list = []

    for r_id in record_ids:
        try:
            record = EmissionRecord.objects.get(id=r_id)
            review_record(
                record=record,
                action=action,
                performed_by=performed_by,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            success_count += 1
        except Exception as ex:
            error_count += 1
            errors_list.append({'record_id': str(r_id), 'message': str(ex)})

    return success_count, error_count, errors_list
