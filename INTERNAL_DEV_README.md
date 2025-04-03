# Internal Developer Documentation - Payment Aggregator

This document provides technical details about the codebase, setup, and architecture for developers working on the Payment Aggregator service.

## 1. Project Structure

```
.
├── app/                      # Main Flask application package
│   ├── api/                  # Handles incoming API requests from users
│   │   ├── __init__.py       # API blueprint initialization
│   │   └── routes.py         # Defines API endpoints (/api/...)
│   ├── callbacks/            # Handles incoming callbacks from Brassica
│   │   ├── __init__.py       # Callbacks blueprint initialization
│   │   └── routes.py         # Defines callback endpoints (/callbacks/...)
│   ├── services/             # Contains clients for external services
│   │   └── brassica_client.py # Client for interacting with the Brassica API
│   ├── __init__.py           # Application factory (create_app)
│   ├── auth.py               # API key authentication logic
│   └── db.py                 # Supabase client initialization
├── venv/                     # Virtual environment directory (if named venv)
├── .env                      # Local environment variables (ignored by git)
├── .env.example              # Template for environment variables
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── run.py                    # Script to run the Flask development server
├── README.md                 # Documentation for API Consumers (External)
└── INTERNAL_DEV_README.md    # This file (Internal Developer Docs)
```

## 2. Setup Instructions

1.  **Clone Repository:** Get the code onto your local machine.
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate Environment:**
    *   Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
    *   Windows (Git Bash/CMD): `source venv/Scripts/activate`
    *   macOS/Linux: `source venv/bin/activate`
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set Up Environment Variables:**
    *   Copy `.env.example` to `.env`.
    *   Fill in the required values in `.env`:
        *   `FLASK_SECRET_KEY`: Generate a strong secret key (e.g., using `python -c 'import secrets; print(secrets.token_hex(16))'`).
        *   `BRASSICA_USERNAME`, `BRASSICA_PASSWORD`: Credentials for the Brassica API (use Sandbox credentials for development).
        *   `BRASSICA_BASE_URL`: Should point to the Brassica Sandbox URL (`https://bbussandbox.brassicagroup.com/BBusGateway`).
        *   `CALLBACK_URL`: The publicly accessible URL where *Brassica* can send callbacks to *this running application*. Use a tunneling service like `ngrok` during local development (e.g., `https://<ngrok_subdomain>.ngrok.io/callbacks/brassica_notification`).
        *   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`: Credentials for your Supabase project.
6.  **Set Up Supabase Database:**
    *   Ensure you have created the necessary tables in your Supabase project using the SQL provided in the project setup phase (see `transactions`, `api_users`, `fee_structures`, `user_callback_urls`).
    *   Make sure the `fee_amount` column has been added to the `transactions` table.

## 3. Running the Application

Ensure your virtual environment is active and the `.env` file is correctly configured.

Start the Flask development server:

```bash
flask run
# or
python run.py
```

The application will typically run on `http://127.0.0.1:5000` by default.

## 4. Core Components & Architecture

### 4.1 Flask Application (`app/__init__.py`)

*   Uses the **Application Factory Pattern** (`create_app`).
*   Loads configuration from environment variables via `python-dotenv` and `os.getenv` into `app.config`.
*   Registers Blueprints (`api`, `callbacks`) to organize routes.
*   Provides a basic `/health` check endpoint.

### 4.2 Configuration

*   Managed via the `.env` file and loaded into `app.config`.
*   Key config values:
    *   Brassica API credentials and base URL.
    *   Supabase URL and Service Key.
    *   Flask Secret Key.
    *   The aggregator's own callback URL (needed for Brassica).

### 4.3 Authentication (`app/auth.py`)

*   **`@require_api_key` Decorator:** Protects API endpoints.
*   **Mechanism:** Extracts the API key from the `X-API-Key` request header.
*   **Validation:** Queries the `api_users` table in Supabase to find an active user matching the key.
*   **Security Note:** Currently performs a direct lookup of the API key. **This MUST be changed** to store securely hashed API keys in the database and compare hashes during validation.
*   **Context:** Stores the authenticated user's data (`id`, `username`) in `flask.g.api_user` for use within the request context.

### 4.4 Brassica Client (`app/services/brassica_client.py`)

