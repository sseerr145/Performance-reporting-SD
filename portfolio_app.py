import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from transaction_processor import TransactionProcessor

# Always load the latest test data
DATA_FILE = 'Test_transactions.xlsx'

# Color codes for each consolidation level (matching your screenshot)
LEVEL_COLORS = {
    'Portfolio': '#cbe7fa',        # Light blue
    'Parent company': '#f8d6ea',   # Light pink
    'Account': '#fffde7',          # Light yellow (if needed)
}

LEVELS = ['Portfolio', 'Parent company', 'Account']

# Map columns to their consolidation level
def get_column_level(col):
    for level in LEVELS:
        if f'({level})' in col:
            return level
    return None

def load_sample_data():
    return pd.read_excel(DATA_FILE)

class PortfolioReportingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Portfolio Reporting Tool - WAC Basis")
        self.root.geometry("1700x950")
        self.processor = TransactionProcessor()
        self.data = load_sample_data()
        self.processed_data = self.processor.process_transactions(self.data)
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header_frame, text="Activity View (All Transactions)", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        export_btn = ttk.Button(header_frame, text="📊 Export to Excel", command=self.export_to_excel, style="TButton")
        export_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # --- Super-header Canvas ---
        columns = list(self.processed_data.columns)
        col_levels = [get_column_level(col) for col in columns]
        col_widths = []
        for col in columns:
            if col in ['Portfolio', 'Parent company', 'Legal entity', 'Custodian', 'Account', 'Security', 'Currency', 'B/S', 'Trade ID']:
                width = 120
            elif 'date' in col.lower():
                width = 100
            elif 'Quantity' in col:
                width = 100
            elif 'Cost' in col or 'Price' in col or 'Total' in col or 'Rate' in col or 'Realized Gain/Loss' in col:
                width = 140
            else:
                width = 120
            col_widths.append(width)

        superheader_frame = tk.Frame(main_frame, height=32)
        superheader_frame.pack(fill=tk.X, side=tk.TOP)
        canvas = tk.Canvas(superheader_frame, height=32, bg='white', highlightthickness=0)
        canvas.pack(fill=tk.X, expand=True)

        # Draw merged super-header cells (colored), no color in Treeview columns
        x = 0
        for level in LEVELS:
            indices = [i for i, l in enumerate(col_levels) if l == level]
            if not indices:
                continue
            x0 = sum(col_widths[:indices[0]])
            x1 = sum(col_widths[:indices[-1]+1])
            canvas.create_rectangle(x0, 0, x1, 32, fill=LEVEL_COLORS[level], outline='')
            canvas.create_text((x0 + x1)//2, 16, text=level, font=("Arial", 12, "bold"))

        # --- Treeview ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, show='headings')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree['columns'] = columns

        # Format numbers for display: thousands separator, 2 decimals
        self.display_data = self.processed_data.copy()
        for col in self.display_data.columns:
            if (
                self.display_data[col].dtype in ['float64', 'int64']
                or col.startswith('Realized Gain/Loss')
            ):
                self.display_data[col] = self.display_data[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) and x != '' else ''
                )

        # Set up column headers and widths (no color in Treeview)
        for i, col in enumerate(columns):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[i], anchor=tk.CENTER, stretch=False)

        # Insert data (no color tags)
        for _, row in self.display_data.iterrows():
            values = [row[col] if pd.notna(row[col]) and row[col] != '' else '' for col in columns]
            self.tree.insert('', 'end', values=values)

        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, False))

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        def try_float(val):
            try:
                return float(val.replace(',', ''))
            except (ValueError, TypeError, AttributeError):
                return str(val)
        l.sort(key=lambda t: try_float(t[0]), reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def export_to_excel(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Excel File",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    self.processed_data.to_excel(writer, sheet_name='Activity', index=False)
                messagebox.showinfo("Success", f"Data exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")

def main():
    root = tk.Tk()
    app = PortfolioReportingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 