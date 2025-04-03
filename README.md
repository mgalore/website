# Payment Aggregator API Documentation

## 1. Overview

Welcome to the Payment Aggregator API! This service acts as a unified gateway, built on top of the Brassica Pay B-BUS platform, allowing you to easily integrate payment functionalities like sending money, debiting accounts, checking account names, and querying transaction statuses within your applications.

Key features include:
*   Simplified access to Brassica Pay services.
*   User management with API key authentication.
*   Asynchronous transaction handling with callbacks to your system.
*   Support for Mobile Money (MNO) and Interbank transfers in Ghana.
*   Fee structure management (defined per API user).

## 2. Environments

The API is available in the following environments:

*   **Sandbox:** `https://your-sandbox-aggregator-url.com` (Replace with your actual deployed sandbox URL) - Use for testing and development. Connects to Brassica's Sandbox.
*   **Production:** `https://your-production-aggregator-url.com` (Replace with your actual deployed production URL) - Use for live transactions. Connects to Brassica's Production environment.

## 3. Authentication

All requests to the Payment Aggregator API must be authenticated using an API key specific to your account.

*   Obtain your API key through the registration process (details to be provided).
*   Include the API key in the `X-API-Key` header for every request.

**Example Header:**
```
X-API-Key: your_unique_api_key_here
```

Requests without a valid `X-API-Key` header will receive a `401 Unauthorized` error.

## 4. API Endpoints

All endpoints require the `Content-Type: application/json` header for POST requests and the `X-API-Key` header for authentication.

---

### 4.1 Name Enquiry

Allows you to validate a Mobile Money (MOMO) or bank account number and retrieve the associated account name.

