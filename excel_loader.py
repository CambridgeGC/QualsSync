try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None
from datetime import datetime, timedelta
import dateutil.parser


class ExcelLoader:
    def __init__(self, config):
        self.config = config
        self.rows = []

    def has_excel(self) -> bool:
        return bool(self.rows) 

    def load_excel(self, fpath):
        """
        Loads Excel file, updates pilots listbox, populates internal rows and pilots.
        Returns (expanded source_items, pilots list).
        """

        if not pd:
            raise ImportError("The 'pandas' and 'openpyxl' libraries are required to read Excel files.")

        try:
            df = pd.read_excel(fpath, sheet_name=0, engine="openpyxl", header=4)
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}") from e

        if df.shape[1] < 3:
            raise ValueError("Excel file error: First sheet has fewer than 3 columns.")

        membership_col = 'ACCOUNT'
        name_col = 'NAME'

        # Extract rows
        self.rows = []
        for _, row in df.iterrows():
            membership = str(row[membership_col]).strip()
            name = str(row[name_col]).strip()
            row_type = str(row.iloc[2]).strip()
            value_from = self._parse_excel_date(row.iloc[4])
            value_to = self._parse_excel_date(row.iloc[5])
            self.rows.append({
                "membership": membership,
                "name": name,
                "type": row_type,
                "date from": value_from,
                "date to": value_to
            })
    
    @staticmethod
    def _parse_excel_date(value):
        if value is None or value == '':
            return None
        try:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            if isinstance(value, (int, float)):
                # Excel serial date
                excel_epoch = datetime(1899, 12, 30)
                return (excel_epoch + timedelta(days=int(value))).strftime("%Y-%m-%d")
            if isinstance(value, str):
                return dateutil.parser.parse(value, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            return None
