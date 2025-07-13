import pandas as pd
from transaction_processor import TransactionProcessor

def test_processor():
    """Test the transaction processor with the provided Excel file"""
    
    # Load the test data
    print("Loading test data...")
    df = pd.read_excel('Test_transactions.xlsx')
    print(f"Loaded {len(df)} transactions")
    print(f"Columns: {list(df.columns)}")
    
    # Show sample data
    print("\nSample data:")
    print(df.head())
    
    # Initialize processor
    processor = TransactionProcessor()
    
    # Process transactions
    print("\nProcessing transactions...")
    processed_df = processor.process_transactions(df)
    
    # Show results
    print(f"\nProcessed {len(processed_df)} transactions")
    print(f"New columns added: {[col for col in processed_df.columns if col not in df.columns]}")
    
    # Show sample processed data
    print("\nSample processed data:")
    sample_cols = ['Portfolio', 'Security', 'B/S', 'Quantity', 'Total USD', 
                   'Transaction Cost (Portfolio) USD', 'Realized P&L (Portfolio) USD']
    print(processed_df[sample_cols].head())
    
    # Get holdings snapshot
    print("\nHoldings snapshot:")
    holdings_df = processor.get_holdings_snapshot(processed_df)
    if not holdings_df.empty:
        print(holdings_df)
    else:
        print("No holdings found")
    
    # Save processed data
    print("\nSaving processed data...")
    with pd.ExcelWriter('Processed_Transactions.xlsx', engine='openpyxl') as writer:
        processed_df.to_excel(writer, sheet_name='Activity', index=False)
        if not holdings_df.empty:
            holdings_df.to_excel(writer, sheet_name='Holdings', index=False)
    
    print("Test completed! Check 'Processed_Transactions.xlsx' for results.")

if __name__ == "__main__":
    test_processor() 