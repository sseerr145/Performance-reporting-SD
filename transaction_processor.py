import pandas as pd
from collections import defaultdict
from typing import Dict, Any, List, Tuple

class TransactionProcessor:
    """Process security transactions and calculate WAC basis with multi-level consolidation"""
    
    def __init__(self):
        # Define consolidation levels and their grouping keys
        self.levels = ["All", "Portfolio", "Parent company", "Legal entity"]
        self.group_keys = {
            "All": [],
            "Portfolio": ["Portfolio"],
            "Parent company": ["Portfolio", "Parent company"],
            "Legal entity": ["Portfolio", "Parent company", "Legal entity"]
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
                    df[col] = ''
                else:
                    df[col] = 0.0
        
        # Process each consolidation level
        for level in self.levels:
            # Initialize state for each group
            state: Dict[Any, Dict[str, float]] = defaultdict(lambda: {
                'qty': 0.0,
                'cost_ccy': 0.0,
                'cost_usd': 0.0,
                'wac_ccy': 0.0,
                'wac_usd': 0.0
            })
            
            group_cols = self.group_keys[level]
            
            # Handle "All" level differently - no grouping needed
            if level == "All":
                # For "All" level, treat the entire dataset as one group
                group_indices = df.sort_values('Trade date').index.tolist()
                for idx in group_indices:
                    self._process_transaction(df, idx, level, state, "all")
            else:
                # For other levels, use grouping
                grouped = df.groupby(group_cols, sort=False)
                for group, group_df in grouped:
                    group_indices = group_df.sort_values('Trade date').index.tolist()
                    for idx in group_indices:
                        self._process_transaction(df, idx, level, state, group)
        
        return df
    
    def _process_transaction(self, df: pd.DataFrame, idx: int, level: str, state: Dict, group: Any):
        """Process a single transaction for a given level and group"""
        try:
            row = df.loc[idx]
            qty = float(row['Quantity'])
            price = float(row['Price'])
            fx = float(row['FX rate'])
            total_ccy = float(row['Total (Original CCY)'])
            total_usd = float(row['Total USD'])
            is_buy = str(row['B/S']).strip().upper().startswith('B')
            
            # For sells, make totals negative to match negative quantity
            if not is_buy:
                total_ccy = -total_ccy
                total_usd = -total_usd
                # Update the original dataframe columns for export
                df.at[idx, 'Total (Original CCY)'] = total_ccy
                df.at[idx, 'Total USD'] = total_usd
            
            # Always use current WAC before the transaction for sells
            wac_ccy_before = state[group]['wac_ccy']
            wac_usd_before = state[group]['wac_usd']
            
            if is_buy:
                # For buys: Transaction Cost = Total USD (actual cost paid)
                df.at[idx, f'Transaction Cost USD ({level})'] = total_usd
                df.at[idx, f'Transaction Cost CCY ({level})'] = total_ccy
                
                # Update cumulative quantities and costs
                state[group]['qty'] += qty
                state[group]['cost_ccy'] += total_ccy
                state[group]['cost_usd'] += total_usd
                
                # Calculate new WAC
                if state[group]['qty'] != 0:
                    state[group]['wac_ccy'] = state[group]['cost_ccy'] / state[group]['qty']
                    state[group]['wac_usd'] = state[group]['cost_usd'] / state[group]['qty']
                
            else:
                # For sells: Transaction Cost = negative WAC cost being released
                wac_cost_ccy = wac_ccy_before * abs(qty)
                wac_cost_usd = wac_usd_before * abs(qty)
                df.at[idx, f'Transaction Cost USD ({level})'] = -wac_cost_usd
                df.at[idx, f'Transaction Cost CCY ({level})'] = -wac_cost_ccy
                
                # Calculate realized P&L using WAC before the transaction
                realized_ccy = (price - wac_ccy_before) * abs(qty)
                realized_usd = (price * fx - wac_usd_before) * abs(qty)
                
                df.at[idx, f'Realized Gain/Loss CCY ({level})'] = realized_ccy
                df.at[idx, f'Realized Gain/Loss USD ({level})'] = realized_usd
                
                # Update cumulative quantities and costs
                state[group]['qty'] += qty  # qty is negative for sells
                if state[group]['qty'] != 0:
                    # Adjust cost basis proportionally
                    remaining_ratio = state[group]['qty'] / (state[group]['qty'] - qty)
                    state[group]['cost_ccy'] *= remaining_ratio
                    state[group]['cost_usd'] *= remaining_ratio
                    state[group]['wac_ccy'] = state[group]['cost_ccy'] / state[group]['qty']
                    state[group]['wac_usd'] = state[group]['cost_usd'] / state[group]['qty']
                else:
                    # Position closed, reset to zero
                    state[group]['cost_ccy'] = 0.0
                    state[group]['cost_usd'] = 0.0
                    state[group]['wac_ccy'] = 0.0
                    state[group]['wac_usd'] = 0.0
            
            # Update cumulative values in dataframe
            df.at[idx, f'Cumulative Quantity ({level})'] = state[group]['qty']
            df.at[idx, f'Cumulative Cost CCY ({level})'] = state[group]['cost_ccy']
            df.at[idx, f'Cumulative Cost USD ({level})'] = state[group]['cost_usd']
            df.at[idx, f'Cost per Unit USD ({level})'] = state[group]['wac_usd']
            df.at[idx, f'Cost per Unit CCY ({level})'] = state[group]['wac_ccy']
            
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
    
    def get_holdings_snapshot(self, df: pd.DataFrame, as_of_date: str, level: str) -> pd.DataFrame:
        """Get holdings snapshot for a specific date and consolidation level"""
        # Filter transactions up to and including the specified date
        as_of_date = pd.to_datetime(as_of_date)
        filtered_df = df[df['Trade date'] <= as_of_date].copy()
        
        if filtered_df.empty:
            return pd.DataFrame()
        
        holdings_data = []
        group_cols = self.group_keys[level]
        
        # Group by the consolidation keys
        groups = filtered_df.groupby(group_cols)
        
        # For each group, get the last transaction's cumulative values
        for group_key, group_df in groups:
            # Sort by date and get the last row
            last_row = group_df.sort_values('Trade date').iloc[-1]
            
            qty_col = f'Cumulative Quantity ({level})'
            cost_usd_col = f'Cumulative Cost USD ({level})'
            cost_ccy_col = f'Cumulative Cost CCY ({level})'
            wac_usd_col = f'Cost per Unit USD ({level})'
            wac_ccy_col = f'Cost per Unit CCY ({level})'
            
            # Only include positions with non-zero quantity
            if last_row[qty_col] != 0:
                holding_record = {}
                
                # Add level-specific field first
                if level == "Legal entity":
                    holding_record['Legal entity'] = last_row.get('Legal entity', '')
                elif level == "Portfolio":
                    holding_record['Portfolio'] = last_row.get('Portfolio', '')
                elif level == "Parent company":
                    holding_record['Parent company'] = last_row.get('Parent company', '')
                
                # Add common fields
                holding_record.update({
                    'Security': last_row['Security'],
                    'Current Quantity': last_row[qty_col],
                    'Current Cost USD': last_row[cost_usd_col],
                    'Current Cost CCY': last_row[cost_ccy_col],
                    'WAC USD': last_row[wac_usd_col],
                    'WAC CCY': last_row[wac_ccy_col],
                    'Market Value USD': last_row[qty_col] * last_row.get('Price', 0) * last_row.get('FX rate', 1)
                })
                
                holdings_data.append(holding_record)
        
        return pd.DataFrame(holdings_data) 