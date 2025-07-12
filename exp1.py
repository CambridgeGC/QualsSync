""
"""
visual_mapper_resizable.py
Excel‑driven list  ⇆  API‑driven tree  +  mapping persistence
Now fully resizable with PanedWindow + grid weights
"""

import json
import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None  # We'll warn the user if they try to load Excel

# ---------- CONFIG ---------------------------------------------------------

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- GUI ------------------------------------------------------------

class MapperGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel ↔ API‑Tree Mapper")
        self.minsize(900, 600)
        self.config = load_config()

        # Data holders
        self.source_items: list[str] = []
        self.mappings: list[tuple[str, str]] = []

        # New: pilots list 
        self.pilots: list[tuple[str, str, str]]  # (name, membership_number, id)

        self.target_tree_dict = self._load_target_tree()

        self._build_widgets()
        self._populate_tree(self.target_tree_dict, "")

    # ---------- widget layout ---------------------------------------------

    def _build_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)     # paned window grows
        self.rowconfigure(1, weight=0)     # bottom stays natural height

        # --- Paned window (Source | Target) --------------------------------
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew", pady=(8, 4), padx=8)

        # -- Source pane -----------------------------------------------------
        src_frame = ttk.Frame(paned, padding=6)
        src_frame.columnconfigure(0, weight=1)
        src_frame.rowconfigure(1, weight=1)   # listbox grows

        # header row
        hdr = ttk.Frame(src_frame)
        hdr.grid(row=0, column=0, sticky="ew")
        ttk.Label(hdr, text="Source (column C)").pack(side="left")
        ttk.Button(hdr, text="Load Excel…", command=self._load_excel).pack(side="right")

        # source pane
        self.tree_source = ttk.Treeview(src_frame, show="tree", selectmode="browse")
        yscroll_src = ttk.Scrollbar(src_frame, orient="vertical",
                                    command=self.tree_source.yview)
        self.tree_source.configure(yscrollcommand=yscroll_src.set)
        self.tree_source.grid(row=1, column=0, sticky="nsew")
        yscroll_src.grid(row=1, column=1, sticky="ns")

        paned.add(src_frame, weight=1)      # let user drag divider

        # -- Target pane -----------------------------------------------------
        tgt_frame = ttk.Frame(paned, padding=6)
        tgt_frame.columnconfigure(0, weight=1)
        tgt_frame.rowconfigure(1, weight=1)

        ttk.Label(tgt_frame, text="Target hierarchy").grid(row=0, column=0, sticky="w")
        self.tree = ttk.Treeview(tgt_frame, show="tree", selectmode="browse")
        yscroll_tree = ttk.Scrollbar(tgt_frame, orient="vertical",
                                     command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll_tree.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        yscroll_tree.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        paned.add(tgt_frame, weight=2)      # tree usually needs more room

        # --- Bottom: mapping list + buttons --------------------------------
        bottom = ttk.Frame(self, padding=8)
        bottom.grid(row=1, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(3, weight=1)    # mapping list grows

        # button row
        btnrow = ttk.Frame(bottom)
        btnrow.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Button(btnrow, text="Map selected →", command=self._map_clicked)\
            .pack(side="left")
        ttk.Button(btnrow, text="Print mappings", command=self._debug_print)\
            .pack(side="left", padx=4)
        ttk.Button(btnrow, text="Reload tree", command=self._reload_tree)\
            .pack(side="left", padx=(20, 4))
        ttk.Button(btnrow, text="Save mappings…", command=self._save_json)\
            .pack(side="left", padx=4)
        ttk.Button(btnrow, text="Load mappings…", command=self._load_json)\
            .pack(side="left", padx=4)

        ttk.Label(bottom, text="Mappings").grid(row=2, column=0, sticky="w")

        frame_mapbox = ttk.Frame(bottom)
        frame_mapbox.grid(row=3, column=0, sticky="nsew")
        frame_mapbox.columnconfigure(0, weight=1)
        frame_mapbox.rowconfigure(0, weight=1)

        self.lb_mappings = tk.Listbox(frame_mapbox, activestyle="none")
        yscroll_map = ttk.Scrollbar(frame_mapbox, orient="vertical",
                                    command=self.lb_mappings.yview)
        self.lb_mappings.configure(yscrollcommand=yscroll_map.set)
        self.lb_mappings.grid(row=0, column=0, sticky="nsew")
        yscroll_map.grid(row=0, column=1, sticky="ns")

        # --- Pilots pane below Mappings -------------------------------
        ttk.Label(bottom, text="Pilots").grid(row=4, column=0, sticky="w", pady=(10, 0))

        frame_pilots = ttk.Frame(bottom)
        frame_pilots.grid(row=5, column=0, sticky="nsew")
        frame_pilots.columnconfigure(0, weight=1)
        frame_pilots.rowconfigure(0, weight=1)

        self.lb_pilots = tk.Listbox(frame_pilots, activestyle="none")
        yscroll_pilots = ttk.Scrollbar(frame_pilots, orient="vertical",
                                    command=self.lb_pilots.yview)
        self.lb_pilots.configure(yscrollcommand=yscroll_pilots.set)
        self.lb_pilots.grid(row=0, column=0, sticky="nsew")
        yscroll_pilots.grid(row=0, column=1, sticky="ns")

        # Make bottom frame row 5 (pilots) grow as well
        bottom.rowconfigure(5, weight=1)

        # delete mapping button
        ttk.Button(btnrow, text="Delete selected mapping", command=self._delete_selected_mapping).pack(side="left", padx=4)


    # ---------- dynamic tree loaders --------------------------------------

    def _load_target_tree(self) -> dict:
        return {
            "Root": {
                "Account": {
                    "data": self._load_account_leaves()
                },
                "Competencies": self._load_competencies_subtree(),
            }
        }

    # -- Account leaves -----------------------------------------------------

    def _load_account_leaves(self) -> list[str]:
        url = f"{self.config['server'].rstrip('/')}/api/accounts.json"
        headers = {"X-API-KEY": self.config["api_key"]}
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

    # -- Competencies subtree ----------------------------------------------

    def _load_competencies_subtree(self) -> dict:
        url = f"{self.config['server'].rstrip('/')}/api/competencies.json"
        headers = {"X-API-KEY": self.config["api_key"]}
        tree: dict[str, dict[str, list[str]]] = {}

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            curricula = resp.json()

            for cur in curricula:
                cat_branch: dict[str, list[str]] = {}
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

    # ---------- tree population (recursive) -------------------------------

    def _populate_tree(self, subtree, parent_id):
        if isinstance(subtree, dict):
            for key, val in subtree.items():
                node_id = self.tree.insert(parent_id, "end", text=key, open=True)
                self._populate_tree(val, node_id)
        elif isinstance(subtree, (list, tuple)):
            for leaf in subtree:
                self.tree.insert(parent_id, "end", text=leaf)
        else:
            self.tree.insert(parent_id, "end", text=str(subtree))




    # ---------- Load Excel -------------------------------

    def _load_excel(self):
        if pd is None:
            messagebox.showerror(
                "Dependency missing",
                "pandas (and openpyxl) are required:\n\npip install pandas openpyxl"
            )
            return

        fpath = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if not fpath:
            return

        df = pd.read_excel(fpath, sheet_name=0, engine="openpyxl", header=4)
        if df.shape[1] < 3:
            raise ValueError("First sheet has fewer than 3 columns.")
        
        membership_col = 'ACCOUNT'  
        name_col = 'NAME'

        # Extract unique base items from column C
        base_items = sorted(
            {str(v).strip() for v in df.iloc[:, 2].dropna() if str(v).strip()}
        )
        if not base_items:
            raise ValueError("No non‑blank values in column C.")

        # Expand each base item to include /date from and /date to children
        expanded = []
        for item in base_items:
            expanded.append(item)  # base (non-mappable)
            expanded.append(f"{item} / date from")
            expanded.append(f"{item} / date to")
        self.source_items = expanded
        self._refresh_source_tree()

        # extract unique pilots
        df_unique_pilots = df.drop_duplicates(subset=membership_col, keep='first')
        
        account_map = {}
        # Fetch account data from server
        url = f"{self.config['server'].rstrip('/')}/api/accounts.json"
        headers = {"X-API-KEY": self.config["api_key"]}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            accounts = response.json()
            account_map = {int(acc['lid_nummer']): acc['id'] for acc in accounts}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch accounts: {e}")
            return

        self.pilots = []

        for _, row in df_unique_pilots.iterrows():
            membership = row[membership_col]
            name = row[name_col]
            pilot_id = account_map.get(membership, None)  # None if no match
            self.pilots.append((name, membership, pilot_id))

        self._refresh_pilots_listbox()

        # Clear mappings on new load
        self.mappings.clear()
        self._refresh_mapping_listbox()

    def _refresh_source_tree(self):
        self.tree_source.delete(*self.tree_source.get_children())
        parents = {}
        for item in self.source_items:
            if item.endswith("/ date from") or item.endswith("/ date to"):
                base, suffix = item.rsplit("/", 1)
                base = base.strip()
                if base not in parents:
                    parents[base] = self.tree_source.insert("", "end", text=base, open=True)
                self.tree_source.insert(parents[base], "end", text=suffix.strip(), values=[item])

    def _refresh_pilots_listbox(self):
        self.lb_pilots.delete(0, tk.END)
        for name, membership, pilot_id in self.pilots:
            self.lb_pilots.insert(tk.END, f"{membership} — {name} - {pilot_id}")

    # ---------- mapping operations ----------------------------------------

    def _on_tree_double_click(self, _event):
        if self._selected_source() and self._selected_tree_leaf():
            self._create_mapping()

    def _map_clicked(self):
        source = self._selected_source()
        target_sel = self.tree.selection()
        if not source or not target_sel:
            return

        target_id = target_sel[0]
        # Only allow mapping to leaf nodes
        if self.tree.get_children(target_id):
            return

        target_path = self._get_tree_path(target_id)
        pair = (source, target_path)
        if pair not in self.mappings:
            self.mappings.append(pair)
            self._refresh_mapping_listbox()


    def _selected_source(self):
        sel = self.tree_source.selection()
        if not sel:
            return None
        item_id = sel[0]
        parent_id = self.tree_source.parent(item_id)
        if not parent_id:
            return None  # root-level = not mappable
        parent_text = self.tree_source.item(parent_id, "text")
        child_text = self.tree_source.item(item_id, "text")
        return f"{parent_text} / {child_text}"

    def _selected_tree_leaf(self):
        focus = self.tree.focus()
        if focus and not self.tree.get_children(focus):
            return self.tree.item(focus, "text")
        return None

    def _create_mapping(self):
        src = self._selected_source()
        dst = self._selected_tree_leaf()
        if any(m[0] == src for m in self.mappings):
            messagebox.showinfo("Duplicate", f"'{src}' is already mapped.")
            return
        if any(m[1] == dst for m in self.mappings):
            messagebox.showinfo("Duplicate", f"Leaf '{dst}' is already mapped.")
            return
        self.mappings.append((src, dst))
        self.lb_mappings.insert(tk.END, f"{src}  →  {dst}")

    def _delete_selected_mapping(self):
        sel = self.lb_mappings.curselection()
        if not sel:
            messagebox.showinfo("No selection", "Select a mapping to delete.")
            return
        idx = sel[0]
        del self.mappings[idx]
        self._refresh_mapping_listbox()
    

    # ---------- save / load mappings --------------------------------------

    def _save_json(self):
        fpath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not fpath:
            return

        result = {}
        for src, tgt_path in self.mappings:
            tgt_parts = [part.strip() for part in tgt_path.split("///")]
            current = result
            for part in tgt_parts[:-1]:
                current = current.setdefault(part, {})
            current.setdefault(tgt_parts[-1], []).append(src)

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


    def _load_json(self):
        fpath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not fpath:
            return

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.mappings.clear()

        def recurse(obj, path):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    recurse(v, path + [k])
            elif isinstance(obj, list):
                for src in obj:
                    self.mappings.append((src, " /// ".join(path)))

        recurse(data, [])
        self._refresh_mapping_listbox()


    def _get_tree_path(self, item_id):
        parts = []
        while item_id:
            parts.insert(0, self.tree.item(item_id, "text"))
            item_id = self.tree.parent(item_id)
        return " /// ".join(parts)


    def _leaf_exists(self, name: str) -> bool:
        def rec(node):
            if not self.tree.get_children(node):
                return self.tree.item(node, "text") == name
            return any(rec(c) for c in self.tree.get_children(node))
        return any(rec(n) for n in self.tree.get_children(""))

    def _refresh_mapping_listbox(self):
        self.lb_mappings.delete(0, tk.END)
        for src, tgt in self.mappings:
            self.lb_mappings.insert(tk.END, f"{src}  →  {tgt}")


    # ---------- tree reload -----------------------------------------------

    def _reload_tree(self):
        self.target_tree_dict = self._load_target_tree()
        self.tree.delete(*self.tree.get_children(""))
        self._populate_tree(self.target_tree_dict, "")
        self.mappings.clear()
        self._refresh_mapping_listbox()

    # ---------- debug ------------------------------------------------------

    def _debug_print(self):
        print("Current mappings:")
        for s, d in self.mappings:
            print(f"  {s!r} -> {d!r}")
        print("-" * 40)

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    MapperGUI().mainloop()
