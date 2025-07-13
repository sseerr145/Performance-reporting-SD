# Portfolio Reporting Tool - Weighted Average Cost Basis

A desktop application for processing security transactions and calculating holdings and realized P&L using the Weighted Average Cost (WAC) method with multi-level consolidation support.

## Features

- **Multi-Level Consolidation**: Supports Portfolio, Parent company, Legal entity, and Account level calculations
- **WAC Calculations**: Automatically calculates weighted average cost basis for buy/sell transactions
- **Realized P&L Tracking**: Tracks realized gains/losses for sell transactions
- **Excel Import/Export**: Load transaction data from Excel and export processed results
- **Activity View**: Complete transaction history with calculated fields
- **Holdings Snapshot**: Current position holdings across all consolidation levels

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
3. Click "Process Transactions" to calculate WAC and P&L
4. View results in the Activity and Holdings tabs
5. Export processed data to Excel using "Export to Excel"

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
- `portfolio_app.py`: Desktop GUI application
- Modular design for easy extension with additional features 