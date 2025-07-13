import tkinter as tk
from tkinter import filedialog, messagebox
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

from api_loader import fetch_accounts_map

def load_excel_and_pilots(config, lb_pilots) -> tuple[list[str], list[tuple[str,str,str]]]:
    """
    Returns (expanded source_items, pilots list)
    Also updates the given pilots Listbox widget.
    """
    if pd is None:
        messagebox.showerror(
            "Dependency missing",
            "pandas (and openpyxl) are required:\n\npip install pandas openpyxl"
        )
        return [], []

    fpath = filedialog.askopenfilename(
        title="Select Excel file",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
    )
    if not fpath:
        return [], []

    df = pd.read_excel(fpath, sheet_name=0, engine="openpyxl", header=4)
    if df.shape[1] < 3:
        messagebox.showerror("Error", "First sheet has fewer than 3 columns.")
        return [], []

    membership_col = 'ACCOUNT'  
    name_col = 'NAME'

    # Extract unique base items from column C
    base_items = sorted(
        {str(v).strip() for v in df.iloc[:, 2].dropna() if str(v).strip()}
    )
    if not base_items:
        messagebox.showerror("Error", "No non‑blank values in column C.")
        return [], []

    # Expand each base item to include /date from and /date to children
    expanded = []
    for item in base_items:
        expanded.append(f"{item} / date from")
        expanded.append(f"{item} / date to")

    # Fetch account data from server
    account_map = fetch_accounts_map(config)

    # Extract unique pilots
    df_unique_pilots = df.drop_duplicates(subset=membership_col, keep='first')

    pilots = []
    for _, row in df_unique_pilots.iterrows():
        membership = row[membership_col]
        name = row[name_col]
        pilot_id = account_map.get(membership, None)  # None if no match
        pilots.append((name, membership, pilot_id))

    # Update pilots Listbox
    lb_pilots.delete(0, tk.END)
    for name, membership, pilot_id in pilots:
        lb_pilots.insert(tk.END, f"{membership} — {name} - {pilot_id}")

    return expanded, pilots
