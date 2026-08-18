"""
Nova's window into Simpl Finances, the budgeting app.

Everything here goes over HTTPS to the hosted SimplAPI — the same Cloud Run
deployment the React frontend talks to — so Nova always sees exactly the data
the app shows, and this backend never needs SimplAPI's database credentials
or Plaid keys.

SimplAPI authenticates with short-lived session tokens (about an hour,
sliding). Nova logs in with the SIMPL_USERNAME / SIMPL_PASSWORD environment
variables, caches the token, and transparently logs in again whenever a
request comes back 401. The token is cached on the class rather than the
instance because ToolService builds a fresh service instance for every tool
call; an instance-level cache would mean a login round-trip per call.
"""

import os
from typing import Any

import requests

DEFAULT_BASE_URL = "https://simplapi-336517969967.us-west1.run.app"
BASE_URL_ENV = "SIMPL_API_BASE_URL"
USERNAME_ENV = "SIMPL_USERNAME"
PASSWORD_ENV = "SIMPL_PASSWORD"

REQUEST_TIMEOUT_SECONDS = 30

# SimplAPI's DateRange enum, shared by spending queries and budget periods.
VALID_PERIODS = ("WEEK", "MONTH", "THREE_MONTHS", "SIX_MONTHS", "YEAR")

# How many pages of the transaction feed categorize_transaction is willing to
# scan when the transaction isn't in the unclassified list. Recategorizing
# something older than this is out of scope for a chat tool.
MAX_TRANSACTION_SEARCH_PAGES = 10

# Transaction rows carry an embedding vector that is useless to the model and
# large enough to crowd out the context window, so it is stripped everywhere.
_TRANSACTION_NOISE_FIELDS = ("embedding",)


class SimplConfigurationError(RuntimeError):
    """Raised when a Simpl Finances call is attempted without credentials."""


class SimplApiError(RuntimeError):
    """Raised when SimplAPI rejects a request after authentication succeeded."""


