import requests
from tkinter import messagebox
from competency import Competency


class ApiClient:
    def __init__(self, config):
        self.config = config
        self.base_url = self.config["server"].rstrip("/")
        self.headers = {"X-API-KEY": self.config["api_key"]}

    def load_account_leaves(self):
        url = f"{self.base_url}/api/accounts.json"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            first = data[0] if isinstance(data, list) and data else {}
            acct_data = first.get("data", {})
            if not isinstance(acct_data, dict):
                raise ValueError("'data' field not found in first element")
            return sorted(acct_data.keys())
        except Exception as e:
            messagebox.showerror("API error", f"Could not load accounts:\n{e}")
            return ["(error loading accounts)"]

    def load_competencies_subtree(self):
        url = f"{self.base_url}/api/competencies.json"
        tree = {}

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            curricula = resp.json()

            for cur in curricula:
                cat_branch = {}
                if cur.get("is_dto"):
                    continue
                for cat in cur.get("categories", []):
                    comps = [
                        Competency(
                            comp["name"], 
                            " / ".join(["Competencies", cur.get("name"), cat.get("name"), comp["name"]]) , 
                            comp.get("id", None)
                            )
                        for comp in cat.get("competencies", [])
                        if not comp.get("is_dto")
                    ]
                    if comps:
                        cat_branch[cat["name"]] = comps

                if cat_branch:
                    name = cur.get("name")
                    tree[name] = cat_branch

            return tree if tree else {"(no eligible data)": []}

        except Exception as e:
            messagebox.showerror("API error", f"Could not load competencies:\n{e}")
            return {"(error loading competencies)": []}


    def fetch_accounts_map(self):
        url = f"{self.base_url}/api/accounts.json"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            accounts = response.json()
            return {int(acc['lid_nummer']): acc['id'] for acc in accounts}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch accounts: {e}")
            return {}

    def put_account_data(self, pilot_id, data_fields):
        url = f"{self.base_url}/api/accounts.json"
        body = {
            "id": pilot_id,
            "data": data_fields
        }
        try:
            response = requests.put(url, json=body, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update accounts: {e}")
            return 
        {}
    
    def assign_competency(self, pilot_id, competency_id, date_assigned, date_valid_to):
        url = f"{self.base_url}/api/competencies/assign.json"
        body = {
            "user_id": pilot_id,
            "id": competency_id,
            **{k: v for k, v in { # we add date_assigned and date_valid_to only if they are "truthy"
                "date_assigned": date_assigned,
                "date_valid_to": date_valid_to
            }.items() if v}
        }
        try:
            response = requests.post(url, json=body, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to assign competency: {e}")
            return 
        {}
    
    def revoke_competency(self, pilot_id, competency_id):
        url = f"{self.base_url}/api/competencies/revoke.json"
        body = {
            "user_id": pilot_id,
            "id": competency_id
        }
        try:
            response = requests.post(url, json=body, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to revoke competency: {e}")
            return 
        {}