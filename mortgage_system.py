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

def check_affordability(agent, price: float, config=None) -> Tuple[bool, float, float]:
    """
    Check if agent can afford the property with mortgage.
    Returns: (is_affordable, down_payment, loan_amount)
    """
    # 0. Config Setup
    mortgage_cfg = config.mortgage if config else MORTGAGE_CONFIG
    down_ratio = mortgage_cfg.get('down_payment_ratio', 0.3)
    annual_rate = mortgage_cfg.get('annual_interest_rate', 0.05)
    loan_term = mortgage_cfg.get('loan_term_years', 30)
    max_dti = mortgage_cfg.get('max_dti_ratio', 0.5)

    # 1. Down Payment Check
    min_down_payment = price * down_ratio
    if agent.cash < min_down_payment:
        return False, 0.0, 0.0
        
    # 2. Loan Amount Needed
    down_payment = min_down_payment
    loan_amount = price - down_payment
    
    # 3. DTI Check (Debt-to-Income)
    # Calculate new monthly payment
    new_monthly_payment = calculate_monthly_payment(
        loan_amount, 
        annual_rate, 
        loan_term
    )
    
    total_monthly_payment = agent.monthly_payment + new_monthly_payment
    max_payment = agent.monthly_income * max_dti
    
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


def calculate_max_affordable(cash: float, monthly_income: float, existing_payment: float = 0, config=None) -> float:
    """
    计算真实购买力 = min(首付能撬动的总价, 现金+贷款能力)
    """
    mortgage_cfg = config.mortgage if config else MORTGAGE_CONFIG
    down_ratio = mortgage_cfg.get('down_payment_ratio', 0.3)
    max_dti = mortgage_cfg.get('max_dti_ratio', 0.5)
    annual_rate = mortgage_cfg.get('annual_interest_rate', 0.05)
    years = mortgage_cfg.get('loan_term_years', 30)
    
    monthly_rate = annual_rate / 12
    num_payments = years * 12
    
    # 方法1: 首付能撬动的总价
    max_by_down = cash / down_ratio
    
    # 方法2: 贷款能力
    available_payment = max(0, monthly_income * max_dti - existing_payment)
    
    if monthly_rate > 0:
        loan_capacity = available_payment * ((1 + monthly_rate) ** num_payments - 1) / (monthly_rate * (1 + monthly_rate) ** num_payments)
    else:
        loan_capacity = available_payment * num_payments
    
    max_by_loan = cash + loan_capacity
    
    return min(max_by_down, max_by_loan)

