import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox,
                             QHeaderView, QFrame, QSplitter, QProgressBar, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
import pandas as pd
from transaction_processor import TransactionProcessor
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

DATA_FILE = 'Test_transactions.xlsx'

# Column grouping metadata for header styling
COLUMN_GROUPS = [
    {
        "section": "Portfolio",
        "color": QColor(203, 231, 250),  # Light blue
        "fields": [
            "Transaction Cost USD", "Transaction Cost CCY", "Cumulative Quantity",
            "Cumulative Cost CCY", "Cumulative Cost USD", "Cost per Unit USD",
            "Cost per Unit CCY", "Realized Gain/Loss CCY", "Realized Gain/Loss USD",
        ],
    },
    {
        "section": "Parent company",
        "color": QColor(248, 214, 234),  # Light pink
        "fields": [
            "Transaction Cost USD", "Transaction Cost CCY", "Cumulative Quantity",
            "Cumulative Cost CCY", "Cumulative Cost USD", "Cost per Unit USD",
            "Cost per Unit CCY", "Realized Gain/Loss CCY", "Realized Gain/Loss USD",
        ],
    },
    {
        "section": "Legal entity",
        "color": QColor(255, 253, 231),  # Light yellow
        "fields": [
            "Transaction Cost USD", "Transaction Cost CCY", "Cumulative Quantity",
            "Cumulative Cost CCY", "Cumulative Cost USD", "Cost per Unit USD",
            "Cost per Unit CCY", "Realized Gain/Loss CCY", "Realized Gain/Loss USD",
        ],
    },
    {
        "section": "Account",
        "color": QColor(232, 245, 232),  # Light green
        "fields": [
            "Transaction Cost USD", "Transaction Cost CCY", "Cumulative Quantity",
            "Cumulative Cost CCY", "Cumulative Cost USD", "Cost per Unit USD",
            "Cost per Unit CCY", "Realized Gain/Loss CCY", "Realized Gain/Loss USD",
        ],
    },
]

LEVELS = [grp["section"] for grp in COLUMN_GROUPS]
LEVEL_COLORS = {grp["section"]: grp["color"] for grp in COLUMN_GROUPS}

def get_column_level(col: str) -> str | None:
    """Get the consolidation level for a column"""
    for level in LEVELS:
        if f"({level})" in col:
            return level
    return None

def load_sample_data():
    """Load sample data from Excel file"""
    if os.path.exists(DATA_FILE):
        return pd.read_excel(DATA_FILE)
    else:
        # Create sample data if file doesn't exist
        return create_sample_data()

def create_sample_data():
    """Create sample transaction data for testing"""
    data = {
        'Portfolio': ['Portfolio 1', 'Portfolio 1', 'Portfolio 2', 'Portfolio 2'],
        'Parent company': ['Parent 1', 'Parent 1', 'Parent 2', 'Parent 2'],
        'Legal entity': ['Legal 1', 'Legal 1', 'Legal 2', 'Legal 2'],
        'Custodian': ['Cust 1', 'Cust 1', 'Cust 2', 'Cust 2'],
        'Account': ['Acc 1', 'Acc 1', 'Acc 2', 'Acc 2'],
        'Security': ['AAPL', 'AAPL', 'MSFT', 'MSFT'],
        'Currency': ['USD', 'USD', 'USD', 'USD'],
        'B/S': ['Buy', 'Sell', 'Buy', 'Buy'],
        'Trade ID': ['T001', 'T002', 'T003', 'T004'],
        'Trade date': ['2024-01-01', '2024-01-15', '2024-01-01', '2024-01-20'],
        'Settle date': ['2024-01-03', '2024-01-17', '2024-01-03', '2024-01-22'],
        'Quantity': [100, -50, 200, 150],
        'Price': [150.00, 160.00, 300.00, 310.00],
        'FX rate': [1.0, 1.0, 1.0, 1.0],
        'Total (Original CCY)': [15000.00, -8000.00, 60000.00, 46500.00],
        'Total USD': [15000.00, -8000.00, 60000.00, 46500.00]
    }
    return pd.DataFrame(data)

class DataProcessorThread(QThread):
    """Thread for processing data to avoid UI freezing"""
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)
    
    def __init__(self, data, processor):
        super().__init__()
        self.data = data
        self.processor = processor
    
    def run(self):
        try:
            processed_data = self.processor.process_transactions(self.data)
            self.finished.emit(processed_data)
        except Exception as e:
            self.error.emit(str(e))