*   **Method:** `POST`
*   **Endpoint:** `/api/name_enquiry`
*   **Description:** Verifies the existence and retrieves the name registered to the provided account number via the specified channel and institution.
*   **Request Body:**

    | Field           | Type   | Required | Description                                     | Example          |
    | --------------- | ------ | -------- | ----------------------------------------------- | ---------------- |
    | `channel`       | String | Yes      | `mno` (Mobile Money) or `interbank` (Bank)    | `"mno"`          |
    | `institutionCode` | String | Yes      | 6-digit code of the destination institution. See [Institution Codes](#8-institution-codes). | `"300594"`       |
    | `accountNumber` | String | Yes      | Account number (Mobile: 10 digits, e.g., `020...`; Bank: Varies) | `"233204188594"` |
    | `transactionId` | String | No       | Optional: Your reference ID to be passed to Brassica. If omitted, the aggregator generates one. | `"YOUR_REF_123"` |

*   **Sample Request:**
    ```json
    {
        "channel": "mno",
        "institutionCode": "300594",
        "accountNumber": "233204188594",
        "transactionId": "ENQ_001"
    }
    ```

*   **Success Response (`200 OK`):**
    ```json
    {
        "status": "SUCCESS",
        "aggregator_transaction_id": "AGG-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", // Unique ID from Aggregator
        "provider_status_code": "200",
        "provider_status": "SUCCESSFUL",
        "provider_message": "Request processed successfully",
        "account_name": "Daniel Mawuli Afawubo",
        "account_number": "0204188594", // As resolved by provider
        "provider_transaction_id": "ENQ_001", // ID sent to Brassica
        "provider_external_id": "0000000000" // Brassica's internal ID (extralTransactionId)
    }
    ```

*   **Error Responses:**
    *   `400 Bad Request`: Missing or invalid parameters.
    *   `401 Unauthorized`: Invalid or missing `X-API-Key`.
    *   `500 Internal Server Error`: Unexpected error within the aggregator.
    *   `502 Bad Gateway`: Error communicating with or receiving an error from Brassica. The response body may contain more details.

---

### 4.2 Send Money

Initiates a transfer to a mobile money or bank account. This is an asynchronous operation; the final status is typically delivered via callback.

*   **Method:** `POST`
*   **Endpoint:** `/api/send_money`
*   **Description:** Sends funds to the specified recipient account. Requires a callback URL to be configured for your account to receive the final transaction status.
*   **Request Body:**

    | Field           | Type   | Required | Description                                     | Example          |
    | --------------- | ------ | -------- | ----------------------------------------------- | ---------------- |
    | `channel`       | String | Yes      | `mno` or `interbank`                          | `"interbank"`    |
    | `institutionCode` | String | Yes      | 6-digit code of the destination institution. | `"300592"`       |
    | `accountNumber` | String | Yes      | Recipient account number.                       | `"233277802384"` |
    | `accountName`   | String | Yes      | Name associated with the recipient account (for verification). | `"Prince Adegah"`|
    | `amount`        | String | Yes      | Amount to send (as string, 2 decimal places). | `"1.00"`         |
    | `creditNaration`| String | Yes      | Narration/description for the recipient (max 50 chars). | `"Payment Ref XYZ"`|
    | `transactionId` | String | No       | Optional: Your unique reference ID (max 40 chars). If omitted, the aggregator generates one. | `"MY_SEND_001"`  |

*   **Sample Request:**
    ```json
    {
        "channel": "interbank",
        "institutionCode": "300592",
        "accountNumber": "233277802384",
        "accountName": "Prince Adegah",
        "amount": "1.00",
        "creditNaration": "Testing Credit",
        "transactionId": "PAY_REF_789"
    }
    ```

*   **Initial Success Response (`202 Accepted`):** Indicates the request was received and is being processed. The final status will be sent via callback.
    ```json
    {
        "status": "ACCEPTED",
        "message": "Request received and is being processed.",
        "aggregator_transaction_id": "AGG-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", // Use this ID for status queries
        "provider_status_code": "202", // From Brassica's initial response
        "provider_status": "ACCEPTED", // From Brassica's initial response
        "provider_message": "Request is being processed", // From Brassica
        "provider_transaction_id": "PAY_REF_789", // ID sent to Brassica
        "provider_external_id": "73662553837" // Brassica's internal ID (extralTransactionId)
    }
    ```
    *(Note: The exact fields in the 202 response depend on the implementation and Brassica's immediate reply).*

*   **Error Responses:** Similar to Name Enquiry (400, 401, 500, 502).

---

### 4.3 Debit Money

Initiates a debit from a mobile money account. This is typically asynchronous and requires a callback for the final status.

*   **Method:** `POST`
*   **Endpoint:** `/api/debit_money`
*   **Description:** Attempts to pull funds from the specified MNO account. Requires a callback URL configured for your account.
*   **Request Body:**

    | Field           | Type   | Required | Description                                     | Example          |
    | --------------- | ------ | -------- | ----------------------------------------------- | ---------------- |
    | `channel`       | String | Yes      | Currently only `mno` is supported by Brassica. | `"mno"`          |
    | `institutionCode` | String | Yes      | 6-digit code of the MNO.                    | `"300591"`       |
    | `accountNumber` | String | Yes      | Payer's mobile money account number (e.g., `233...`). | `"233242268121"` |
    | `accountName`   | String | Yes      | Name associated with the payer account (for verification). | `"Melisa"`       |
    | `amount`        | String | Yes      | Amount to debit (as string, 2 decimal places). | `"2.00"`         |
    | `debitNaration` | String | Yes      | Narration for the debit transaction (max 50 chars). | `"Service Payment"`|
    | `serviceType`   | String | Yes      | Type of service (e.g., `ECG`, `DSTV`, `test`). | `"test"`         |
    | `transactionId` | String | No       | Optional: Your unique reference ID (max 40 chars). If omitted, the aggregator generates one. | `"DEBIT_REF_001"`|

*   **Sample Request:**
    ```json
    {
        "channel": "mno",
        "institutionCode": "300591",
        "accountNumber": "233242268121",
        "accountName": "Melisa",
        "amount": "2.00",
        "debitNaration": "Test debit",
        "serviceType": "test",
        "transactionId": "DEBIT_REF_1122"
    }
    ```

*   **Initial Success Response (`202 Accepted`):** Indicates the request was received and is being processed. The final status will be sent via callback.
    ```json
    {
        "status": "ACCEPTED",
        "message": "Request received and is being processed.",
        "aggregator_transaction_id": "AGG-yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
        "provider_status_code": "202",
        "provider_status": "ACCEPTED",
        "provider_message": "Request is being processed",
        "provider_transaction_id": "DEBIT_REF_1122",
        "provider_external_id": "84772553839" // Example Brassica ID
    }
    ```
    *(Note: The exact fields depend on Brassica's immediate reply).*

*   **Error Responses:** Similar to Name Enquiry (400, 401, 500, 502).

---

### 4.4 Transaction Status Query

Allows you to check the current status of a previously initiated transaction.

*   **Method:** `POST`
*   **Endpoint:** `/api/transaction_status`
*   **Description:** Retrieves the status of a transaction using the `aggregator_transaction_id` returned when the transaction was initiated. This may query the aggregator's database or poll Brassica directly if the status is not final.
*   **Request Body:**

    | Field                     | Type   | Required | Description                                      | Example                                      |
    | ------------------------- | ------ | -------- | ------------------------------------------------ | -------------------------------------------- |
    | `aggregator_transaction_id` | String | Yes      | The unique ID generated by the aggregator.       | `"AGG-xxxx..."`                              |
    | `transactionType`         | String | No       | Optional: `credit` or `debit`. May help Brassica locate the transaction. | `"credit"` |

*   **Sample Request:**
    ```json
    {
        "aggregator_transaction_id": "AGG-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
    ```

*   **Success Response (`200 OK`):**
    ```json
    {
        "status": "SUCCESSFUL", // Current status in the aggregator
        "aggregator_transaction_id": "AGG-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "provider_status_code": "200", // Latest status code from Brassica
        "provider_status": "SUCCESSFUL", // Latest status from Brassica
        "provider_message": "Request processed successfully", // Latest message
        "account_name": "Prince Adegah", // If applicable/available
        "account_number": "233277802384", // If applicable/available
        "amount": "1.00", // If applicable/available
        "provider_transaction_id": "PAY_REF_789", // ID originally sent to Brassica
        "provider_external_id": "73662553837", // Brassica's internal ID
        "institution_approval_code": "25809613539", // If applicable
        "last_updated_at": "2023-10-27T10:30:00Z" // Timestamp of the last update
        // May include fee_amount here in future implementations
    }
    ```
    *(Note: The exact fields returned depend on the transaction type and the data available).*

*   **Error Responses:**
    *   `400 Bad Request`: Missing `aggregator_transaction_id`.
    *   `401 Unauthorized`: Invalid or missing `X-API-Key`.
    *   `404 Not Found`: Transaction with the given ID not found.
    *   `500 Internal Server Error`.
    *   `502 Bad Gateway`.

---

### 4.5 Get Balance

Retrieves the available balance on your aggregator account (as reported by Brassica).

*   **Method:** `GET`
*   **Endpoint:** `/api/get_balance`
*   **Description:** Fetches the current available balance from Brassica associated with the API credentials configured for the aggregator.
*   **Request Body:** None

*   **Success Response (`200 OK`):**
    ```json
    {
        "status": "SUCCESS",
        "account_balance": "74.1985", // Balance as string from Brassica
        "retrieved_at": "23-08-2023 10:59:25" // DateTime string from Brassica
    }
    ```
    *(Note: Field names might be adapted slightly from Brassica's direct response for consistency).*

*   **Error Responses:**
    *   `401 Unauthorized`.
    *   `500 Internal Server Error`.
    *   `502 Bad Gateway`.

---

## 5. Callbacks

For asynchronous operations like `Send Money` and `Debit Money`, the aggregator relies on receiving callbacks from Brassica to determine the final transaction status. The aggregator can, in turn, notify your application via a callback.

*   **Registering Your Callback URL:** You need to provide your callback endpoint URL during account setup or via a dedicated management interface (details TBD). This URL must be publicly accessible.
*   **Aggregator Callback Request:** When a final status update is received from Brassica, the aggregator will send a `POST` request to your registered URL with the following JSON payload:

    ```json
    {
        "event_type": "transaction_update", // Type of event
        "aggregator_transaction_id": "AGG-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "status": "SUCCESSFUL", // Final status (e.g., SUCCESSFUL, FAILED)
        "provider_status_code": "200", // Final code from Brassica
        "provider_status": "SUCCESSFUL", // Final status string from Brassica
        "provider_message": "Request processed successfully.", // Final message from Brassica
        "provider_transaction_id": "PAY_REF_789", // ID originally sent to Brassica
        "provider_external_id": "73662553837", // Brassica's internal ID
        "institution_approval_code": "25809613539", // If applicable
        "timestamp": "2023-10-27T10:35:00Z" // Time the callback was processed by the aggregator
        // May include account details, amount, fee_amount etc.
    }
    ```

*   **Expected Response from Your Endpoint:** Your callback endpoint should acknowledge receipt by returning an `HTTP 200 OK` status code with a simple JSON body, for example:
    ```json
    {
        "status": "received"
    }
    ```
    The aggregator may retry sending the callback if it doesn't receive a 200 OK response within a certain timeout period.

## 6. Transaction IDs

Understanding the different IDs is important:

*   **`transactionId` (User Input):** An optional ID you can provide when initiating a transaction (e.g., `/api/send_money`). This is passed to Brassica.
*   **`aggregator_transaction_id` (Output):** A unique UUID generated by *this* aggregator service for every request it processes. This ID is returned in API responses and callbacks. **Use this ID when querying the `/api/transaction_status` endpoint.**
*   **`provider_transaction_id` (Output):** The `transactionId` that was actually sent to Brassica (either the one you provided or one generated by the aggregator). Included in responses/callbacks for reference.
*   **`provider_external_id` (Output):** Brassica's unique internal transaction identifier (`extralTransactionId`). Included in responses/callbacks.

## 7. Fees

Fees may be applied to certain transactions based on your agreement and the configured fee structure.

*   Fees are calculated based on factors like transaction type, channel, amount, and your specific user account.
*   *(Future Implementation):* The calculated fee amount may be included in the transaction status response or callbacks.
*   Currently, fee calculation happens internally. Please refer to your service agreement for details on applicable fees.

## 8. Institution Codes

You will need these codes for the `institutionCode` parameter.

| Institution Code | Institution Name                       | Type      |
| :--------------- | :------------------------------------- | :-------- |
| `300303`         | Absa Bank Ghana Limited                | Interbank |
| `300329`         | Access Bank Ghana Plc                  | Interbank |
| `300307`         | Agricultural Development Bank of Ghana | Interbank |
| `300306`         | ARB Apex Bank PLC                      | Interbank |
| `300320`         | Bank of Africa Ghana Limited           | Interbank |
| `300313`         | Cal Bank Limited                       | Interbank |
| `300331`         | Consolidated Bank Ghana Limited        | Interbank |
| `300312`         | Ecobank Ghana Limited                  | Interbank |
| `300319`         | FBN Bank Ghana Limited                 | Interbank |
| `300323`         | Fidelity Bank Ghana Limited            | Interbank |
| `300316`         | First Atlantic Bank Limited            | Interbank |
| `300334`         | First National Bank Ghana              | Interbank |
| `300304`         | GCB Bank Limited                       | Interbank |
| `300322`         | Guaranty Trust Bank Ghana Limited      | Interbank |
| `300305`         | National Investment Bank Limited       | Interbank |
| `300324`         | Omni BSIC Bank Ghana Limited           | Interbank |
| `300317`         | Prudential Bank Limited                | Interbank |
| `300310`         | Republic Bank Ghana Limited            | Interbank |
| `300308`         | Société Générale Ghana Limited         | Interbank |
| `300318`         | Stanbic Bank Ghana Limited             | Interbank |
| `300302`         | Standard Chartered Bank Ghana Limited  | Interbank |
| `300325`         | United Bank for Africa Ghana Limited   | Interbank |
| `300309`         | Universal Merchant Bank Limited        | Interbank |
| `300311`         | Zenith Bank Ghana Limited              | Interbank |
| `300591`         | MTN                                    | MNO       |
| `300592`         | AIRTELTIGO MONEY                       | MNO       |
| `300594`         | VODAFONE CASH                          | MNO       |

## 9. Error Handling

The API uses standard HTTP status codes to indicate success or failure.

*   **`200 OK`:** Request successful (synchronous operations).
*   **`202 Accepted`:** Request accepted for processing (asynchronous operations).
*   **`400 Bad Request`:** Invalid syntax or missing parameters in the request body. The response body will contain an `error` field with details.
*   **`401 Unauthorized`:** Missing or invalid `X-API-Key`.
*   **`404 Not Found`:** The requested resource (e.g., a specific transaction ID) was not found.
*   **`500 Internal Server Error`:** An unexpected error occurred on the aggregator's server.
*   **`502 Bad Gateway`:** The aggregator encountered an error communicating with the downstream provider (Brassica) or received an error response from them. The response body may contain provider-specific error details.
*   **`503 Service Unavailable`:** The service is temporarily unavailable (e.g., maintenance).

Error responses will generally follow this format:
```json
{
    "error": "Description of the error",
    "aggregator_transaction_id": "AGG-xxxx..." // Included if available
    // Potentially other fields like "provider_error_code"
}
```

## 10. Aggregator Status Codes (Internal)

The `status` field within the transaction record (retrieved via status query or callback) indicates the internal state within the aggregator:

*   `RECEIVED`: Initial request received from the API user, not yet processed.
*   `SENT_TO_PROVIDER`: Request successfully sent to Brassica.
*   `PENDING_CALLBACK`: Waiting for a final status callback from Brassica (for async operations).
*   `SUCCESSFUL`: Transaction completed successfully according to Brassica.
*   `FAILED`: Transaction failed according to Brassica or due to an internal error.
*   `PROVIDER_REJECTED`: Brassica rejected the initial request (e.g., validation error, authentication failure).

*(Note: This list may evolve)* 