import requests
import time
import jwt # Added for JWT decoding
from flask import current_app

class BrassicaAuthError(Exception):
    """Custom exception for authentication errors."""
    pass

class BrassicaAPIError(Exception):
    """Custom exception for general API errors."""
    # Add status_code and response_data attributes for more detailed error info
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class BrassicaClient:
    def __init__(self):
        self.base_url = current_app.config['BRASSICA_BASE_URL']
        self.username = current_app.config['BRASSICA_USERNAME']
        self.password = current_app.config['BRASSICA_PASSWORD']
        self.token = None
        self.token_expiry_time = 0 # Store token expiry time (epoch seconds)

    def _get_headers(self, include_auth=True):
        headers = {
            'Content-Type': 'application/json'
        }
        if include_auth:
            token = self._get_valid_token()
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _get_valid_token(self):
        # Check if token exists and is not expired (with a small buffer)
        buffer_seconds = 60 # Refresh token if it expires within the next 60 seconds
        if self.token and time.time() < self.token_expiry_time - buffer_seconds:
            return self.token
        
        # If token is invalid or expired, get a new one
        return self._authenticate()

    def _authenticate(self):
        """Authenticates with Brassica and stores the token and expiry."""
        auth_url = f"{self.base_url}/Authenticate"
        payload = {
            "userName": self.username,
            "password": self.password
        }
        headers = {'Content-Type': 'application/json'}
        
        try:
            current_app.logger.info(f"Authenticating with Brassica at {auth_url}")
            response = requests.post(auth_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            current_app.logger.debug(f"Authentication response data: {data}")

            if data.get('response') == '000' and data.get('data', {}).get('resp1'):
                self.token = data['data']['resp1']
                try:
                    # Decode the JWT token without verification to get the payload
                    # WARNING: We are NOT verifying the signature as we don't have the secret key.
                    # We are only interested in the expiry time (exp claim).
                    decoded_token = jwt.decode(self.token, options={"verify_signature": False, "verify_aud": False})
                    self.token_expiry_time = decoded_token.get('exp')
                    if self.token_expiry_time:
                         current_app.logger.info(f"Successfully authenticated. Token expires at: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self.token_expiry_time))}")
                    else:
                        # Fallback if 'exp' claim is missing (use a short default)
                        self.token_expiry_time = time.time() + 240 # Fallback: 4 minutes
                        current_app.logger.warning("Token expiry ('exp') claim not found in JWT. Using default 4 min validity.")
                except jwt.PyJWTError as e:
                    # Fallback if JWT decoding fails
                    self.token_expiry_time = time.time() + 240 # Fallback: 4 minutes
                    current_app.logger.error(f"Error decoding JWT token: {e}. Using default 4 min validity.")

                return self.token
            else:
                error_msg = data.get('responseMesg', 'Authentication failed')
                current_app.logger.error(f"Brassica authentication failed: {error_msg}")
                raise BrassicaAuthError(f"Authentication failed: {error_msg}")

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error during Brassica authentication request: {e}")
            raise BrassicaAPIError(f"API request error during authentication: {e}")
        except Exception as e:
             current_app.logger.error(f"Unexpected error during Brassica authentication: {e}")
             # Pass the original exception for better debugging
             raise BrassicaAuthError(f"Unexpected error during authentication: {e}") from e

    def _make_request(self, method, endpoint, payload=None, include_auth=True):
        """Helper method to make authenticated requests."""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers(include_auth=include_auth)
        
        try:
            current_app.logger.info(f"Making {method} request to {url} with payload: {payload}")
            if method.upper() == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=30) # Longer timeout for transactions
            elif method.upper() == 'GET':
                 response = requests.get(url, headers=headers, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Note: Don't raise_for_status immediately if we want to capture API-level errors from the body
            # response.raise_for_status() # Check for HTTP errors

            # Check for specific non-JSON success cases first
            if response.status_code == 204: # No Content
                return None
            if not response.content:
                 current_app.logger.warning(f"Received empty response body from {url} with status {response.status_code}")
                 # If status is OK-ish (2xx) but no content, might be acceptable? Return None.
                 # If status is an error (4xx/5xx), we'll handle it below.
                 return None if 200 <= response.status_code < 300 else response.text # Or raise?

            # Try parsing JSON, handle potential errors
            try:
                 response_data = response.json()
                 current_app.logger.debug(f"Response from {url} (Status {response.status_code}): {response_data}")
            except ValueError:
                 # If response is not JSON, log and potentially raise based on status code
                 error_body = response.text
                 current_app.logger.error(f"Failed to decode JSON response from {url} (Status {response.status_code}). Body: {error_body}")
                 if 400 <= response.status_code < 600:
                      raise BrassicaAPIError(f"Brassica API non-JSON error: {response.status_code} {response.reason}. Response: {error_body}", status_code=response.status_code)
                 else:
                     # What to do on non-error, non-JSON response? Maybe return raw text or None?
                     return error_body # Or None

            # Now check for application-level errors indicated by status code or response content
            # Brassica seems to use HTTP status codes + response codes in the JSON body
            if 400 <= response.status_code < 600:
                 error_msg = response_data.get('message', f"HTTP error {response.status_code}")
                 current_app.logger.error(f"Brassica API error response from {url}: {response_data}")
                 raise BrassicaAPIError(error_msg, status_code=response.status_code, response_data=response_data)

            # Consider non-2xx status codes that might not be errors based on Brassica docs (e.g., 202 Accepted)
            # The current logic assumes any JSON response from a non-4xx/5xx status is success.
            # Refine this if specific non-error status codes need special handling.

            return response_data

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error calling Brassica API {url}: {e}")
            raise BrassicaAPIError(f"API request error: {e}")
        # Keep the custom BrassicaAPIError catch if it was raised above
        except BrassicaAPIError as e:
             raise e
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Brassica API call {url}: {e}")
            # Pass the original exception for better debugging
            raise BrassicaAPIError(f"Unexpected error: {e}") from e

    # --- API Methods --- #

    def send_money(self, data):
        """Calls the sendMoney endpoint."""
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'sendMoney', payload=data)

    def debit_money(self, data):
        """Calls the debitMoney endpoint."""
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'debitMoney', payload=data)

    def name_enquiry(self, data):
        """Calls the nameEnquiry endpoint."""
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'nameEnquiry', payload=data)

    def transaction_status_query(self, data):
        """Calls the transStatusQuery endpoint."""
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'transStatusQuery', payload=data)

    def get_balance(self):
        """Calls the GetAvailableBalance endpoint."""
        return self._make_request('GET', 'GetAvailableBalance')

    def create_mandate(self, data):
        """Calls the createMandate endpoint."""
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'createMandate', payload=data)

    def debit_mandate(self, data):
        """Calls the Direct Debit debitMoney endpoint."""
        # Note: The docs show the same endpoint 'createMandate' for DD debit, which seems wrong.
        # Assuming it should be a different endpoint or requires a specific flag.
        # Using a placeholder endpoint name 'debitMandate' for now.
        # Verify the correct endpoint with Brassica documentation/support.
        current_app.logger.warning("Using placeholder endpoint 'debitMandate' for Direct Debit debit. Verify correct endpoint.")
        # TODO: Add validation for required fields in 'data'
        return self._make_request('POST', 'debitMandate', payload=data) # Replace 'debitMandate' if needed 