import pandas as pd
from collections import defaultdict
from typing import Dict, Any, List, Tuple

class TransactionProcessor:
    """Process security transactions and calculate WAC basis with multi-level consolidation"""
    
    def __init__(self):
        # Define consolidation levels and their grouping keys
        self.levels = ["Portfolio", "Parent company", "Legal entity", "Account"]
        self.group_keys = {
            "Portfolio": ["Portfolio"],
            "Parent company": ["Portfolio", "Parent company"],
            "Legal entity": ["Portfolio", "Parent company", "Legal entity"],
            "Account": ["Portfolio", "Parent company", "Legal entity", "Custodian", "Account"]
        }
        
        # Required columns for processing
        self.required_columns = [
            'Portfolio', 'Parent company', 'Legal entity', 'Custodian', 'Account',
            'Security', 'Currency', 'B/S', 'Trade ID', 'Trade date', 'Settle date',
            'Quantity', 'Price', 'FX rate', 'Total (Original CCY)', 'Total USD'
        ]
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate input data has required columns and proper format"""
        errors = []
        
        # Check for required columns
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Check data types for numeric columns
        numeric_cols = ['Quantity', 'Price', 'FX rate', 'Total (Original CCY)', 'Total USD']
        for col in numeric_cols:
            if col in df.columns:
                try:
                    pd.to_numeric(df[col], errors='coerce')
                except:
                    errors.append(f"Column '{col}' contains non-numeric values")
        
        # Check date columns
        date_cols = ['Trade date', 'Settle date']
        for col in date_cols:
            if col in df.columns:
                try:
                    pd.to_datetime(df[col], errors='coerce')
                except:
                    errors.append(f"Column '{col}' contains invalid date values")
        
        return len(errors) == 0, errors
    
    def process_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process transactions and calculate WAC basis for all consolidation levels"""
        # Make a copy to avoid modifying original data
        df = df.copy()
        
        # Ensure date columns are datetime
        df['Trade date'] = pd.to_datetime(df['Trade date'])
        df['Settle date'] = pd.to_datetime(df['Settle date'])
        
        # Ensure numeric columns are numeric
        numeric_cols = ['Quantity', 'Price', 'FX rate', 'Total (Original CCY)', 'Total USD']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Define the order of calculated columns for each level
        level_col_order = [
            'Transaction Cost USD', 'Transaction Cost CCY', 'Cumulative Quantity',
            'Cumulative Cost CCY', 'Cumulative Cost USD', 'Cost per Unit USD',
            'Cost per Unit CCY', 'Realized Gain/Loss CCY', 'Realized Gain/Loss USD'
        ]
        
        # Initialize calculated columns for each level
        for level in self.levels:
            for base in level_col_order:
                col = f'{base} ({level})'
                if 'Realized Gain/Loss' in base:
                    df[col] = 0.0  # Initialize as 0.0 instead of empty string
                else:
                    df[col] = 0.0
        
        # Process each consolidation level
        for level in self.levels:
            self._process_level(df, level)
        
        return df
    
    def _process_level(self, df: pd.DataFrame, level: str):
        """Process all transactions for a specific consolidation level"""
        # Initialize state tracking for each security within each group
        state: Dict[Any, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {
            'cumulative_qty': 0.0,
            'cumulative_cost_ccy': 0.0,
            'cumulative_cost_usd': 0.0,
            'wac_per_unit_ccy': 0.0,
            'wac_per_unit_usd': 0.0
        }))
        
        group_cols = self.group_keys[level] + ['Security']  # Group by consolidation level + Security
        
        # Sort by trade date to ensure chronological processing
        df_sorted = df.sort_values(['Trade date', 'Trade ID']).copy()
        
        # Process each transaction
        for idx in df_sorted.index:
            row = df_sorted.loc[idx]
            
            # Create group key for this consolidation level
            if level == "Portfolio":
                group_key = row['Portfolio']
            elif level == "Parent company":
                group_key = (row['Portfolio'], row['Parent company'])
            elif level == "Legal entity":
                group_key = (row['Portfolio'], row['Parent company'], row['Legal entity'])
            elif level == "Account":
                group_key = (row['Portfolio'], row['Parent company'], row['Legal entity'], 
                           row['Custodian'], row['Account'])
            
            security = row['Security']
            
            # Process this transaction
            self._process_single_transaction(df, idx, level, state[group_key][security], row)
    
    def _process_single_transaction(self, df: pd.DataFrame, idx: int, level: str, 
                                  security_state: Dict[str, float], row: pd.Series):
        """Process a single transaction and update the security state"""
        try:
            # Extract transaction details
            qty = float(row['Quantity'])
            price = float(row['Price'])
            fx_rate = float(row['FX rate'])
            total_ccy = float(row['Total (Original CCY)'])
            total_usd = float(row['Total USD'])
            is_buy = str(row['B/S']).strip().upper().startswith('B')
            
            # ACCOUNTING PRINCIPLE: Transaction costs and quantities must have consistent signs
            # Buys: positive quantity, positive cost
            # Sells: negative quantity, negative cost (cost basis release)
            
            if is_buy:
                # BUY TRANSACTION
                transaction_cost_ccy = abs(total_ccy)  # Cost paid (positive)
                transaction_cost_usd = abs(total_usd)  # Cost paid (positive)
                transaction_qty = abs(qty)  # Shares acquired (positive)
                
                # Update cumulative position
                new_cumulative_qty = security_state['cumulative_qty'] + transaction_qty
                new_cumulative_cost_ccy = security_state['cumulative_cost_ccy'] + transaction_cost_ccy
                new_cumulative_cost_usd = security_state['cumulative_cost_usd'] + transaction_cost_usd
                
                # Calculate new WAC (only changes on buys)
                if new_cumulative_qty > 0:
                    new_wac_ccy = new_cumulative_cost_ccy / new_cumulative_qty
                    new_wac_usd = new_cumulative_cost_usd / new_cumulative_qty
                else:
                    new_wac_ccy = 0.0
                    new_wac_usd = 0.0
                
                # No realized P&L on buys
                realized_pnl_ccy = 0.0
                realized_pnl_usd = 0.0
                
            else:
                # SELL TRANSACTION
                transaction_qty = -abs(qty)  # Shares sold (negative)
                
                # CRITICAL: Use CURRENT WAC before this transaction for cost basis release
                current_wac_ccy = security_state['wac_per_unit_ccy']
                current_wac_usd = security_state['wac_per_unit_usd']
                
                # Transaction cost = cost basis being released (negative to show release)
                transaction_cost_ccy = current_wac_ccy * transaction_qty  # Negative (cost released)
                transaction_cost_usd = current_wac_usd * transaction_qty  # Negative (cost released)
                
                # Calculate realized P&L
                # P&L = Proceeds - Cost Basis Released
                sale_proceeds_ccy = price * abs(qty)  # What we received
                sale_proceeds_usd = price * fx_rate * abs(qty)  # What we received in USD
                cost_basis_released_ccy = current_wac_ccy * abs(qty)  # Cost basis of shares sold
                cost_basis_released_usd = current_wac_usd * abs(qty)  # Cost basis of shares sold
                
                realized_pnl_ccy = sale_proceeds_ccy - cost_basis_released_ccy
                realized_pnl_usd = sale_proceeds_usd - cost_basis_released_usd
                
                # Update cumulative position
                new_cumulative_qty = security_state['cumulative_qty'] + transaction_qty
                new_cumulative_cost_ccy = security_state['cumulative_cost_ccy'] + transaction_cost_ccy
                new_cumulative_cost_usd = security_state['cumulative_cost_usd'] + transaction_cost_usd
                
                # CRITICAL: WAC per unit does NOT change on sells, only the cumulative amounts change
                if new_cumulative_qty > 0:
                    # Position still exists, WAC remains the same
                    new_wac_ccy = current_wac_ccy
                    new_wac_usd = current_wac_usd
                elif new_cumulative_qty == 0:
                    # Position fully closed
                    new_wac_ccy = 0.0
                    new_wac_usd = 0.0
                    new_cumulative_cost_ccy = 0.0  # Ensure no rounding errors
                    new_cumulative_cost_usd = 0.0
                else:
                    # Short position - this shouldn't happen with WAC but handle gracefully
                    print(f"Warning: Short position detected at row {idx}")
                    new_wac_ccy = current_wac_ccy
                    new_wac_usd = current_wac_usd
            
            # Update the dataframe with calculated values
            df.at[idx, f'Transaction Cost USD ({level})'] = transaction_cost_usd
            df.at[idx, f'Transaction Cost CCY ({level})'] = transaction_cost_ccy
            df.at[idx, f'Cumulative Quantity ({level})'] = new_cumulative_qty
            df.at[idx, f'Cumulative Cost CCY ({level})'] = new_cumulative_cost_ccy
            df.at[idx, f'Cumulative Cost USD ({level})'] = new_cumulative_cost_usd
            df.at[idx, f'Cost per Unit USD ({level})'] = new_wac_usd
            df.at[idx, f'Cost per Unit CCY ({level})'] = new_wac_ccy
            df.at[idx, f'Realized Gain/Loss CCY ({level})'] = realized_pnl_ccy
            df.at[idx, f'Realized Gain/Loss USD ({level})'] = realized_pnl_usd
            
            # Update the security state for next transaction
            security_state['cumulative_qty'] = new_cumulative_qty
            security_state['cumulative_cost_ccy'] = new_cumulative_cost_ccy
            security_state['cumulative_cost_usd'] = new_cumulative_cost_usd
            security_state['wac_per_unit_ccy'] = new_wac_ccy
            security_state['wac_per_unit_usd'] = new_wac_usd
            
        except Exception as e:
            print(f"Error processing transaction at row {idx} for level {level}: {e}")
            # Set default values to prevent cascade errors
            df.at[idx, f'Transaction Cost USD ({level})'] = 0.0
            df.at[idx, f'Transaction Cost CCY ({level})'] = 0.0
            df.at[idx, f'Cumulative Quantity ({level})'] = security_state['cumulative_qty']
            df.at[idx, f'Cumulative Cost CCY ({level})'] = security_state['cumulative_cost_ccy']
            df.at[idx, f'Cumulative Cost USD ({level})'] = security_state['cumulative_cost_usd']
            df.at[idx, f'Cost per Unit USD ({level})'] = security_state['wac_per_unit_usd']
            df.at[idx, f'Cost per Unit CCY ({level})'] = security_state['wac_per_unit_ccy']
            df.at[idx, f'Realized Gain/Loss CCY ({level})'] = 0.0
            df.at[idx, f'Realized Gain/Loss USD ({level})'] = 0.0
    
    def get_holdings_snapshot(self, df: pd.DataFrame, as_of_date: str = None, level: str = "Portfolio") -> pd.DataFrame:
        """Get holdings snapshot for a specific date and consolidation level"""
        if as_of_date:
            # Filter transactions up to and including the specified date
            as_of_date = pd.to_datetime(as_of_date)
            filtered_df = df[df['Trade date'] <= as_of_date].copy()
        else:
            # Use all transactions
            filtered_df = df.copy()
        
        if filtered_df.empty:
            return pd.DataFrame()
        
        holdings_data = []
        group_cols = self.group_keys[level] + ['Security']
        
        # Group by the consolidation keys plus security
        grouped = filtered_df.groupby(group_cols, sort=False)
        
        # For each group, get the last transaction's cumulative values
        for group_key, group_df in grouped:
            # Sort by date and get the last row for this security group
            last_row = group_df.sort_values(['Trade date', 'Trade ID']).iloc[-1]
            
            qty_col = f'Cumulative Quantity ({level})'
            cost_usd_col = f'Cumulative Cost USD ({level})'
            cost_ccy_col = f'Cumulative Cost CCY ({level})'
            wac_usd_col = f'Cost per Unit USD ({level})'
            wac_ccy_col = f'Cost per Unit CCY ({level})'
            
            # Only include positions with non-zero quantity
            current_qty = last_row[qty_col]
            if abs(current_qty) > 0.001:  # Use small threshold to handle rounding
                holding_record = {}
                
                # Add grouping fields
                if level == "Portfolio":
                    holding_record['Portfolio'] = last_row['Portfolio']
                elif level == "Parent company":
                    holding_record['Portfolio'] = last_row['Portfolio']
                    holding_record['Parent company'] = last_row['Parent company']
                elif level == "Legal entity":
                    holding_record['Portfolio'] = last_row['Portfolio']
                    holding_record['Parent company'] = last_row['Parent company']
                    holding_record['Legal entity'] = last_row['Legal entity']
                elif level == "Account":
                    holding_record['Portfolio'] = last_row['Portfolio']
                    holding_record['Parent company'] = last_row['Parent company']
                    holding_record['Legal entity'] = last_row['Legal entity']
                    holding_record['Custodian'] = last_row['Custodian']
                    holding_record['Account'] = last_row['Account']
                
                # Add position details
                holding_record.update({
                    'Security': last_row['Security'],
                    'Currency': last_row['Currency'],
                    'Current Quantity': current_qty,
                    'Current Cost USD': last_row[cost_usd_col],
                    'Current Cost CCY': last_row[cost_ccy_col],
                    'WAC per Unit USD': last_row[wac_usd_col],
                    'WAC per Unit CCY': last_row[wac_ccy_col],
                    'Last Trade Date': last_row['Trade date']
                })
                
                holdings_data.append(holding_record)
        
        holdings_df = pd.DataFrame(holdings_data)
        
        # Sort by portfolio, then security for better readability
        if not holdings_df.empty:
            sort_cols = ['Portfolio']
            if level in ["Parent company", "Legal entity", "Account"]:
                sort_cols.append('Parent company')
            if level in ["Legal entity", "Account"]:
                sort_cols.append('Legal entity')
            if level == "Account":
                sort_cols.extend(['Custodian', 'Account'])
            sort_cols.append('Security')
            
            holdings_df = holdings_df.sort_values(sort_cols).reset_index(drop=True)
        
        return holdings_df 