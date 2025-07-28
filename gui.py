import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import traceback

import config
from api_client import ApiClient
from excel_loader import ExcelLoader

from competency import Competency
from serializer import Serializer

import threading


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QualsSync - maps and synchronises technical qualifications - " + config.VERSION)
        self.minsize(900, 600)
        self.config_data = config.load_config()

        # Data holders
        self.source_items: list[str] = []
        self.mappings: list[tuple[str, str | Competency]] = []
        self.pilots: list[tuple[str, str, str]] = []
        self._competency_map: dict[str, Competency] = {}

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
        ttk.Button(hdr_tgt, text="Load Target Tree", command=self._load_target_tree).grid(row=0, column=1, sticky="e")
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
        bottom.rowconfigure(8, weight=1)

        btnrow = ttk.Frame(bottom)
        btnrow.grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Button(btnrow, text="Map selected →", command=self._map_clicked).pack(side="left")
        ttk.Button(btnrow, text="Save mappings…", command=self._serialise_json).pack(side="left", padx=4)
        ttk.Button(btnrow, text="Load mappings…", command=self._deserlialise_json).pack(side="left", padx=4)
        ttk.Button(btnrow, text="Delete selected mapping", command=self._delete_selected_mapping).pack(side="left", padx=4)
        ttk.Button(btnrow, text="TODO: Verify mappings (currently inactive)", command=self._verify_mappings).pack(side="left", padx=4)

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
            text="Upload Data",
            command=self.upload_data,
            state=tk.DISABLED  # only enabled when ready
        )
        self.btn_upload.grid(row=6, column=0, sticky="ew", pady=(0, 4))

        # Log textbox
        ttk.Label(bottom, text="Log").grid(row=7, column=0, sticky="w")
        self.txt_log = tk.Text(bottom, height=5, state='disabled', wrap="word")
        self.txt_log.grid(row=8, column=0, columnspan=2, sticky="nsew")
        yscroll_log = ttk.Scrollbar(bottom, orient="vertical", command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=yscroll_log.set)
        yscroll_log.grid(row=8, column=2, sticky="ns")
        self.txt_log.tag_configure("info", foreground="black")
        self.txt_log.tag_configure("success", foreground="green")
        self.txt_log.tag_configure("warning", foreground="orange")
        self.txt_log.tag_configure("error", foreground="red", background="#ffeeee")

    # ----------- Data Loading -----------------------------

    def _load_target_tree(self):
        def background_task():
            # Load accounts and competencies subtree from API
            accounts = self.api.load_account_leaves()
            competencies = self.api.load_competencies_subtree()
            tree = {}
            if accounts and accounts[0] != "(error loading accounts)":
                tree["Accounts"] = accounts
            if competencies and "(error loading competencies)" not in competencies:
                tree["Competencies"] = competencies
            return tree
        def callback(tree):
            self.target_tree_dict = tree
            self.tree.delete(*self.tree.get_children())
            self._populate_tree(self.target_tree_dict, "")
        self.run_with_modal("Loading..", "Loading Target Gliding App competencies . Please wait...", background_task, callback)


    def _populate_tree(self, d: dict | list, parent: str):
        if isinstance(d, dict):
            for k, v in d.items():
                iid = self.tree.insert(parent, "end", text=k, open=True)
                self._populate_tree(v, iid)
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, Competency):
                    iid = self.tree.insert(parent, "end", text=item.name, values=[item], open=True)
                    self._competency_map[iid] = item
                else:
                    self.tree.insert(parent, "end", text=str(item), open=True)
        else:
            # single string or None
            if d:
                self.tree.insert(parent, "end", text=str(d), open=True)

    # ----------- Excel Loading -----------------------------

    def _load_excel(self):
        fpath = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if not fpath:
            return [], []
        
        def background_task():
            self.excel_loader.load_excel(fpath)

            # Expand base items for left pane
            base_items = sorted(
                {row["type"] for row in self.excel_loader.rows}
            )
            source_items = []
            for item in base_items:
                source_items.append(f"{item} / date from")
                source_items.append(f"{item} / date to")

            # Fetch account data from server, to get pilots' ids
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
            
            return source_items, pilots
        
        def callback(result):
            self.source_items, self.pilots = result
            # Update pilots listbox
            self.lb_pilots.delete(0, tk.END)
            for name, membership, pilot_id in self.pilots:
                self.lb_pilots.insert(tk.END, f"{membership} — {name} - {pilot_id}")

            # Update source items listbox
            self.tree_source.delete(*self.tree_source.get_children())
            for item in self.source_items:
                self.tree_source.insert("", "end", text=item, open=True)

            # Update upload button state
            self._update_upload_button_state()   
        
        self.run_with_modal("Loading..", "Loading Excel file. Please wait...", background_task, callback)
        
         

    # ----------- Mapping Logic -----------------------------

    def _map_clicked(self):
        sel_source = self.tree_source.selection()
        sel_target = self.tree.selection()
        if not sel_source or not sel_target:
            messagebox.showinfo("Select items", "Please select an item on both Source and Target trees.")
            return

        # Only allow mapping leaves in target tree
        if self.tree.get_children(sel_target[0]):
            messagebox.showwarning("Mapping restriction", "Only leaf nodes in target tree can be mapped.")
            return
        
        source_text = self.tree_source.item(sel_source[0])["text"]
        target_iid = sel_target[0]
        target_text = self._get_full_tree_path(target_iid)

        if target_text.startswith("Competencies"):
            self.unsplit_source_item(source_text)
            # Truncate date_from / date_to
            source_text = source_text[:source_text.rfind(" / ")] if " / " in source_text else source_text

        # Try to get a Competency object from the iid
        target_competency = self._competency_map.get(target_iid)
        if target_competency:
            target = target_competency
        else:
            target = target_text  # fallback if it's not a competency

        self.mappings.append((source_text, target))
        self._update_mappings_list()
        # Update upload button state
        self._update_upload_button_state()          

    def _update_mappings_list(self):
        self.lb_mappings.delete(0, tk.END)
        for source, target in self.mappings:
            if isinstance(target, Competency):
                target_label = target.path
            else:
                target_label = target
            self.lb_mappings.insert(tk.END, f"{source} → {target_label}")


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


    # ----------- Serialisation -----------------------

    def _verify_mappings(self):
        #TODO
        messagebox.showinfo("Not implemented", "A mapping file is only valid against the environment it was created from: if you've loaded the mappings, ensure they have been created against the environment you are pointing at in the config.json file. In the future, a verify&correct functionality will be implemented.")
        return

    def _serialise_json(self):
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
            Serializer(fname).serialize(self.mappings)
            messagebox.showinfo("Saved", f"Mappings saved to {fname}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def _deserlialise_json(self):
        fname = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Load mappings from JSON",
        )
        if not fname:
            return
        try:
            self.mappings.clear()
            self.mappings = Serializer(fname).deserialize()
            self._update_mappings_list()
            self._update_upload_button_state()
            self.unsplit_mappings_to_competencies()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mappings:\n{e}")

    def unsplit_mappings_to_competencies(self):
        for source_label, target in self.mappings:
            if isinstance(target, Competency):
                self.unsplit_source_item(source_label)        

    def unsplit_source_item(self, base_item):
        if base_item.endswith(" / date from"):
            base_item = base_item.replace(" / date from", "")
        elif base_item.endswith(" / date to"):
            base_item = base_item.replace(" / date to", "")        
        from_label = f"{base_item} / date from"
        to_label = f"{base_item} / date to"

        # Get list of items and their positions
        all_items = self.tree_source.get_children()
        positions = []

        # Find and remove split items
        for iid in all_items:
            text = self.tree_source.item(iid, 'text')
            if text == from_label or text == to_label:
                positions.append(all_items.index(iid))
                self.tree_source.delete(iid)

        if not positions:
            return  # Nothing to insert

        # Compute insert position (e.g., min of removed items)
        insert_index = min(positions)

        # Recreate the base item at the same position
        new_iid = self.tree_source.insert('', insert_index, text=base_item)

        # Select and focus the new item
        self.tree_source.selection_set(new_iid)
        self.tree_source.focus(new_iid)
        self.tree_source.see(new_iid)


    # ----------- Save data into Gliding.App ----------

    def upload_data(self):
        def task():
            successful_updates = 0
            for name, membership, account in self.pilots:
                if account is None:
                    continue    
                pilot_id = account.get("id")

                matching_rows = [
                    r for r in self.excel_loader.rows
                    if str(r["membership"]) == str(membership)
                ]
                if not matching_rows:
                    continue        

                successful_updates += self._upload_account_data(pilot_id, name, matching_rows, account.get("data"))
                successful_updates += self._upload_competencies_data(pilot_id, name, matching_rows)
            
            if (successful_updates > 0):
                self.log_info(f"updated {successful_updates} competencies")
            else:
                self.log_info("data was already up to date, nothing changed.")
            # reload accounts with updated information.
            self.account_map = self.api.fetch_accounts_map()
            return f"Upload completed. Updated {successful_updates} competencies"

        self.run_with_modal("Uploading..", "Uploading data to Gliding.App. Please wait...", task)

    def _upload_competencies_data(self, pilot_id, name, matching_rows):
        successful_updates = 0
        pilot_current_competencies = None
        for excel_value_type, full_key in self.mappings:
            if not isinstance(full_key, Competency):
                continue

            if (pilot_current_competencies == None):
                pilot_current_competencies = self.api.get_competencies_by_pilot(pilot_id)

            competency = full_key
            row_type = excel_value_type.split(' / ', 1)[0]

            row = next((r for r in matching_rows if r["type"] == row_type), None)
            if row is None:
                continue #it means the pilot doesn't have this competency

            if Competency.should_assign_based_on_dates(row["date from"], row["date to"]):
                if competency.id not in pilot_current_competencies or pilot_current_competencies[competency.id].has_changed_compared_to_current(row["date from"], row["date to"]):
                    try:
                        self.api.assign_competency(pilot_id, competency.id, row["date from"], row["date to"])
                        self.log_success(f"Assigned competency to pilot {name}: {competency.name}")
                        successful_updates += 1
                    except Exception as e:
                        self.log_error(f"Failed to assign competency {competency.name} to pilot {name}")
            else:
                try:
                    self.api.revoke_competency(pilot_id, competency.id)
                    self.log_warning(f"Revoked competency to pilot {name}: {competency.name}")
                    successful_updates += 1
                except Exception as e:
                    self.log_error(f"Failed to revoke competency {competency.name} to pilot {name}")
        return successful_updates

    
    def _upload_account_data(self, pilot_id, name, matching_rows, account_data):
            updates = {}
            successful_updates = 0

            for excel_value_type, full_key in self.mappings:
                if isinstance(full_key, Competency):
                    continue

                field_name = full_key.split(" / ", 1)[1]
                row_type = excel_value_type.split(" / ", 1)[0]
                row_subtype_from_to = excel_value_type.split(" / ", 1)[1]

                for r in matching_rows:
                    if r["type"] != row_type:
                        continue

                    new_value = r.get(row_subtype_from_to)
                    if new_value is not None and account_data.get(field_name) != new_value:
                        updates[field_name] = new_value

            if updates:
                try:
                    self.api.put_account_data(pilot_id, updates)
                    self.log_success(f"Uploaded account data for pilot {name}: {updates}")
                    successful_updates += 1
                except Exception as e:
                    self.log_error(f"Failed to upload account data for pilot {name}")
                    self.log_error(f"attempted updates: {updates}")
                    self.log_error(f"error: {e}")
                    self.log_error(f"------------------------------")

            return successful_updates
        


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

    # ----------- Log Window -----------------

    def log(self, message: str, tag: str = None):
        self.txt_log.config(state='normal')
        if tag:
            self.txt_log.insert(tk.END, message + "\n", tag)
        else:
            self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state='disabled') 

    def log_error(self, message):
        self.log(message, "error") 

    def log_success(self, message):
        self.log(message, "success") 

    def log_info(self, message):
        self.log(message, "info") 

    def log_warning(self, message):
        self.log(message, "warning") 

    # ----------- don't lock the UI when working -----------

    def run_with_modal(self, title, message, task, on_complete=None):
        # Create modal dialog
        modal = tk.Toplevel(self)
        modal.title(title)
        modal.transient(self)
        modal.grab_set()  # Make it modal
        modal.resizable(False, False)
        modal.protocol("WM_DELETE_WINDOW", lambda: None)
        label = tk.Label(modal, text=message, padx=20, pady=20)
        label.pack()

        # Center the modal
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (modal.winfo_reqwidth() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (modal.winfo_reqheight() // 2)
        modal.geometry(f"+{x}+{y}")

        def worker():
            try:
                result = task()
            except Exception as e:
                result = e
            def finish():
                modal.destroy()
                if isinstance(result, Exception):
                    #show the whole call stack
                    tb_lines = traceback.format_exception(type(result), result, result.__traceback__)
                    tb_str = ''.join(tb_lines)
                    messagebox.showerror("Error", tb_str)
                else:
                    if on_complete:
                        on_complete(result)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

