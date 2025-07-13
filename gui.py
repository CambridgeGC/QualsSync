import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import json

from config import load_config
import api_loader
import excel_loader

class MapperGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel ↔ API‑Tree Mapper")
        self.minsize(900, 600)
        self.config_data = load_config()

        # Data holders
        self.source_items: list[str] = []
        self.mappings: list[tuple[str, str]] = []
        self.pilots: list[tuple[str, str, str]] = []

        self.target_tree_dict = self._load_target_tree()

        self._build_widgets()
        self._populate_tree(self.target_tree_dict, "")

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

        ttk.Label(tgt_frame, text="Target hierarchy").grid(row=0, column=0, sticky="w")
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

    # ----------- Data Loading -----------------------------

    def _load_target_tree(self):
        # Load accounts and competencies subtree from API
        accounts = api_loader.load_account_leaves(self.config_data)
        competencies = api_loader.load_competencies_subtree(self.config_data)
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
        source_items, pilots = excel_loader.load_excel_and_pilots(self.config_data, self.lb_pilots)
        if not source_items:
            return
        self.source_items = source_items
        self.pilots = pilots
        self.tree_source.delete(*self.tree_source.get_children())
        for item in source_items:
            self.tree_source.insert("", "end", text=item, open=True)

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
            else:
                messagebox.showerror("Error", "Invalid mappings JSON format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mappings:\n{e}")

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


if __name__ == "__main__":
    app = MapperGUI()
    app.mainloop()
