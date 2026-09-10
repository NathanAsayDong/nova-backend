"""
Service for checking Claude API usage and billing information.
Uses Anthropic's API to retrieve account details.
"""

from anthropic import Anthropic
from typing import Optional, Dict, Any
import os


class ClaudeCreditsService:
    """Service for checking Claude API credits and usage."""

    def __init__(self):
        """Initialize with Anthropic client."""
        self.client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Fetch account information from Claude API.

        This uses the undocumented /v1/account endpoint to retrieve
        billing and usage information.

        Returns:
            Dictionary with account info including credits remaining,
            or None if the call fails.
        """
        try:
            # Try to use the internal account endpoint
            response = self.client._client.get(
                "/v1/account",
            )
            return response.json()
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return None

    def get_credits_remaining(self) -> Optional[float]:
        """
        Get the remaining credits on the Claude API account.

        Returns:
            The remaining credit balance, or None if unable to retrieve.
        """
        account_info = self.get_account_info()
        if account_info is None:
            return None

        # The balance is in the account info response
        # Structure depends on Anthropic's API format
        if "account" in account_info:
            account = account_info.get("account", {})
            return account.get("balance_amount")
        return account_info.get("balance_amount")

    def get_usage_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of API usage metrics.

        Returns:
            Dictionary with usage information, or None if unable to retrieve.
        """
        account_info = self.get_account_info()
        if account_info is None:
            return None

        return {
            "credits_remaining": account_info.get("balance_amount"),
            "account_status": account_info.get("account_status", "unknown"),
        }
