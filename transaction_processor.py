import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CumulativeState:
    """Represents the cumulative state for a specific group"""
    quantity: float = 0.0
    cost_ccy: float = 0.0
    cost_usd: float = 0.0
    wac_ccy: float = 0.0
    wac_usd: float = 0.0


class TransactionProcessor:
    """Processes transactions and calculates WAC-based holdings and P&L"""
    
    def __init__(self):
        # Only Portfolio, Parent company, Account
        self.levels = ['Portfolio', 'Parent company', 'Account']
        self.group_keys = {
            'Portfolio': ['Portfolio', 'Security'],
            'Parent company': ['Parent company', 'Security'],
            'Account': ['Account', 'Security']
        }

    def process_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        # Always sort by all possible group keys and Trade date for correct WAC/cumulative logic
        df = df.copy()
        sort_cols = list({col for keys in self.group_keys.values() for col in keys}) + ['Trade date']
        df = df.sort_values(sort_cols).reset_index(drop=True)

        # Define the order of columns for each level
        level_col_order = [
            'Transaction Cost USD', 'Transaction Cost CCY',
            'Cumulative Quantity', 'Cumulative Cost CCY', 'Cumulative Cost USD',
            'Cost per Unit USD', 'Cost per Unit CCY',
            'Realized Gain/Loss CCY', 'Realized Gain/Loss USD'
        ]

        # Prepare output columns for each level in the correct order
        for level in self.levels:
            for base in level_col_order:
                col = f'{base} ({level})'
                if 'Realized Gain/Loss' in base:
                    df[col] = ''
                else:
                    df[col] = 0.0

        for level in self.levels:
            state: Dict[Any, Dict[str, float]] = defaultdict(lambda: {
                'qty': 0.0,
                'cost_ccy': 0.0,
                'cost_usd': 0.0,
                'wac_ccy': 0.0,
                'wac_usd': 0.0
            })
            group_cols = self.group_keys[level]
            grouped = df.groupby(group_cols, sort=False)
            for group, group_df in grouped:
                group_indices = group_df.sort_values('Trade date').index.tolist()
                for idx in group_indices:
                    row = df.loc[idx]
                    qty = float(row['Quantity'])
                    price = float(row['Price'])
                    fx = float(row['FX rate'])
                    total_ccy = float(row['Total (Original CCY)'])
                    total_usd = float(row['Total USD'])
                    is_buy = str(row['B/S']).strip().upper().startswith('B')

                    # Always use current WAC before the transaction for sells
                    wac_ccy_before = state[group]['wac_ccy']
                    wac_usd_before = state[group]['wac_usd']

                    df.at[idx, f'Transaction Cost USD ({level})'] = total_usd
                    df.at[idx, f'Transaction Cost CCY ({level})'] = total_ccy

                    if is_buy:
                        state[group]['qty'] += qty
                        state[group]['cost_ccy'] += total_ccy
                        state[group]['cost_usd'] += total_usd
                        if state[group]['qty'] != 0:
                            state[group]['wac_ccy'] = state[group]['cost_ccy'] / state[group]['qty']
                            state[group]['wac_usd'] = state[group]['cost_usd'] / state[group]['qty']
                        else:
                            state[group]['wac_ccy'] = 0.0
                            state[group]['wac_usd'] = 0.0
                        df.at[idx, f'Realized Gain/Loss CCY ({level})'] = ''
                        df.at[idx, f'Realized Gain/Loss USD ({level})'] = ''
                    else:
                        released_cost_ccy = abs(qty) * wac_ccy_before
                        released_cost_usd = abs(qty) * wac_usd_before
                        proceeds_ccy = abs(qty) * price
                        proceeds_usd = abs(qty) * price * fx
                        rgl_ccy = proceeds_ccy - released_cost_ccy
                        rgl_usd = proceeds_usd - released_cost_usd
                        state[group]['qty'] += qty
                        state[group]['cost_ccy'] -= released_cost_ccy
                        state[group]['cost_usd'] -= released_cost_usd
                        if state[group]['qty'] != 0:
                            state[group]['wac_ccy'] = state[group]['cost_ccy'] / state[group]['qty']
                            state[group]['wac_usd'] = state[group]['cost_usd'] / state[group]['qty']
                        else:
                            state[group]['wac_ccy'] = 0.0
                            state[group]['wac_usd'] = 0.0
                        df.at[idx, f'Realized Gain/Loss CCY ({level})'] = round(rgl_ccy, 8)
                        df.at[idx, f'Realized Gain/Loss USD ({level})'] = round(rgl_usd, 8)

                    df.at[idx, f'Cumulative Quantity ({level})'] = state[group]['qty']
                    df.at[idx, f'Cumulative Cost CCY ({level})'] = state[group]['cost_ccy']
                    df.at[idx, f'Cumulative Cost USD ({level})'] = state[group]['cost_usd']
                    df.at[idx, f'Cost per Unit CCY ({level})'] = state[group]['wac_ccy']
                    df.at[idx, f'Cost per Unit USD ({level})'] = state[group]['wac_usd']

        for col in df.columns:
            if df[col].dtype == float:
                df[col] = df[col].fillna(0.0)
            elif df[col].dtype == object:
                df[col] = df[col].fillna('')
        return df
    
    def get_holdings_snapshot(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame([]) 