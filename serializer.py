from competency import Competency

import json

class Serializer:
    def __init__(self, path):
        self.path = path

    def serialize(self, mappings):
        serializable = []
        for source, target in mappings:
            if isinstance(target, Competency):
                target_data = {"__type__": "Competency", **target.to_dict()}
            else:
                target_data = {"__type__": "str", "value": target}
            serializable.append({"source": source, "target": target_data})
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)

    def deserialize(self):
        mappings = []
        with open(self.path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            for pair in loaded:
                source = pair["source"]
                target_data = pair["target"]
                if target_data["__type__"] == "Competency":
                    target = Competency.from_dict(target_data)
                else:
                    target = target_data["value"]
                mappings.append((source, target))
        return mappings