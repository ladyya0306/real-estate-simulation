
"""
Financial Calculator Service
Provides investment metrics for Agent decision making.
"""
from typing import Dict, Optional

class FinancialCalculator:
    
    @staticmethod
    def calculate_rental_yield(property_price: float, monthly_rental_income: float) -> float:
        """
        Calculate Annual Rental Yield.
        Formula: (Monthly Rent * 12) / Property Price
        """
        if property_price <= 0:
            return 0.0
        return (monthly_rental_income * 12) / property_price

    @staticmethod
    def calculate_holding_cost(agent, property_data: Dict, mortgage_payment: float = 0) -> float:
        """
        Calculate Monthly Holding Cost.
        Formula: Mortgage + Maintenance - Rent (if rented out)
        Note: If property is vacant, Rent is 0.
        """
        maintenance_cost = property_data.get('base_value', 0) * 0.0003 # Approx 0.3% monthly maintenance/tax
        monthly_rent = property_data.get('rental_income', 0)
        
        # If agent lives in it, no rent income, but implicit benefit? 
        # For simplicity, if 'status' is 'for_rent', deduct rent.
        if property_data.get('status') == 'for_rent':
            pass
        else:
            monthly_rent = 0
            
        return mortgage_payment + maintenance_cost - monthly_rent

    @staticmethod
    def calculate_potential_roi(
        down_payment: float, 
        monthly_cash_flow: float, 
        appreciation_rate: float, 
        property_value: float,
        years: int = 1
    ) -> float:
        """
        Calculate Return on Investment (ROI) Projection.
        Includes Cash Flow + Appreciation.
        """
        if down_payment <= 0:
            return 0.0
            
        annual_cash_flow = monthly_cash_flow * 12
        appreciation_gain = property_value * ((1 + appreciation_rate) ** years - 1)
        
        total_gain = (annual_cash_flow * years) + appreciation_gain
        return total_gain / down_payment

    @staticmethod
    def compare_with_risk_free(yield_rate: float, risk_free_rate: float) -> str:
        """
        Return a textual comparison signal.
        """
        diff = yield_rate - risk_free_rate
        if diff > 0.02:
            return "EXCELLENT (远超存款)"
        elif diff > 0:
            return "GOOD (略高于存款)"
        elif diff > -0.01:
            return "FAIR (不如存款，但可博增值)"
        else:
            return "POOR (严重亏损)"
