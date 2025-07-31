from datetime import datetime, date

def apply_medical_check_rule(updates, account_data, name, log_callback):
    """
    Applies the business rule that 'medical_checked_at' and 'medical_checked_by'
    fields should only be updated if the pilot's medical qualification is current.
    This modifies the 'updates' dictionary in place.
    """
    is_checking_medical = 'medical_checked_at' in updates or 'medical_checked_by' in updates
    if not is_checking_medical:
        return

    def is_medical_current(valid_from_str, valid_to_str):
        today = date.today()
        try:
            vf = datetime.strptime(valid_from_str, "%Y-%m-%d").date() if valid_from_str else None
            vt = datetime.strptime(valid_to_str, "%Y-%m-%d").date() if valid_to_str else None
        except (ValueError, TypeError):
            return False  # Handles malformed or non-string date values

        if vf is None and vt is None:
            return False  # Not current if no dates are provided
        if vf and vf > today:
            return False  # Not yet valid
        if vt and vt < today:
            return False  # Expired
        return True

    # Use the new validity dates if they're part of this update, otherwise use existing data.
    effective_valid_from = updates.get('medical_valid_from', account_data.get('medical_valid_from'))
    effective_valid_to = updates.get('medical_valid_to', account_data.get('medical_valid_to'))

    if not is_medical_current(effective_valid_from, effective_valid_to):
        skipped_fields = []
        if 'medical_checked_at' in updates:
            updates.pop('medical_checked_at')
            skipped_fields.append("'medical_checked_at'")
        if 'medical_checked_by' in updates:
            updates.pop('medical_checked_by')
            skipped_fields.append("'medical_checked_by'")
        
        if skipped_fields:
            log_callback(f"Skipping update of {', '.join(skipped_fields)} for {name}: medical is not current.", "warning")

def should_assign_competency_based_on_dates(value_from: str | None, value_to: str | None) -> bool:
    """
    Business rule to determine if a competency should be assigned based on its
    validity dates compared to the current date.
    """
    today = date.today()

    def parse(d):
        return datetime.strptime(d, "%Y-%m-%d").date() if d else None

    try:
        vf = parse(value_from)
        vt = parse(value_to)
    except (ValueError, TypeError):
        return False # Handles malformed or non-string date values

    if vf is None and vt is None:
        return True

    if vf and vf > today:
        return False  # starts in the future

    if vt and vt < today:
        return False  # already expired

    return True
