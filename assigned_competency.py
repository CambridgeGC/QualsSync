class AssignedCompetency:
    def __init__(self, comp_id, date_assigned, date_valid_to, pilot_id):
        self.id = comp_id
        self.date_assigned = date_assigned
        self.date_valid_to = date_valid_to
        self.pilot_id = pilot_id

    def __str__(self):
        return f"AssignedCompetency(id={self.id})"  # For debugging, UI formatting should be separate

    def __repr__(self):
        return f"AssignedCompetency(id={self.id!r}, date_assigned={self.date_assigned}, date_valid_to={self.date_valid_to}, pilot_id={self.pilot_id})"
    
    def has_changed_compared_to_current(self, new_date_assigned, new_date_valid_to):
        return (
            (new_date_assigned and self.date_assigned != new_date_assigned) or
            (new_date_valid_to and self.date_valid_to != new_date_valid_to)
        )
