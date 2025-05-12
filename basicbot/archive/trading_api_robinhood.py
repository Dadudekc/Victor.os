import os
import logging
import uuid
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class CustomRobinhoodAPI:
    """
    Custom implementation for Robinhood login with SMS-based MFA handling.
    This version dynamically updates its endpoint URLs by scraping a specified page.
    """
    # Default endpoints
    LOGIN_URL = "https://api.robinhood.com/oauth2/token/"
    MFA_URL = "https://api.robinhood.com/oauth2/mfa/"  # Assumed endpoint for SMS MFA
    REVOKE_URL = "https://api.robinhood.com/oauth2/revoke_token/"
    CHALLENGE_URL_TEMPLATE = "https://api.robinhood.com/challenge/{}/respond/"

    def __init__(self, logger: logging.Logger = None):
        """
        Initializes Robinhood API client.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.username = os.getenv("ROBINHOOD_USERNAME")
        self.password = os.getenv("ROBINHOOD_PASSWORD")
        self.device_token = os.getenv("ROBINHOOD_DEVICE_TOKEN", uuid.uuid4().hex)
        self.access_token = None
        self.logged_in = False
        self.session = requests.Session()
        self.challenge_id = None  # To preserve challenge state if needed

        if not self.username or not self.password:
            raise ValueError("Missing credentials in .env file.")

        self.logger.info("Initialized CustomRobinhoodAPI")

        # Update endpoints dynamically by scraping, if URL is provided.
        self.update_endpoints()

    def update_endpoints(self):
        """
        Scrapes a designated URL for updated Robinhood API endpoints.
        The URL should return an HTML page with elements that contain the endpoint values.
        Expected element IDs: login_url, mfa_url, revoke_url, challenge_url_template.
        """
        endpoints_url = os.getenv("ROBINHOOD_ENDPOINTS_URL")
        if not endpoints_url:
            self.logger.info("No Robinhood endpoints URL provided; using default endpoints.")
            return

        self.logger.info(f"Attempting to scrape endpoints from {endpoints_url}...")
        try:
            response = self.session.get(endpoints_url)
            self._log_response(response)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                login_elem = soup.find("span", {"id": "login_url"})
                mfa_elem = soup.find("span", {"id": "mfa_url"})
                revoke_elem = soup.find("span", {"id": "revoke_url"})
                challenge_elem = soup.find("span", {"id": "challenge_url_template"})

                if login_elem and mfa_elem and revoke_elem and challenge_elem:
                    self.LOGIN_URL = login_elem.text.strip()
                    self.MFA_URL = mfa_elem.text.strip()
                    self.REVOKE_URL = revoke_elem.text.strip()
                    self.CHALLENGE_URL_TEMPLATE = challenge_elem.text.strip()
                    self.logger.info("Endpoints updated successfully via scraping.")
                else:
                    self.logger.error("Failed to find all required endpoint elements on the page.")
            else:
                self.logger.error(f"Scraping endpoints failed with status code: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Exception while scraping endpoints: {e}")

    def login(self):
        """
        Login to Robinhood, handling SMS MFA if required.
        """
        payload = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
            "client_id": "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",
            "scope": "internal",
            "device_token": self.device_token,
        }

        self.logger.info("Attempting login...")
        response = self.session.post(self.LOGIN_URL, data=payload)
        self._log_response(response)

        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            self.logged_in = True
            self.logger.info("Login successful!")
            return True

        elif response.status_code == 403:
            response_data = response.json()
            # Assume SMS MFA is required if a verification workflow is returned.
            if "verification_workflow" in response_data:
                self.challenge_id = response_data["verification_workflow"]["id"]
                return self._handle_sms_verification(self.challenge_id, payload)

            self.logger.error("Unexpected verification response from Robinhood.")
        
        self.logger.error(f"Unexpected error during login: {response.status_code}")
        return False

    def _handle_sms_verification(self, challenge_id, payload):
        """
        Handles SMS-based MFA verification.
        """
        self.logger.info(f"SMS Verification Required. Challenge ID: {challenge_id}")

        # Prompt user for the MFA code received via SMS
        mfa_code = input("Enter the MFA code you received via SMS: ").strip()
        if not mfa_code:
            self.logger.error("No MFA code entered.")
            return False

        self.logger.info(f"Submitting MFA code for challenge ID: {challenge_id}...")
        challenge_url = self.CHALLENGE_URL_TEMPLATE.format(challenge_id)
        response = self.session.post(challenge_url, json={"response": mfa_code})
        self._log_response(response)

        if response.status_code == 200:
            self.logger.info("MFA verification successful! Finalizing login...")
            return self._finalize_login(payload)
        else:
            self.logger.error("MFA verification failed.")
            return False

    def _finalize_login(self, payload):
        """
        Finalizes login after successful MFA verification using the original payload.
        """
        self.logger.info("Finalizing login after MFA verification...")
        response = self.session.post(self.LOGIN_URL, data=payload)
        self._log_response(response)

        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            self.logged_in = True
            self.logger.info("Login finalized successfully!")
            return True
        else:
            self.logger.error("Final login attempt failed.")
            return False

    def _log_response(self, response):
        """
        Logs HTTP response details for debugging.
        """
        self.logger.debug(f"HTTP {response.status_code}: {response.url}")
        self.logger.debug(f"Response: {response.text}")

    def logout(self):
        """
        Log out and invalidate the session.
        """
        if self.logged_in:
            self.logger.info("Logging out...")
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = self.session.post(self.REVOKE_URL, headers=headers)
            self._log_response(response)

            if response.status_code == 200:
                self.logger.info("Logged out successfully.")
                self.logged_in = False
            else:
                self.logger.error("Logout failed.")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("CustomRobinhoodAPI")

    api = CustomRobinhoodAPI(logger)

    try:
        if api.login():
            logger.info("Successfully logged into Robinhood!")
        else:
            logger.error("Failed to log in.")
    finally:
        api.logout()
