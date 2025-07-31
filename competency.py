from datetime import date, datetime

class Competency:
    def __init__(self, name, path, comp_id):
        self.name = name
        self.path = path
        self.id = comp_id

    def __str__(self):
        return self.name  # Controls what shows in the UI

    def __repr__(self):
        return f"Competency(name={self.name!r}, path={self.path}, id={self.id})"

    def to_dict(self):
        """Convert to a JSON-serializable dict."""
        return {"name": self.name, "path": self.path, "id": self.id}

    @classmethod
    def from_dict(cls, data):
        """Recreate a Competency from a dict (e.g., from JSON)."""
        return cls(data["name"], data["path"], data["id"])
