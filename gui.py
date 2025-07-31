import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import traceback

import config
from sync_service import SyncService, CancelledByUserError
from competency import Competency

import threading


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QualsSync - maps and synchronises technical qualifications - " + config.VERSION)
        self.geometry("1800x900")   
        self.minsize(1200, 700)     

        self.withdraw()  # Hide the window during setup
        self.after(0, lambda: self._set_initial_position())  # Defer positioning

        self.config_data = config.load_config()
        self.service = SyncService(self.config_data)

        # Data holders
        self._competency_map: dict[str, Competency] = {}

        self._build_widgets()
        

    # ----------- Widget Layout -----------------------------

    def _build_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) 
        self.rowconfigure(1, weight=2) 

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

        # Predefined values pane
        predefined_frame = ttk.Frame(paned, padding=6)
        predefined_frame.columnconfigure(0, weight=1)
        predefined_frame.rowconfigure(1, weight=1)
        ttk.Label(predefined_frame, text="Predefined Values").grid(row=0, column=0, sticky="w")
        self.tree_predefined = ttk.Treeview(predefined_frame, show="tree", selectmode="browse", height=2)
        self.tree_predefined.grid(row=1, column=0, sticky="nsew")
        self.tree_predefined.insert("", "end", text="Current DateTime")
        self.tree_predefined.insert("", "end", text="App Name (QualsSync)")
        paned.add(predefined_frame, weight=0)

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

        self.tree_source.bind("<<TreeviewSelect>>", self._on_source_tree_select)
        self.tree_predefined.bind("<<TreeviewSelect>>", self._on_source_tree_select)

        paned.add(tgt_frame, weight=2)

        # Bottom frame with mapping list and buttons
        bottom = ttk.Frame(self, padding=8)
        bottom.grid(row=1, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        for r in (3, 5, 8):  # mapping box, pilots box, log box
            bottom.rowconfigure(r, weight=1)

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

        # Upload section 
        upload_frame = ttk.Frame(bottom)
        upload_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        upload_frame.columnconfigure(0, weight=1)
        # Upload button
        self.btn_upload = ttk.Button(
            upload_frame,
            text="Upload Data",
            command=self.upload_data,
            state=tk.DISABLED
        )
        self.btn_upload.grid(row=0, column=0, sticky="ew")
        # "Compare only" checkbox
        self.check_only_var = tk.BooleanVar()
        self.chk_check_only = ttk.Checkbutton(
            upload_frame,
            text="Compare only (don't update)",
            variable=self.check_only_var
        )
        self.chk_check_only.grid(row=0, column=1, padx=(8, 0), sticky="e")
      

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

    def _set_initial_position(self):
        self.update_idletasks()      # Ensure layout is calculated
        self.geometry("+50+30")      # Move window near top-left
        self.deiconify()             # Show the window if it was hidden

    # ----------- Data Loading -----------------------------

    def _load_target_tree(self):
        def background_task(cancel_event):
            return self.service.load_target_tree(cancel_event)
        
        def callback(tree):
            if tree:
                self.target_tree_dict = tree
                self.tree.delete(*self.tree.get_children())
                self._populate_tree(self.target_tree_dict, "")
            else:
                self.log_warning("No target data loaded.")

        self.run_with_modal("Loading...", "Loading Target Gliding App data. Please wait...", background_task, callback)


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
            return

        def background_task(cancel_event):
            return self.service.load_excel_data(fpath, cancel_event)

        def callback(result):
            source_items, pilots = result
            
            # Update pilots listbox
            self.lb_pilots.delete(0, tk.END)
            for name, membership, pilot_id in pilots:
                pilot_id_str = pilot_id if pilot_id else "NOT FOUND"
                self.lb_pilots.insert(tk.END, f"{membership} — {name} - {pilot_id_str}")

            # Update source items listbox
            self.tree_source.delete(*self.tree_source.get_children())
            for item in source_items:
                self.tree_source.insert("", "end", text=item, open=True)

            # Update upload button state
            self._update_upload_button_state()

        self.run_with_modal("Loading..", "Loading Excel file. Please wait...", background_task, callback)
        
         

    # ----------- Mapping Logic -----------------------------

    def _on_source_tree_select(self, event):
        """Ensures only one source tree has a selection at a time."""
        widget = event.widget
        if widget == self.tree_source:
            if self.tree_predefined.selection():
                self.tree_predefined.selection_set("")  # Deselect all in other tree
        elif widget == self.tree_predefined:
            if self.tree_source.selection():
                self.tree_source.selection_set("")  # Deselect all in other tree

    def _map_clicked(self):
        sel_source_id = self.tree_source.selection()
        sel_predefined_id = self.tree_predefined.selection()

        sel_target_id = self.tree.selection()
        if (not sel_source_id and not sel_predefined_id) or not sel_target_id:
            messagebox.showinfo("Select items", "Please select an item from one of the source lists and from the target tree.")
            return

        sel_target_id = sel_target_id[0]

        # Only allow mapping leaves in target tree
        if self.tree.get_children(sel_target_id):
            messagebox.showwarning("Mapping restriction", "Only leaf nodes in target tree can be mapped.")
            return
        
        is_predefined = bool(sel_predefined_id)
        if is_predefined:
            source_id = sel_predefined_id[0]
            source_tree = self.tree_predefined
        else:
            source_id = sel_source_id[0]
            source_tree = self.tree_source

        source_text = source_tree.item(source_id)["text"]
        target_text = self._get_full_tree_path(sel_target_id)
        is_competency = target_text.startswith("Competencies")

        if is_predefined and is_competency:
            messagebox.showerror("Mapping Error", "Predefined values can only be mapped to Account fields.")
            return

        if is_competency:
            self.unsplit_source_item(source_text)

        target_item = self._competency_map.get(sel_target_id) or target_text
        
        self.service.add_mapping(source_text, target_item, is_competency)
        self._update_mappings_list()
        self._update_upload_button_state()

    def _update_mappings_list(self):
        self.lb_mappings.delete(0, tk.END)
        display_items = self.service.get_mappings_for_display()
        for item in display_items:
            self.lb_mappings.insert(tk.END, item)


    def _delete_selected_mapping(self):
        sel = self.lb_mappings.curselection()
        if not sel:
            return
        index = sel[0]
        self.service.delete_mapping(index)
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
        if not self.service.mappings:
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
            self.service.save_mappings(fname)
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
            self.service.load_mappings(fname)
            self._update_mappings_list()
            self._update_upload_button_state()
            self.unsplit_mappings_to_competencies()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mappings:\n{e}")

    def unsplit_mappings_to_competencies(self):
        for source_label, target in self.service.mappings:
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
        check_only = self.check_only_var.get()

        def task(cancel_event):
            # Clear previous log entries before starting
            self.txt_log.config(state='normal')
            self.txt_log.delete(1.0, tk.END)
            self.txt_log.config(state='disabled')
            return self.service.upload_data(check_only, self.log, cancel_event)

        def on_complete(result):
            # The service returns a summary message
            self.log_info(f"\n----- {result} -----")

        self.run_with_modal("Uploading.." if not check_only else "Comparing..",
            "Uploading data to Gliding.App. Please wait..." if not check_only else "Comparing data with Gliding.App. Please wait...",
            task, on_complete)

        


    # ----------- Tree double click -----------------------

    def _on_tree_double_click(self, event):
        # Allow mapping on double-click: source must be selected too
        sel_target = self.tree.selection()
        sel_source = self.tree_source.selection()
        sel_predefined = self.tree_predefined.selection()
        if sel_target and (sel_source or sel_predefined):
            self._map_clicked()

    # ----------- Enable update --------------

    def _update_upload_button_state(self):
        has_excel = self.service.excel_loader.has_excel()
        has_any_mappings = bool(self.service.mappings)
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
        cancel_event = threading.Event()

        # Create modal dialog
        modal = tk.Toplevel(self)
        modal.title(title)
        modal.transient(self)
        modal.grab_set()  # Make it modal
        modal.resizable(False, False)
        modal.protocol("WM_DELETE_WINDOW", lambda: None)
        label = tk.Label(modal, text=message, padx=20, pady=20)
        label.pack()

        def on_cancel():
            cancel_button.config(state=tk.DISABLED, text="Cancelling...")
            cancel_event.set()

        cancel_button = ttk.Button(modal, text="Cancel", command=on_cancel)
        cancel_button.pack(pady=(0, 10))


        # Center the modal
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (modal.winfo_reqwidth() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (modal.winfo_reqheight() // 2)
        modal.geometry(f"+{x}+{y}")

        def worker():
            try:
                result = task(cancel_event)
            except Exception as e:
                result = e
            def finish():
                modal.destroy()
                if isinstance(result, CancelledByUserError):
                    self.log_info(str(result))
                elif isinstance(result, Exception):
                    #show the whole call stack
                    tb_lines = traceback.format_exception(type(result), result, result.__traceback__)
                    tb_str = ''.join(tb_lines)
                    messagebox.showerror("Error", tb_str)
                else:
                    if on_complete and not cancel_event.is_set():
                        on_complete(result)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