*   **Purpose:** Encapsulates all interaction logic with the external Brassica Pay API.
*   **Authentication:** Handles obtaining and caching the Brassica Bearer token.
    *   Calls the `/Authenticate` endpoint.
    *   Uses `PyJWT` to decode the token (`resp1` from auth response) **without signature verification** (as the secret isn't available) solely to extract the `exp` (expiry time) claim.
    *   Automatically requests a new token if the current one is missing or close to expiry (`_get_valid_token`).
*   **Request Handling:** Provides methods (`send_money`, `name_enquiry`, etc.) mirroring Brassica API operations.
    *   Uses the `requests` library.
    *   Constructs appropriate headers (including `Authorization: Bearer <token>`).
    *   Includes error handling for HTTP errors and potential API-level errors reported in the response body.
*   **Error Handling:** Raises custom exceptions (`BrassicaAuthError`, `BrassicaAPIError`) to signal issues to the calling route handler. `BrassicaAPIError` includes `status_code` and `response_data` attributes where possible.
*   **Potential Issue:** The documentation for Direct Debit `debitMoney` uses the `createMandate` endpoint name. This might be incorrect. The client currently uses a placeholder name (`debit_mandate` method calling a hypothetical `debitMandate` endpoint) and logs a warning. Verify the correct endpoint.

### 4.5 Database (`app/db.py` & Schema)

*   **`get_supabase_client()`:** Utility function to initialize the `supabase-py` client using credentials from `app.config`. It stores the client instance in `flask.g` to reuse it within a single request context.
*   **Schema:** Defined in SQL (see initial setup steps or query the DB). Key tables:
    *   `api_users`: Consumers of *this* aggregator API.
    *   `user_callback_urls`: Callback endpoints for *our* API users (for aggregator-to-user notifications - **Not yet implemented**).
    *   `transactions`: Logs every transaction attempt, parameters, provider IDs, status updates (internal and Brassica's), fees, and payloads.
    *   `fee_structures`: Defines fee rules (user-specific override defaults).
*   **`updated_at` Trigger:** A Postgres function and trigger automatically update the `updated_at` column in the `transactions` table on any `UPDATE` operation.

### 4.6 API Routes (`app/api/routes.py`)

*   Defines endpoints exposed to the aggregator's users (e.g., `/api/send_money`).
*   Protected by `@require_api_key`.
*   **Typical Flow (Example: `name_enquiry`):**
    1.  Receive and validate request JSON.
    2.  Generate `aggregator_transaction_id` (UUID).
    3.  Get Supabase client (`get_supabase_client`).
    4.  Insert initial record into `transactions` table (status: `RECEIVED` or `SENT_TO_PROVIDER`).
    5.  Instantiate `BrassicaClient`.
    6.  Call the relevant `BrassicaClient` method.
    7.  Handle `BrassicaAPIError`/`BrassicaAuthError` (log to DB, return error response).
    8.  Update the `transactions` record with response details and final status (`SUCCESSFUL`/`FAILED`).
    9.  Return a success/error response to the API user.
*   **Asynchronous Flow (e.g., `send_money` - **Partially Implemented**):
    1.  Steps 1-6 as above.
    2.  Handle the *initial* response from Brassica (often `202 Accepted`).
    3.  Update the `transactions` record with the initial response and status (e.g., `ACCEPTED` or `PENDING_CALLBACK`).
    4.  Return `202 Accepted` to the API user.
    5.  The final status update relies on the callback handler.

### 4.7 Callback Handler (`app/callbacks/routes.py`)

*   **Purpose:** Receives asynchronous status updates from *Brassica*.
*   **Endpoint:** `/callbacks/brassica_notification` (or similar - must match `CALLBACK_URL` in `.env`). Must be publicly accessible.
*   **Current Implementation (Placeholder):**
    *   Receives POST request with JSON payload from Brassica.
    *   Logs the received data.
    *   Returns the required `200 OK` response (`{"status": "OK", "message": "Received succesfully."}`) to acknowledge receipt.
*   **Required Implementation:**
    1.  **(Optional but Recommended) Validate Callback Source:** Check source IP or use a signature if Brassica provides one.
    2.  Extract key identifiers (e.g., `transactionId`, `extralTransactionId`) from the callback payload.
    3.  Query the `transactions` table to find the matching record (likely using `transaction_id` or `brassica_external_id`).
    4.  Update the transaction record with the final status (`SUCCESSFUL`/`FAILED`), status codes, messages, and the callback payload itself.
    5.  **(Aggregator-to-User Callback - Future):** If a user callback URL exists for this `api_user_id` in `user_callback_urls`, queue or send a notification to that user's endpoint.

### 4.8 Fee Calculation (Conceptual)

*   **Goal:** Calculate fees based on rules in `fee_structures`.
*   **Plan:**
    1.  Create `calculate_fee(api_user_id, transaction_type, channel, amount, ...)` function.
    2.  Query `fee_structures` table, prioritizing user-specific rules over defaults (where `api_user_id` is NULL).
    3.  Match based on type, channel, amount range.
    4.  Calculate `fixed_fee + (amount * percentage_fee)`.
    5.  Integrate this function into transaction processing routes (e.g., `send_money`, `debit_money`).
    6.  Store the result in the `transactions.fee_amount` column (ensure column exists via `ALTER TABLE`).

## 5. Development Notes & TODOs

*   **API Key Security:** Implement hashing for API keys in `api_users` and update the `require_api_key` decorator.
*   **Implement Missing Routes:** Flesh out `send_money`, `debit_money`, `transaction_status`, `get_balance`, and Direct Debit endpoints.
*   **Implement Callback Logic:** Complete the database update logic in `app/callbacks/routes.py`.
*   **Implement Fee Calculation:** Create and integrate the `calculate_fee` function.
*   **Aggregator-to-User Callbacks:** Implement the system to send notifications to user-defined callback URLs stored in `user_callback_urls`.
*   **Input Validation:** Add more robust input validation (data types, lengths, formats) to API routes.
*   **Testing:** Add unit and integration tests.
*   **Logging:** Enhance logging where needed for better traceability.
*   **Deployment:** Create deployment scripts/configuration (e.g., Dockerfile, server configuration).
*   **User Management Interface:** A way to create/manage `api_users` and their associated `user_callback_urls` and `fee_structures` might be needed. 