import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import json

from config import load_config
from api_client import ApiClient
from excel_loader import ExcelLoader

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QualsSync - maps and synchronises technical qualifications")
        self.minsize(900, 600)
        self.config_data = load_config()

        # Data holders
        self.source_items: list[str] = []
        self.mappings: list[tuple[str, str]] = []
        self.pilots: list[tuple[str, str, str]] = []

        self.excel_loader = ExcelLoader(self.config_data)
        self.api = ApiClient(self.config_data)

        self._build_widgets()

    # ----------- Widget Layout -----------------------------

    def _build_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew", pady=(8,4), padx=8)

        # Source pane
        src_frame = ttk.Frame(paned, padding=6)
        src_frame.columnconfigure(0, weight=1)
        src_frame.rowconfigure(1, weight=1)

        hdr = ttk.Frame(src_frame)
        hdr.grid(row=0, column=0, sticky="ew")
        ttk.Label(hdr, text="Source (column C)").pack(side="left")
        ttk.Button(hdr, text="Load Excel…", command=self._load_excel).pack(side="right")

        self.tree_source = ttk.Treeview(src_frame, show="tree", selectmode="browse")
        yscroll_src = ttk.Scrollbar(src_frame, orient="vertical", command=self.tree_source.yview)
        self.tree_source.configure(yscrollcommand=yscroll_src.set)
        self.tree_source.grid(row=1, column=0, sticky="nsew")
        yscroll_src.grid(row=1, column=1, sticky="ns")

        paned.add(src_frame, weight=1)

        # Target pane
        tgt_frame = ttk.Frame(paned, padding=6)
        tgt_frame.columnconfigure(0, weight=1)
        tgt_frame.rowconfigure(1, weight=1)

        hdr_tgt = ttk.Frame(tgt_frame)
        hdr_tgt.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr_tgt.columnconfigure(0, weight=1)
        ttk.Label(hdr_tgt, text="Target hierarchy").grid(row=0, column=0, sticky="w")
        ttk.Button(hdr_tgt, text="Load Target Tree", command=self._reload_tree).grid(row=0, column=1, sticky="e")
        self.tree = ttk.Treeview(tgt_frame, show="tree", selectmode="browse")
        yscroll_tree = ttk.Scrollbar(tgt_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll_tree.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        yscroll_tree.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_tree_double_click)
        paned.add(tgt_frame, weight=2)

        # Bottom frame with mapping list and buttons
        bottom = ttk.Frame(self, padding=8)
        bottom.grid(row=1, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(3, weight=1)

        btnrow = ttk.Frame(bottom)
        btnrow.grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Button(btnrow, text="Map selected →", command=self._map_clicked).pack(side="left")
        ttk.Button(btnrow, text="Print mappings", command=self._debug_print).pack(side="left", padx=4)
        ttk.Button(btnrow, text="Reload tree", command=self._reload_tree).pack(side="left", padx=(20,4))
        ttk.Button(btnrow, text="Save mappings…", command=self._save_json).pack(side="left", padx=4)
        ttk.Button(btnrow, text="Load mappings…", command=self._load_json).pack(side="left", padx=4)
        ttk.Button(btnrow, text="Delete selected mapping", command=self._delete_selected_mapping).pack(side="left", padx=4)

        ttk.Label(bottom, text="Mappings").grid(row=2, column=0, sticky="w")

        frame_mapbox = ttk.Frame(bottom)
        frame_mapbox.grid(row=3, column=0, sticky="nsew")
        frame_mapbox.columnconfigure(0, weight=1)
        frame_mapbox.rowconfigure(0, weight=1)

        self.lb_mappings = tk.Listbox(frame_mapbox)
        self.lb_mappings.grid(row=0, column=0, sticky="nsew")
        yscroll_map = ttk.Scrollbar(frame_mapbox, orient="vertical", command=self.lb_mappings.yview)
        self.lb_mappings.configure(yscrollcommand=yscroll_map.set)
        yscroll_map.grid(row=0, column=1, sticky="ns")

        # Pilots Listbox below mappings
        ttk.Label(bottom, text="Pilots").grid(row=4, column=0, sticky="w")
        self.lb_pilots = tk.Listbox(bottom, height=6)
        self.lb_pilots.grid(row=5, column=0, sticky="nsew", pady=(0,6))
        yscroll_pilots = ttk.Scrollbar(bottom, orient="vertical", command=self.lb_pilots.yview)
        self.lb_pilots.configure(yscrollcommand=yscroll_pilots.set)
        yscroll_pilots.grid(row=5, column=1, sticky="ns")

        # Upload button
        self.btn_upload = ttk.Button(
            bottom,
            text="Upload Accounts Data",
            command=self.upload_accounts_data,
            state=tk.DISABLED  # only enabled when ready
        )
        self.btn_upload.grid(row=6, column=0, sticky="ew", pady=(0, 4))

    # ----------- Data Loading -----------------------------

    def _load_target_tree(self):
        # Load accounts and competencies subtree from API
        accounts = self.api.load_account_leaves()
        competencies = self.api.load_competencies_subtree()
        tree = {}
        if accounts and accounts[0] != "(error loading accounts)":
            tree["Accounts"] = accounts
        if competencies and "(error loading competencies)" not in competencies:
            tree["Competencies"] = competencies
        return tree

    def _reload_tree(self):
        self.target_tree_dict = self._load_target_tree()
        self.tree.delete(*self.tree.get_children())
        self._populate_tree(self.target_tree_dict, "")

    def _populate_tree(self, d: dict | list, parent: str):
        if isinstance(d, dict):
            for k, v in d.items():
                iid = self.tree.insert(parent, "end", text=k, open=True)
                self._populate_tree(v, iid)
        elif isinstance(d, list):
            for item in d:
                self.tree.insert(parent, "end", text=item, open=True)
        else:
            # single string or None
            if d:
                self.tree.insert(parent, "end", text=str(d), open=True)

    # ----------- Excel Loading -----------------------------

    def _load_excel(self):
        self.excel_loader.load_excel()

        # Expand base items for left pane
        base_items = sorted(
            {row["type"] for row in self.excel_loader.rows}
        )
        source_items = []
        for item in base_items:
            source_items.append(f"{item} / date from")
            source_items.append(f"{item} / date to")

        # Fetch account data from server
        self.account_map = self.api.fetch_accounts_map()

        # Build unique pilot list
        seen = set()
        pilots = []
        for row in self.excel_loader.rows:
            membership = int(row["membership"])
            name = row["name"]
            if membership not in seen:
                seen.add(membership)
                pilot_id = self.account_map.get(membership, None)
                pilots.append((name, membership, pilot_id))
        
        self.source_items = source_items
        self.pilots = pilots
        
        # Update pilots listbox
        self.lb_pilots.delete(0, tk.END)
        for name, membership, pilot_id in self.pilots:
            self.lb_pilots.insert(tk.END, f"{membership} — {name} - {pilot_id}")

        # Update source items listbox
        self.tree_source.delete(*self.tree_source.get_children())
        for item in source_items:
            self.tree_source.insert("", "end", text=item, open=True)

        # Update upload button state
        self._update_upload_button_state()            

    # ----------- Mapping Logic -----------------------------

    def _map_clicked(self):
        sel_source = self.tree_source.selection()
        sel_target = self.tree.selection()
        if not sel_source or not sel_target:
            messagebox.showinfo("Select items", "Please select an item on both Source and Target trees.")
            return

        source_text = self.tree_source.item(sel_source[0])["text"]
        target_text = self._get_full_tree_path(sel_target[0])

        # Only allow mapping leaves in target tree
        if self.tree.get_children(sel_target[0]):
            messagebox.showwarning("Mapping restriction", "Only leaf nodes in target tree can be mapped.")
            return

        self.mappings.append((source_text, target_text))
        self._update_mappings_list()
        # Update upload button state
        self._update_upload_button_state()          

    def _update_mappings_list(self):
        self.lb_mappings.delete(0, tk.END)
        for source, target in self.mappings:
            self.lb_mappings.insert(tk.END, f"{source} → {target}")


    def _delete_selected_mapping(self):
        sel = self.lb_mappings.curselection()
        if not sel:
            return
        index = sel[0]
        del self.mappings[index]
        self._update_mappings_list()

    def _get_full_tree_path(self, item_id):
        parts = []
        while item_id:
            parts.insert(0, self.tree.item(item_id)["text"])
            item_id = self.tree.parent(item_id)
        return " / ".join(parts)


    # ----------- Save/Load mappings -----------------------

    def _save_json(self):
        if not self.mappings:
            messagebox.showinfo("No mappings", "There are no mappings to save.")
            return
        fname = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save mappings to JSON",
        )
        if not fname:
            return
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(self.mappings, f, indent=2)
            messagebox.showinfo("Saved", f"Mappings saved to {fname}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def _load_json(self):
        fname = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Load mappings from JSON",
        )
        if not fname:
            return
        try:
            with open(fname, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list) and all(isinstance(t, list) or isinstance(t, tuple) and len(t)==2 for t in loaded):
                self.mappings = [(str(src), str(tgt)) for src, tgt in loaded]
                self._update_mappings_list()
                # Update upload button state
                self._update_upload_button_state()
            else:
                messagebox.showerror("Error", "Invalid mappings JSON format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mappings:\n{e}")

    # ----------- Save data into Gliding.App ----------

    def upload_accounts_data(self):
        updates_by_pilot = {}

        for excel_value_type, full_key in self.mappings:
            if not full_key.startswith("Accounts /"):
                continue

            field_name = full_key.split(" / ", 1)[1]
            row_type = excel_value_type.split(' / ', 1)[0]

            for _, membership, pilot_id in self.pilots:
                if pilot_id is None:
                    continue

                matching_rows = [
                    r for r in self.excel_loader.rows
                    if str(r["membership"]) == str(membership) and r["type"] == row_type
                ]

                if not matching_rows:
                    continue

                if pilot_id not in updates_by_pilot:
                    updates_by_pilot[pilot_id] = {}

                for r in matching_rows:
                    if r["value_from"]:
                        updates_by_pilot[pilot_id][field_name] = r["value_from"]
                    if r["value_to"]:
                        to_field = field_name.replace("_from", "_to")
                        updates_by_pilot[pilot_id][to_field] = r["value_to"]

        for pilot_id, data in updates_by_pilot.items():
            try:
                self.api.put_account_data(pilot_id, data)
            except Exception as e:
                print(f"Failed to upload pilot {pilot_id}: {e}")


    # ----------- Debug -----------------------

    def _debug_print(self):
        print("Source items:")
        for si in self.source_items:
            print(f" - {si}")
        print("\nMappings:")
        for src, tgt in self.mappings:
            print(f"{src} -> {tgt}")

    # ----------- Tree double click -----------------------

    def _on_tree_double_click(self, event):
        # Allow mapping on double-click: source must be selected too
        sel_target = self.tree.selection()
        sel_source = self.tree_source.selection()
        if sel_target and sel_source:
            self._map_clicked()

    # ----------- Enable update --------------

    def _update_upload_button_state(self):
        has_excel = self.excel_loader.has_excel()
        has_any_mappings = bool(self.mappings)
        if has_excel and has_any_mappings:
            self.btn_upload.config(state=tk.NORMAL)
        else:
            self.btn_upload.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = MapperGUI()
    app.mainloop()
