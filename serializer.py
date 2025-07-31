from competency import Competency

import json

class Serializer:
    @staticmethod
    def serialize(mappings, path):
        serializable = []
        for source, target in mappings:
            if isinstance(target, Competency):
                target_data = {"__type__": "Competency", **target.to_dict()}
            else:
                target_data = {"__type__": "str", "value": target}
            serializable.append({"source": source, "target": target_data})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

    @staticmethod
    def deserialize(path):
        mappings = []
        with open(path, "r", encoding="utf-8") as f:
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
