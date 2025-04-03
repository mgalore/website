from decimal import Decimal, ROUND_HALF_UP
from flask import current_app

from .db import get_supabase_client

# Define a precision context for Decimal calculations
# Adjust precision (prec) and rounding as needed for your currency
# Example: 4 decimal places
DECIMAL_CONTEXT = decimal.Context(prec=19, rounding=ROUND_HALF_UP)
TWO_PLACES = Decimal('0.0001') # Quantizer for 4 decimal places

def calculate_fee(api_user_id: str, transaction_type: str, amount_str: str, channel: str = None, institution_code: str = None) -> Decimal:
    """Calculates the aggregator fee for a given transaction.

    Args:
        api_user_id: The UUID of the API user initiating the transaction.
        transaction_type: Type of transaction (e.g., 'send_money', 'debit_money').
        amount_str: The transaction amount as a string.
        channel: The channel ('mno', 'interbank', optional).
        institution_code: The institution code (optional).

    Returns:
        The calculated fee amount as a Decimal, or Decimal(0) if no matching rule is found.
    """
    try:
        # Convert amount string to Decimal for accurate calculations
        # Use context for conversion
        amount = DECIMAL_CONTEXT.quantize(Decimal(amount_str), TWO_PLACES)
    except (decimal.InvalidOperation, TypeError):
        current_app.logger.error(f"Invalid amount format for fee calculation: {amount_str}")
        # Decide how to handle invalid amount - perhaps raise error or return 0?
        # Returning 0 for now, but consider raising an exception.
        return Decimal(0)

    if amount <= 0:
        return Decimal(0) # No fee for zero or negative amounts

    supabase = get_supabase_client()
    fee_amount = Decimal(0)
    best_match_rule = None

    try:
        # Construct the query to find matching fee rules
        # We need to check rules specific to the user AND default rules (user_id is NULL)
        # Order by specificity: user-specific rules first, then more specific rules (more non-null fields)
        
        # Build filter conditions dynamically (this is complex with Supabase client)
        # Alternative: Use Supabase RPC (database function) for complex matching logic?
        
        # Simplified approach: Fetch potential rules and filter/sort in Python.
        # Fetch rules for the specific user OR default rules.
        query = supabase.table('fee_structures')\
                      .select('*')\
                      .eq('is_active', True)\
                      .lte('min_amount', float(amount))\
                      .gte('max_amount', float(amount))
                      # Add filters for potentially NULL fields using .or()
        
        # Filter by user_id (specific or default)
        query = query.filter('api_user_id', 'is', None) # Check default rules
        if api_user_id:
             query = query.or_(f'api_user_id.eq.{api_user_id}') # Also check user-specific rules
             
        # Filter by transaction_type (specific or default)
        query = query.filter('transaction_type', 'is', None)
        if transaction_type:
            query = query.or_(f'transaction_type.eq.{transaction_type}')
            
        # Filter by channel (specific or default)
        query = query.filter('channel', 'is', None)
        if channel:
             query = query.or_(f'channel.eq.{channel}')

        # Filter by institution_code (specific or default)
        query = query.filter('institution_code', 'is', None)
        if institution_code:
             query = query.or_(f'institution_code.eq.{institution_code}')

        # Execute the query
        response = query.execute()

        if response.data:
            potential_rules = response.data
            current_app.logger.debug(f"Found {len(potential_rules)} potential fee rules for user {api_user_id}, amount {amount}")

            # Define specificity score function
            def get_specificity_score(rule):
                score = 0
                if rule.get('api_user_id'): score += 8
                if rule.get('transaction_type'): score += 4
                if rule.get('channel'): score += 2
                if rule.get('institution_code'): score += 1
                return score

            # Sort rules by specificity (highest score first)
            potential_rules.sort(key=get_specificity_score, reverse=True)

            # Find the best match (first rule after sorting)
            # We still need to properly check amount ranges and optional field matches
            for rule in potential_rules:
                # Check optional fields match if they are not NULL in the rule
                type_match = rule.get('transaction_type') is None or rule.get('transaction_type') == transaction_type
                channel_match = rule.get('channel') is None or rule.get('channel') == channel
                inst_match = rule.get('institution_code') is None or rule.get('institution_code') == institution_code
                user_match = rule.get('api_user_id') is None or rule.get('api_user_id') == api_user_id
                
                # Check amount range (handle NULLs in min/max_amount)
                min_ok = rule.get('min_amount') is None or Decimal(rule['min_amount']) <= amount
                max_ok = rule.get('max_amount') is None or amount <= Decimal(rule['max_amount'])

                if user_match and type_match and channel_match and inst_match and min_ok and max_ok:
                    best_match_rule = rule
                    current_app.logger.info(f"Selected fee rule ID {best_match_rule['id']} for user {api_user_id}")
                    break # Found the most specific rule

        if best_match_rule:
            fixed_fee = Decimal(best_match_rule.get('fixed_fee', 0))
            percentage_fee_rate = Decimal(best_match_rule.get('percentage_fee', 0))

            # Calculate percentage component
            percentage_component = (amount * percentage_fee_rate)
            
            # Calculate total fee
            total_fee = fixed_fee + percentage_component
            
            # Apply precision and rounding
            fee_amount = DECIMAL_CONTEXT.quantize(total_fee, TWO_PLACES)
            current_app.logger.info(f"Calculated fee: {fee_amount} (Fixed: {fixed_fee}, Rate: {percentage_fee_rate}, Amount: {amount})")
        else:
            current_app.logger.warning(f"No matching fee structure found for user {api_user_id}, type {transaction_type}, amount {amount}. Defaulting to 0 fee.")
            fee_amount = Decimal(0)

    except Exception as e:
        current_app.logger.error(f"Error during fee calculation for user {api_user_id}: {e}", exc_info=True)
        # Decide on error handling - return 0 or raise?
        # Returning 0 for now, but this could mask DB issues.
        fee_amount = Decimal(0)

    return fee_amount 