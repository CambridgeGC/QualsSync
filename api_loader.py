import requests
from tkinter import messagebox

def load_account_leaves(config):
    url = f"{config['server'].rstrip('/')}/api/accounts.json"
    headers = {"X-API-KEY": config["api_key"]}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
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


def load_competencies_subtree(config):
    url = f"{config['server'].rstrip('/')}/api/competencies.json"
    headers = {"X-API-KEY": config["api_key"]}
    tree = {}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        curricula = resp.json()

        for cur in curricula:
            cat_branch = {}
            if cur.get("is_dto"):
                continue
            for cat in cur.get("categories", []):
                comps = [
                    comp["name"]
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


def fetch_accounts_map(config):
    url = f"{config['server'].rstrip('/')}/api/accounts.json"
    headers = {"X-API-KEY": config["api_key"]}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        accounts = response.json()
        return {int(acc['lid_nummer']): acc['id'] for acc in accounts}
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch accounts: {e}")
        return {}