class SimpleFinancesService:
    # Shared across instances; see module docstring.
    _session_token: str | None = None

    def __init__(self) -> None:
        self.base_url = (os.getenv(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")

    # ---------- auth ----------

    def _credentials(self) -> tuple[str, str]:
        username = os.getenv(USERNAME_ENV)
        password = os.getenv(PASSWORD_ENV)
        if not username or not password:
            raise SimplConfigurationError(
                f"Simpl Finances credentials are not configured. Set {USERNAME_ENV} "
                f"and {PASSWORD_ENV} in the environment."
            )
        return username, password

    def _login(self) -> str:
        username, password = self._credentials()
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": username, "password": password},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise SimplApiError(
                f"Simpl Finances login failed ({response.status_code}): {response.text}"
            )
        token = response.json().get("sessionId")
        if not token:
            raise SimplApiError("Simpl Finances login response contained no sessionId.")
        SimpleFinancesService._session_token = token
        return token

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        token = SimpleFinancesService._session_token or self._login()

        for attempt in range(2):
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            # Sessions expire after an hour of inactivity; one re-login is the
            # expected recovery, a second 401 means the credentials are wrong.
            if response.status_code == 401 and attempt == 0:
                token = self._login()
                continue
            break

        if response.status_code != 200:
            raise SimplApiError(
                f"Simpl Finances request {method} {path} failed "
                f"({response.status_code}): {response.text}"
            )
        return response.json()

    # ---------- validation helpers ----------

    @staticmethod
    def _validate_period(period: str) -> str:
        normalized = (period or "").strip().upper()
        if normalized not in VALID_PERIODS:
            raise SimplApiError(
                f"Invalid period '{period}'. Must be one of: {', '.join(VALID_PERIODS)}."
            )
        return normalized

    @staticmethod
    def _slim_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in transaction.items()
            if key not in _TRANSACTION_NOISE_FIELDS
        }

    # ---------- accounts ----------

    def sync_accounts(self) -> dict[str, Any]:
        result = self._request("POST", "/sync-transactions")
        return {
            "status": "sync_started",
            "detail": result.get("message", "Accounts syncing in background"),
            "note": (
                "The sync runs in the background on SimplAPI; new transactions "
                "appear within a minute or two."
            ),
        }

    def get_accounts(self) -> list[dict[str, Any]]:
        return self._request("GET", "/get-accounts-all")

    # ---------- spending ----------

    def get_spending(self, period: str = "MONTH", range_pagination: int = 0) -> dict[str, Any]:
        period = self._validate_period(period)
        chart = self._request(
            "GET",
            "/spending/chart",
            params={"period": period, "rangePagination": range_pagination},
        )
        return {"period": period, "range_pagination": range_pagination, "spending_by_day": chart}

    def get_spending_summary(
        self, period: str = "MONTH", range_pagination: int = 0
    ) -> dict[str, Any]:
        period = self._validate_period(period)
        params = {"period": period, "rangePagination": range_pagination}
        need_target, need_spent = self._request("GET", "/spending/need-spend", params=params)
        want_target, want_spent = self._request("GET", "/spending/want-spend", params=params)
        income_total = self._request("GET", "/spending/income-total", params=params)
        return {
            "period": period,
            "range_pagination": range_pagination,
            "needs": {"budgeted": need_target, "spent": need_spent},
            "wants": {"budgeted": want_target, "spent": want_spent},
            "income_total": income_total,
        }

    def get_category_spend(
        self, period: str = "MONTH", range_pagination: int = 0
    ) -> dict[str, Any]:
        period = self._validate_period(period)
        chart = self._request(
            "GET",
            "/spending/chart",
            params={"period": period, "rangePagination": range_pagination},
        )

        totals: dict[str, float] = {}
        for day_amounts in chart.values():
            for category_id, amount in day_amounts.items():
                key = str(category_id)
                totals[key] = totals.get(key, 0.0) + float(amount)

        names = {
            str(category.get("categoryId")): category.get("categoryName")
            for category in self.get_categories()
        }
        return {
            "period": period,
            "range_pagination": range_pagination,
            "categories": [
                {
                    "category_id": category_id,
                    "category_name": names.get(category_id),
                    "total_spent": round(total, 2),
                }
                for category_id, total in sorted(
                    totals.items(), key=lambda item: item[1], reverse=True
                )
            ],
        }

    # ---------- budgets ----------

    def get_budgets(self) -> list[dict[str, Any]]:
        return self._request("GET", "/budget/get-all")

    def get_budget_spend(self, budget_id: int) -> dict[str, Any]:
        spend = self._request("GET", "/budget/budget-spend", params={"budgetId": budget_id})
        return {"budget_id": budget_id, "spend": spend}

    def get_budget_amount(
        self, budget_id: int, period: str = "MONTH", range_pagination: int = 0
    ) -> dict[str, Any]:
        period = self._validate_period(period)
        result = self._request(
            "GET",
            "/budget/get-amount",
            params={
                "budgetId": budget_id,
                "period": period,
                "rangePagination": range_pagination,
            },
        )
        return {
            "budget_id": budget_id,
            "period": period,
            "range_pagination": range_pagination,
            "amount_spent": result.get("amount"),
        }

    def create_budget(
        self,
        budget_name: str,
        amount: float,
        period_type: str = "MONTH",
        description: str = "",
        is_need: bool = False,
    ) -> dict[str, Any]:
        period_type = self._validate_period(period_type)
        return self._request(
            "POST",
            "/budget/add",
            json_body={
                "budgetName": budget_name,
                "amount": amount,
                "periodType": period_type,
                "description": description,
                "is_need": is_need,
            },
        )

    def delete_budget(self, budget_id: int) -> dict[str, Any]:
        # The delete endpoint wants the full budget payload, not just an id,
        # so look it up first — which also gives a clear error for a bad id.
        budgets = self.get_budgets()
        budget = next((b for b in budgets if b.get("budgetId") == budget_id), None)
        if budget is None:
            raise SimplApiError(
                f"No budget with id {budget_id}. Use get_budgets to list "
                "existing budgets and their ids."
            )
        self._request("POST", "/budget/delete", json_body=budget)
        return {"status": "deleted", "budget_id": budget_id, "budget_name": budget.get("budgetName")}

    # ---------- categories ----------

    def get_categories(self) -> list[dict[str, Any]]:
        return self._request("GET", "/get-categories-all")

    # ---------- transactions ----------

    def fetch_uncategorized_transactions(self) -> list[dict[str, Any]]:
        transactions = self._request("GET", "/get-unclassified-transactions")
        return [self._slim_transaction(transaction) for transaction in transactions]

    def get_transactions(
        self,
        page: int = 1,
        account_ids: str = "",
        category_ids: str = "",
        start_date: str = "",
        end_date: str = "",
        search_text: str = "",
    ) -> list[dict[str, Any]]:
        transactions = self._request(
            "GET",
            "/get-filtered-transactions",
            params={
                "page": page,
                "accountIds": account_ids,
                "categoryIds": category_ids,
                "startDate": start_date,
                "endDate": end_date,
                "searchText": search_text,
            },
        )
        return [self._slim_transaction(transaction) for transaction in transactions]

    def categorize_transaction(self, transaction_id: int, category_id: int) -> dict[str, Any]:
        transaction = self._find_transaction(transaction_id)
        self._request(
            "POST",
            "/update-transaction-category",
            json_body={"transaction": transaction, "categoryId": category_id},
        )
        return {
            "status": "categorized",
            "transaction_id": transaction_id,
            "description": transaction.get("description"),
            "category_id": category_id,
        }

    def _find_transaction(self, transaction_id: int) -> dict[str, Any]:
        """
        The categorize endpoint needs the whole transaction object, so resolve
        the id against the unclassified list first (the common case), then walk
        the recent transaction feed.
        """
        for transaction in self.fetch_uncategorized_transactions():
            if transaction.get("transactionId") == transaction_id:
                return transaction

        for page in range(1, MAX_TRANSACTION_SEARCH_PAGES + 1):
            transactions = self.get_transactions(page=page)
            if not transactions:
                break
            for transaction in transactions:
                if transaction.get("transactionId") == transaction_id:
                    return transaction

        raise SimplApiError(
            f"No transaction with id {transaction_id} found in the unclassified "
            f"list or the {MAX_TRANSACTION_SEARCH_PAGES} most recent pages of "
            "transactions. Use fetch_uncategorized_transactions or "
            "get_transactions to find the right id."
        )
