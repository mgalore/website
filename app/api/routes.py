from flask import Blueprint, request, jsonify, current_app, g
import uuid # For generating unique transaction IDs
from decimal import Decimal # For handling amounts and fees

from . import bp
from ..auth import require_api_key
from ..db import get_supabase_client
from ..services.brassica_client import BrassicaClient, BrassicaAPIError, BrassicaAuthError
from ..fees import calculate_fee # Import the fee calculation function

# Placeholder for Brassica client service (to be created)
# from ..services.brassica_client import BrassicaClient

# --- Helper Functions --- #

def generate_unique_transaction_id():
    """Generates a unique transaction ID."""
    # Combine a UUID with a prefix for easier identification if needed
    return f"AGG-{uuid.uuid4()}"

# --- API Routes --- #

@bp.route('/send_money', methods=['POST'])
@require_api_key
def send_money():
    """Handles send money requests (asynchronous)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # 1. Validate required fields
    required_fields = ['channel', 'institutionCode', 'accountNumber', 'accountName', 'amount', 'creditNaration']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Validate amount format before fee calculation
    try:
        Decimal(data['amount'])
    except Exception:
        return jsonify({"error": "Invalid amount format"}), 400

    # 2. Calculate Fee
    try:
        fee = calculate_fee(
            api_user_id=g.api_user['id'],
            transaction_type='send_money',
            amount_str=data['amount'],
            channel=data.get('channel'),
            institution_code=data.get('institutionCode')
        )
    except Exception as fee_exc:
        # Log the fee calculation error but maybe proceed without fee or reject?
        # For now, log and proceed with zero fee.
        current_app.logger.error(f"Fee calculation failed for user {g.api_user['id']}: {fee_exc}", exc_info=True)
        fee = Decimal(0)

    # TODO: Add balance check logic here later
    # Check if g.api_user has sufficient balance/credit for amount + fee

    # 3. Prepare IDs and Payloads
    aggregator_tx_id = generate_unique_transaction_id()
    brassica_tx_id = data.get('transactionId', aggregator_tx_id) # Use user ID if provided

    brassica_payload = {
        "channel": data['channel'],
        "institutionCode": data['institutionCode'],
        "accountNumber": data['accountNumber'],
        "accountName": data['accountName'],
        "amount": data['amount'],
        "creditNaration": data['creditNaration'],
        "transactionId": brassica_tx_id
    }

    current_app.logger.info(f"Processing send_money {aggregator_tx_id} for user {g.api_user['username']} with fee {fee}")
    supabase = get_supabase_client()

    try:
        # 4. Log initial request to DB
        insert_resp = supabase.table('transactions').insert({
            'id': aggregator_tx_id,
            'api_user_id': g.api_user['id'],
            'transaction_id': brassica_tx_id,
            'transaction_type': 'send_money',
            'channel': data['channel'],
            'institution_code': data['institutionCode'],
            'account_number': data['accountNumber'],
            'account_name': data['accountName'],
            'amount': Decimal(data['amount']), # Store as Decimal
            'narration': data['creditNaration'],
            'fee_amount': float(fee), # Store calculated fee (convert Decimal to float for Supabase)
            'request_payload': data,
            'brassica_request_payload': brassica_payload,
            'status': 'PENDING_PROVIDER', # Status before sending
        }, returning='minimal').execute()

        if not insert_resp.data and insert_resp.error:
            current_app.logger.error(f"DB insert failed for {aggregator_tx_id}: {insert_resp.error}")
            # If DB insert fails, we cannot proceed
            return jsonify({"error": "Failed to record transaction locally"}), 500

        # 5. Call Brassica Client
        brassica_client = BrassicaClient()
        # Use try-except specifically around the API call
        try:
            api_response = brassica_client.send_money(brassica_payload)
            # Default status if API call succeeds but doesn't give definitive status
            new_db_status = 'PENDING_CALLBACK' 
            response_to_user_status = 202
            response_to_user_body = {
                "status": "ACCEPTED",
                "message": "Request accepted and is being processed.",
                "aggregator_transaction_id": aggregator_tx_id,
                "provider_transaction_id": api_response.get('transactionId'),
                "provider_external_id": api_response.get('extralTransactionId'),
                "provider_status_code": api_response.get('statusCode'),
                "provider_status": api_response.get('status'),
                "provider_message": api_response.get('message')
            }

        except (BrassicaAPIError, BrassicaAuthError) as api_err:
            current_app.logger.error(f"Brassica API error during send_money for {aggregator_tx_id}: {api_err}")
            api_response = api_err.response_data if isinstance(api_err, BrassicaAPIError) else None
            new_db_status = 'PROVIDER_REJECTED'
            # Update DB with error details
            supabase.table('transactions').update({
                'status': new_db_status,
                'error_details': str(api_err),
                'initial_brassica_response': api_response,
                'brassica_status_code': api_response.get('statusCode') if api_response else None,
                'brassica_status': api_response.get('status') if api_response else None,
                'brassica_message': api_response.get('message') if api_response else None
            }).eq('id', aggregator_tx_id).execute()
            # Return error to user
            status_code = api_err.status_code if isinstance(api_err, BrassicaAPIError) and api_err.status_code else 502
            return jsonify({"error": f"Provider API Error: {api_err}", "aggregator_transaction_id": aggregator_tx_id}), status_code

        # 6. Log Brassica's Initial Response and Update DB (if API call didn't raise error)
        update_data = {
            'brassica_external_id': api_response.get('extralTransactionId'),
            'initial_brassica_response': api_response,
            'status': new_db_status, # Usually PENDING_CALLBACK
            'brassica_status_code': api_response.get('statusCode'),
            'brassica_status': api_response.get('status'),
            'brassica_message': api_response.get('message')
        }
        update_resp = supabase.table('transactions')\
                              .update(update_data)\
                              .eq('id', aggregator_tx_id)\
                              .execute()

        if not update_resp.data and update_resp.error:
            current_app.logger.error(f"DB update failed for {aggregator_tx_id} after initial API call: {update_resp.error}")
            # Log error, but return the already prepared success response to user

        # 7. Return success response (usually 202 Accepted) to user
        return jsonify(response_to_user_body), response_to_user_status

    except Exception as e:
        # Catch unexpected errors during validation, DB insert, etc.
        current_app.logger.error(f"Unexpected error during send_money {aggregator_tx_id}: {e}", exc_info=True)
        # Attempt to mark DB record as FAILED if it exists
        if aggregator_tx_id:
            try:
                supabase.table('transactions').update({'status': 'FAILED', 'error_details': f'Unexpected error: {e}'}).eq('id', aggregator_tx_id).execute()
            except Exception as db_err:
                current_app.logger.error(f"DB update failed during unexpected error handling for {aggregator_tx_id}: {db_err}")
        return jsonify({"error": "Internal Server Error"}), 500

@bp.route('/debit_money', methods=['POST'])
@require_api_key
def debit_money():
    # TODO: Implement debit_money similar to send_money, including fee calculation
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    current_app.logger.info(f"Received debit_money request from {g.api_user['username']}: {data}")
    return jsonify({"message": "Debit money request received (Not Implemented)", "data": data}), 501

@bp.route('/name_enquiry', methods=['POST'])
@require_api_key
def name_enquiry():
    """Handles name enquiry requests."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # 1. Validate required fields
    required_fields = ['channel', 'institutionCode', 'accountNumber']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Add our own unique transaction ID
    aggregator_tx_id = generate_unique_transaction_id()
    brassica_tx_id = data.get('transactionId', aggregator_tx_id)

    brassica_payload = {
        "channel": data['channel'],
        "institutionCode": data['institutionCode'],
        "accountNumber": data['accountNumber'],
        "transactionId": brassica_tx_id
    }

    current_app.logger.info(f"Processing name_enquiry {aggregator_tx_id} for user {g.api_user['username']}")
    supabase = get_supabase_client()
    # db_record_id = None # Variable not used

    try:
        # 2. Log initial request to DB (No fee for name enquiry typically)
        insert_resp = supabase.table('transactions').insert({
            'id': aggregator_tx_id, # Use our generated UUID as primary key
            'api_user_id': g.api_user['id'],
            'transaction_id': brassica_tx_id, # ID sent to Brassica
            'transaction_type': 'name_enquiry',
            'channel': data['channel'],
            'institution_code': data['institutionCode'],
            'account_number': data['accountNumber'],
            'request_payload': data, # Original request
            'brassica_request_payload': brassica_payload,
            'status': 'PENDING_PROVIDER', # Status before sending
        }, returning='minimal').execute() # Use UUID as PK

        if not insert_resp.data and insert_resp.error:
            current_app.logger.error(f"DB insert failed for {aggregator_tx_id}: {insert_resp.error}")
            return jsonify({"error": "Failed to record transaction locally"}), 500

        # 3. Call Brassica Client
        brassica_client = BrassicaClient()
        api_response = brassica_client.name_enquiry(brassica_payload)

        # 4. Log Brassica Response and Update DB
        update_data = {
            'brassica_external_id': api_response.get('extralTransactionId'),
            'initial_brassica_response': api_response,
            'status': 'SUCCESSFUL' if str(api_response.get('statusCode')) == '200' else 'FAILED', # Compare as string
            'brassica_status_code': api_response.get('statusCode'),
            'brassica_status': api_response.get('status'),
            'brassica_message': api_response.get('message'),
            'account_name': api_response.get('accountName'), # Store the resolved name
            'institution_approval_code': api_response.get('institutionApprovalCode')
        }
        update_resp = supabase.table('transactions')\
                              .update(update_data)\
                              .eq('id', aggregator_tx_id)\
                              .execute()

        if not update_resp.data and update_resp.error:
            current_app.logger.error(f"DB update failed for {aggregator_tx_id} after successful API call: {update_resp.error}")
            # Log error, but likely return success to user as the API call worked

        # 5. Return success/error response to user based on provider status
        if str(api_response.get('statusCode')) == '200':
            user_response = {
                "status": "SUCCESS",
                "aggregator_transaction_id": aggregator_tx_id,
                "provider_status_code": api_response.get('statusCode'),
                "provider_status": api_response.get('status'),
                "provider_message": api_response.get('message'),
                "account_name": api_response.get('accountName'),
                "account_number": api_response.get('accountNumber'),
                "provider_transaction_id": api_response.get('transactionId'),
                "provider_external_id": api_response.get('extralTransactionId')
            }
            return jsonify(user_response), 200
        else:
            # If Brassica returned a non-200 status for name enquiry, treat it as an error
             return jsonify({
                 "error": f"Provider Error: {api_response.get('message', 'Name enquiry failed')}",
                 "aggregator_transaction_id": aggregator_tx_id,
                 "provider_status_code": api_response.get('statusCode'),
                 "provider_status": api_response.get('status'),
             }), 400 # Or map Brassica status code to appropriate HTTP code?

    except (BrassicaAPIError, BrassicaAuthError) as e:
        current_app.logger.error(f"Brassica API error for {aggregator_tx_id}: {e}")
        error_status = 'PROVIDER_REJECTED'
        # Log error details to DB if possible
        error_payload = {
            'status': error_status,
            'error_details': str(e),
        }
        api_response = e.response_data if isinstance(e, BrassicaAPIError) else None
        if api_response:
            error_payload['brassica_status_code'] = api_response.get('statusCode')
            error_payload['brassica_status'] = api_response.get('status')
            error_payload['brassica_message'] = api_response.get('message')
            error_payload['initial_brassica_response'] = api_response

        if aggregator_tx_id:
            try:
                supabase.table('transactions').update(error_payload).eq('id', aggregator_tx_id).execute()
            except Exception as db_err:
                current_app.logger.error(f"DB update failed during error handling for {aggregator_tx_id}: {db_err}")

        status_code = e.status_code if isinstance(e, BrassicaAPIError) and e.status_code else 502
        return jsonify({"error": f"Provider API Error: {e}", "aggregator_transaction_id": aggregator_tx_id}), status_code

    except Exception as e:
        current_app.logger.error(f"Unexpected error during name enquiry {aggregator_tx_id}: {e}", exc_info=True)
        if aggregator_tx_id:
            try:
                supabase.table('transactions').update({'status': 'FAILED', 'error_details': f'Unexpected error: {e}'}).eq('id', aggregator_tx_id).execute()
            except Exception as db_err:
                current_app.logger.error(f"DB update failed during unexpected error handling for {aggregator_tx_id}: {db_err}")

        return jsonify({"error": "Internal Server Error"}), 500

@bp.route('/transaction_status', methods=['POST'])
@require_api_key
def transaction_status():
    # TODO: Implement transaction_status
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    current_app.logger.info(f"Received transaction_status request from {g.api_user['username']}: {data}")
    return jsonify({"message": "Transaction status request received (Not Implemented)", "data": data}), 501

@bp.route('/get_balance', methods=['GET'])
@require_api_key
def get_balance():
    # TODO: Implement get_balance
    current_app.logger.info(f"Received get_balance request from {g.api_user['username']}")
    return jsonify({"message": "Get balance request received (Not Implemented)"}), 501

# TODO: Add endpoints for Direct Debit (createMandate, debitMoney) 