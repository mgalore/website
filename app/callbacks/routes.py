from flask import request, jsonify, current_app

from . import bp

@bp.route('/brassica_notification', methods=['POST']) # Assuming one endpoint for all callbacks
def brassica_notification():
    callback_data = request.get_json()
    if not callback_data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    current_app.logger.info(f"Received Brassica callback: {callback_data}")

    # TODO: Identify the type of callback (send_money, debit_money, create_mandate, etc.) based on payload
    # Example check (needs refinement based on actual callback differences):
    transaction_id = callback_data.get('transactionId')
    if not transaction_id:
        current_app.logger.error("Callback received without transactionId")
        # Decide on response - maybe OK if we can't process?
        return jsonify({"status": "ERROR", "message": "Missing transactionId"}), 400

    # TODO: Validate the callback source if possible (e.g., IP check, signature if provided)
    
    # TODO: Update the transaction status in the database based on the callback data
    # E.g., find transaction by transaction_id and update its status, message, etc.

    # Respond to Brassica as per their requirement
    # The docs specify: { "status": "OK", "message": "Received succesfully." }
    return jsonify({"status": "OK", "message": "Received succesfully."}), 200 