class CustomTableWidget(QTableWidget):
    """Custom table widget with enhanced styling and functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
    
    def setup_table(self):
        """Setup table appearance and behavior"""
        # Set table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)
        
        # Configure header
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setHighlightSections(True)
        
        # Set header height (this is where PyQt5 shines!)
        header.setFixedHeight(80)  # Easy header height control!
        
        # Configure vertical header
        vheader = self.verticalHeader()
        vheader.setVisible(False)
        
        # Set row height
        self.verticalHeader().setDefaultSectionSize(30)
        
        # Set font
        font = QFont("Arial", 10)
        self.setFont(font)
        
        # Set header font
        header_font = QFont("Arial", 10, QFont.Bold)
        header.setFont(header_font)
    
    def set_header_colors(self, column_colors):
        """Set header background colors for different consolidation levels"""
        header = self.horizontalHeader()
        for col, color in enumerate(column_colors):
            if col < self.columnCount():
                # Create a palette with the desired background color
                palette = header.palette()
                palette.setColor(QPalette.Button, color)
                header.setPalette(palette)
                
                # Force header update
                header.updateSection(col)

class PortfolioReportingApp(QMainWindow):
    """Main portfolio reporting application"""
    
    def __init__(self):
        super().__init__()
        self.processor = TransactionProcessor()
        self.data = None
        self.processed_data = None
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Portfolio Reporting Tool - WAC Basis")
        self.setGeometry(100, 100, 1900, 1100)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create header
        self.create_header(main_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_activity_tab()
        self.create_holdings_tab()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_header(self, layout):
        """Create the application header"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Box)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border: none;
                border-radius: 5px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Title
        title_label = QLabel("Portfolio Reporting Tool - WAC Basis")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Buttons
        load_btn = QPushButton("📁 Load Excel File")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        load_btn.clicked.connect(self.load_file)
        header_layout.addWidget(load_btn)
        
        export_btn = QPushButton("📊 Export to Excel")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        export_btn.clicked.connect(self.export_to_excel)
        header_layout.addWidget(export_btn)
        
        layout.addWidget(header_frame)
    
    def create_activity_tab(self):
        """Create the activity view tab"""
        activity_widget = QWidget()
        activity_layout = QVBoxLayout(activity_widget)
        
        # Activity subtitle
        subtitle = QLabel("All Transactions with Multi-Level Consolidation")
        subtitle.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")
        activity_layout.addWidget(subtitle)
        
        # Create activity table
        self.activity_table = CustomTableWidget()
        activity_layout.addWidget(self.activity_table)
        
        self.tab_widget.addTab(activity_widget, "📈 Activity View")
    
    def create_holdings_tab(self):
        """Create the holdings view tab"""
        holdings_widget = QWidget()
        holdings_layout = QVBoxLayout(holdings_widget)
        
        # Controls frame
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        # Level selector
        level_label = QLabel("Consolidation Level:")
        level_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(level_label)
        
        self.holdings_level_combo = QComboBox()
        self.holdings_level_combo.addItems(["Portfolio", "Parent company", "Legal entity", "Account"])
        self.holdings_level_combo.setCurrentText("Portfolio")
        self.holdings_level_combo.currentTextChanged.connect(self.refresh_holdings_view)
        controls_layout.addWidget(self.holdings_level_combo)
        
        controls_layout.addSpacing(30)
        
        # Date selector
        date_label = QLabel("As of Date:")
        date_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(date_label)
        
        self.holdings_date_combo = QComboBox()
        self.holdings_date_combo.currentTextChanged.connect(self.refresh_holdings_view)
        controls_layout.addWidget(self.holdings_date_combo)
        
        controls_layout.addSpacing(20)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_holdings_view)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        
        holdings_layout.addWidget(controls_frame)
        
        # Create holdings table
        self.holdings_table = CustomTableWidget()
        holdings_layout.addWidget(self.holdings_table)
        
        self.tab_widget.addTab(holdings_widget, "💼 Current Holdings")
    
    def load_initial_data(self):
        """Load initial sample data"""
        try:
            self.data = load_sample_data()
            self.process_data()
            self.update_date_selector()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load initial data: {str(e)}")
    
    def process_data(self):
        """Process the loaded data"""
        if self.data is None:
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.showMessage("Processing data...")
        
        # Create and start processing thread
        self.processor_thread = DataProcessorThread(self.data, self.processor)
        self.processor_thread.finished.connect(self.on_data_processed)
        self.processor_thread.error.connect(self.on_processing_error)
        self.processor_thread.start()
    
    def on_data_processed(self, processed_data):
        """Handle processed data"""
        self.processed_data = processed_data
        self.populate_activity_table()
        self.update_date_selector()  # Ensure date selector is populated after data is processed
        self.refresh_holdings_view()
        
        # Hide progress
        self.progress_bar.setVisible(False)
        if self.data is not None:
            self.status_bar.showMessage(f"Loaded {len(self.data)} transactions")
        else:
            self.status_bar.showMessage("Data loaded")
    
    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Processing Error", f"Failed to process data: {error_msg}")
    
    def populate_activity_table(self):
        """Populate the activity table with processed data"""
        if self.processed_data is None:
            return
        
        # Build column order and headers
        columns = []
        col_headers = []
        column_colors = []
        
        # Include original transaction columns first
        main_cols = [c for c in self.processed_data.columns if get_column_level(c) is None]
        for col in main_cols:
            columns.append(col)
            col_headers.append(col)
            column_colors.append(QColor(255, 255, 255))  # White for main columns
        
        # Add calculated columns grouped by level
        for group in COLUMN_GROUPS:
            for field in group["fields"]:
                col = f"{field} ({group['section']})"
                columns.append(col)
                
                # Create multi-line header
                if len(field) > 10:
                    words = field.split(' ')
                    if len(words) > 1:
                        if len(words) >= 3:
                            mid = len(words) // 2
                            header = f"{' '.join(words[:mid])}\n{' '.join(words[mid:])}\n({group['section']})"
                        else:
                            header = f"{words[0]}\n{words[1]}\n({group['section']})"
                    else:
                        if len(field) > 15:
                            mid = len(field) // 2
                            header = f"{field[:mid]}\n{field[mid:]}\n({group['section']})"
                        else:
                            header = f"{field}\n({group['section']})"
                else:
                    header = f"{field}\n({group['section']})"
                
                col_headers.append(header)
                column_colors.append(group["color"])
        
        # Set up table
        self.activity_table.setColumnCount(len(columns))
        self.activity_table.setHorizontalHeaderLabels(col_headers)
        
        # Set column widths
        for i, col in enumerate(columns):
            if "Security" in col or "Description" in col:
                width = 160
            elif "Parent company" in col or "Legal entity" in col:
                width = 200
            elif any(keyword in col for keyword in ['Cost', 'Price', 'Total', 'Rate', 'Gain/Loss']):
                width = 170
            else:
                width = 140
            self.activity_table.setColumnWidth(i, width)
        
        # Set header colors
        self.activity_table.set_header_colors(column_colors)
        
        # Format and populate data
        display_data = self.processed_data.copy()
        for col in display_data.columns:
            if display_data[col].dtype in ["float64", "int64"]:
                display_data[col] = display_data[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) and x != '' else '0.00'
                )
            elif 'Realized Gain/Loss' in col:
                def format_rgl(value):
                    if pd.isna(value) or value == '' or value == 0:
                        return ''
                    try:
                        return f"{float(value):,.2f}"
                    except (ValueError, TypeError):
                        return ''
                display_data[col] = display_data[col].apply(format_rgl)
        
        # Populate table
        self.activity_table.setRowCount(len(display_data))
        for row_idx, (_, row_data) in enumerate(display_data[columns].iterrows()):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                
                # Set alignment
                if any(keyword in columns[col_idx] for keyword in ['Cost', 'Quantity', 'Price', 'Total', 'Gain/Loss', 'WAC']):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                self.activity_table.setItem(row_idx, col_idx, item)
    
    def update_date_selector(self):
        """Update the date selector with available dates"""
        if self.processed_data is None:
            return
        
        available_dates = sorted(pd.to_datetime(self.processed_data['Trade date']).dt.date.unique())
        latest_date = max(available_dates) if available_dates else None
        
        self.holdings_date_combo.clear()
        self.holdings_date_combo.addItems([str(d) for d in available_dates])
        
        if latest_date:
            self.holdings_date_combo.setCurrentText(str(latest_date))
    
    def refresh_holdings_view(self):
        """Refresh the holdings view"""
        if self.processed_data is None:
            return
        
        selected_level = self.holdings_level_combo.currentText()
        selected_date = self.holdings_date_combo.currentText()
        
        if not selected_date:
            return
        
        # Get holdings data
        holdings_data = self.processor.get_holdings_snapshot(
            self.processed_data, selected_date, selected_level
        )
        
        if holdings_data.empty:
            self.holdings_table.setRowCount(0)
            self.holdings_table.setColumnCount(0)
            return
        
        # Define columns based on level - Focus on core holdings metrics
        if selected_level == "Portfolio":
            holdings_cols = ['Portfolio', 'Security', 'Current Quantity', 'Current Cost USD', 'WAC per Unit USD', 'Current Cost CCY', 'WAC per Unit CCY']
        elif selected_level == "Parent company":
            holdings_cols = ['Portfolio', 'Parent company', 'Security', 'Current Quantity', 'Current Cost USD', 'WAC per Unit USD', 'Current Cost CCY', 'WAC per Unit CCY']
        elif selected_level == "Legal entity":
            holdings_cols = ['Portfolio', 'Parent company', 'Legal entity', 'Security', 'Current Quantity', 'Current Cost USD', 'WAC per Unit USD', 'Current Cost CCY', 'WAC per Unit CCY']
        elif selected_level == "Account":
            holdings_cols = ['Portfolio', 'Parent company', 'Legal entity', 'Custodian', 'Account', 'Security', 'Current Quantity', 'Current Cost USD', 'WAC per Unit USD', 'Current Cost CCY', 'WAC per Unit CCY']
        else:
            holdings_cols = ['Security', 'Current Quantity', 'Current Cost USD', 'WAC per Unit USD', 'Current Cost CCY', 'WAC per Unit CCY']
        
        # Filter to available columns
        available_cols = [col for col in holdings_cols if col in holdings_data.columns]
        holdings_data = holdings_data[available_cols]
        
        # Format numeric columns
        for col in holdings_data.columns:
            if any(keyword in col for keyword in ['Quantity', 'Cost', 'WAC', 'Value']):
                holdings_data[col] = holdings_data[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else '0.00'
                )
        
        # Set up holdings table
        self.holdings_table.setColumnCount(len(available_cols))
        self.holdings_table.setHorizontalHeaderLabels(available_cols)
        
        # Set column widths
        for i, col in enumerate(available_cols):
            if col in ['Portfolio', 'Parent company', 'Legal entity']:
                width = 200
            elif col == 'Security':
                width = 180
            elif any(keyword in col for keyword in ['Cost USD', 'WAC USD']):
                width = 150
            elif any(keyword in col for keyword in ['Cost CCY', 'WAC CCY']):
                width = 140
            elif col == 'Current Quantity':
                width = 130
            else:
                width = 120
            self.holdings_table.setColumnWidth(i, width)
        
        # Set header color (green for holdings)
        header_colors = [QColor(39, 174, 96)] * len(available_cols)  # Green
        self.holdings_table.set_header_colors(header_colors)
        
        # Populate table
        self.holdings_table.setRowCount(len(holdings_data))
        for row_idx, (_, row_data) in enumerate(holdings_data.iterrows()):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                
                # Set alignment
                if any(keyword in available_cols[col_idx] for keyword in ['Quantity', 'Cost', 'WAC']):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                self.holdings_table.setItem(row_idx, col_idx, item)
    
    def load_file(self):
        """Load Excel file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel files (*.xlsx *.xls);;All files (*.*)"
        )
        
        if file_path:
            try:
                self.data = pd.read_excel(file_path)
                
                # Validate data
                is_valid, errors = self.processor.validate_data(self.data)
                if not is_valid:
                    QMessageBox.critical(self, "Data Validation Error", 
                                       "Data validation failed:\n" + "\n".join(errors))
                    return
                
                self.process_data()
                self.update_date_selector()
                QMessageBox.information(self, "Success", f"Loaded {len(self.data)} transactions")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def export_to_excel(self):
        """Export data to Excel"""
        if self.processed_data is None:
            QMessageBox.warning(self, "Warning", "No data to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel File", "Processed_Transactions.xlsx", 
            "Excel files (*.xlsx);;All files (*.*)"
        )
        
        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    self.processed_data.to_excel(writer, sheet_name='Activity', index=False)
                    
                    # Apply formatting
                    self.apply_excel_formatting(writer.book, writer.sheets['Activity'])
                
                QMessageBox.information(self, "Success", f"Data exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
    
    def apply_excel_formatting(self, workbook, worksheet):
        """Apply formatting to Excel worksheet"""
        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Apply header formatting
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Set header row height
        worksheet.row_dimensions[1].height = 60
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = PortfolioReportingApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 