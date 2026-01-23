"""
Mortgage System: Loan Calculation and Affordability Check
"""
import math
from typing import Dict, Tuple
from config.settings import MORTGAGE_CONFIG

def calculate_monthly_payment(loan_amount: float, annual_rate: float, years: int) -> float:
    """
    Calculate monthly mortgage payment using standard formula.
    M = P [ i(1 + i)^n ] / [ (1 + i)^n – 1 ]
    """
    if loan_amount <= 0:
        return 0.0
    
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    if monthly_rate == 0:
        return loan_amount / num_payments
        
    payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    return payment

def check_affordability(agent, price: float) -> Tuple[bool, float, float]:
    """
    Check if agent can afford the property with mortgage.
    Returns: (is_affordable, down_payment, loan_amount)
    """
    # 1. Down Payment Check
    min_down_payment = price * MORTGAGE_CONFIG["down_payment_ratio"]
    if agent.cash < min_down_payment:
        return False, 0.0, 0.0
        
    # 2. Loan Amount Needed
    loan_amount = price - agent.cash # Try to pay as much cash as possible? Or just min down payment?
    
    # Normally buyers pay min down payment to leverage, or some optimizing strategy.
    # For now, let's assume they pay min down payment + any excess cash above a safety buffer?
    # Simple strategy: Pay min down payment. Keep cash for safety.
    down_payment = min_down_payment
    loan_amount = price - down_payment
    
    # 3. DTI Check (Debt-to-Income)
    # Calculate new monthly payment
    new_monthly_payment = calculate_monthly_payment(
        loan_amount, 
        MORTGAGE_CONFIG["annual_interest_rate"], 
        MORTGAGE_CONFIG["loan_term_years"]
    )
    
    total_monthly_payment = agent.monthly_payment + new_monthly_payment
    max_payment = agent.monthly_income * MORTGAGE_CONFIG["max_dti_ratio"]
    
    if total_monthly_payment > max_payment:
        # Cannot afford monthly payment
        return False, 0.0, 0.0
        
    return True, down_payment, loan_amount

def get_max_loan(agent) -> float:
    """
    Calculate max loan amount agent can get based on income.
    """
    max_payment = agent.monthly_income * MORTGAGE_CONFIG["max_dti_ratio"]
    available_payment = max(0, max_payment - agent.monthly_payment)
    
    # Inverse of monthly payment formula to get Principal
    # P = M * [ (1 + i)^n - 1 ] / [ i(1 + i)^n ]
    
    annual_rate = MORTGAGE_CONFIG["annual_interest_rate"]
    years = MORTGAGE_CONFIG["loan_term_years"]
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    if monthly_rate == 0:
        return available_payment * num_payments
        
    max_loan = available_payment * ((1 + monthly_rate) ** num_payments - 1) / (monthly_rate * (1 + monthly_rate) ** num_payments)
    return max_loan
