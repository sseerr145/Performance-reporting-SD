# Portfolio Reporting Tool - PyQt5 Version

A modern desktop application for processing security transactions and calculating holdings and realized P&L using the Weighted Average Cost (WAC) method with multi-level consolidation support.

## Features

- **Modern PyQt5 Interface**: Clean, professional UI with full control over table formatting
- **Multi-Level Consolidation**: Supports All, Portfolio, Parent company, and Legal entity level calculations
- **WAC Calculations**: Automatically calculates weighted average cost basis for buy/sell transactions
- **Realized P&L Tracking**: Tracks realized gains/losses for sell transactions
- **Excel Import/Export**: Load transaction data from Excel and export processed results with formatting
- **Activity View**: Complete transaction history with calculated fields and color-coded headers
- **Holdings Snapshot**: Current position holdings across all consolidation levels
- **Full Table Control**: Easy header height adjustment, column formatting, and styling

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python portfolio_app.py
```

2. Load your Excel transaction file using the "Load Excel File" button
3. View results in the Activity and Holdings tabs
4. Export processed data to Excel using "Export to Excel"

## Data Format

Your Excel file should contain the following columns:
- Portfolio
- Parent company  
- Legal entity
- Custodian
- Account
- Security
- Currency
- B/S (Buy/Sell indicator)
- Trade ID
- Trade date
- Settle date
- Quantity
- Price
- FX rate
- Total (Original CCY)
- Total USD

## Output Columns

For each consolidation level, the tool calculates:
- Transaction Cost (CCY and USD)
- Cumulative Quantity
- Cumulative Cost (CCY and USD)
- Cost per Unit (CCY and USD)
- Realized P&L (CCY and USD)

## Architecture

- `transaction_processor.py`: Core WAC calculation engine
- `portfolio_app.py`: PyQt5 desktop GUI application
- Modular design for easy extension with additional features

## Advantages of PyQt5 Version

- **Full Table Control**: Easy header height adjustment and column formatting
- **Modern UI**: Professional appearance with native look and feel
- **Better Performance**: More efficient than Tkinter for large datasets
- **Rich Styling**: Comprehensive styling options for tables and widgets
- **Cross-Platform**: Consistent appearance across Windows, macOS, and Linux

## Sample Data

The application includes sample transaction data in `Test_transactions.xlsx` for testing and demonstration purposes. 