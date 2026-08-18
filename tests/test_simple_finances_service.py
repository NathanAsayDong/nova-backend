import unittest
from unittest import mock

from src.service.simple_finances_service import (
    SimplApiError,
    SimplConfigurationError,
    SimpleFinancesService,
    PASSWORD_ENV,
    USERNAME_ENV,
)


def response(status_code=200, json_body=None, text=""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else {}
    resp.text = text
    return resp


LOGIN_OK = response(json_body={"status": "success", "sessionId": "token-1"})

CREDS = {USERNAME_ENV: "nathan@example.com", PASSWORD_ENV: "hunter2"}


class SimpleFinancesServiceTest(unittest.TestCase):
    def setUp(self):
        # The token cache is class-level (it must outlive the per-tool-call
        # instances), so each test starts logged out.
        SimpleFinancesService._session_token = None
        self.service = SimpleFinancesService()

        env = mock.patch.dict("os.environ", CREDS)
        env.start()
        self.addCleanup(env.stop)

    # ---------- auth ----------

    def test_missing_credentials_raise_configuration_error(self):
        with mock.patch.dict("os.environ", {USERNAME_ENV: "", PASSWORD_ENV: ""}):
            with self.assertRaises(SimplConfigurationError):
                self.service.get_budgets()

    @mock.patch("src.service.simple_finances_service.requests")
    def test_logs_in_once_and_reuses_token_across_instances(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(json_body=[])

        self.service.get_budgets()
        SimpleFinancesService().get_categories()

        self.assertEqual(requests_mock.post.call_count, 1)
        for call in requests_mock.request.call_args_list:
            self.assertEqual(
                call.kwargs["headers"], {"Authorization": "Bearer token-1"}
            )

    @mock.patch("src.service.simple_finances_service.requests")
    def test_relogs_in_once_on_expired_session(self, requests_mock):
        SimpleFinancesService._session_token = "stale-token"
        requests_mock.post.return_value = response(json_body={"sessionId": "fresh-token"})
        requests_mock.request.side_effect = [
            response(status_code=401, text="Invalid session"),
            response(json_body=[{"budgetId": 1}]),
        ]

        budgets = self.service.get_budgets()

        self.assertEqual(budgets, [{"budgetId": 1}])
        self.assertEqual(requests_mock.post.call_count, 1)
        retry = requests_mock.request.call_args_list[1]
        self.assertEqual(retry.kwargs["headers"], {"Authorization": "Bearer fresh-token"})

    @mock.patch("src.service.simple_finances_service.requests")
    def test_second_401_surfaces_as_error_not_login_loop(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(status_code=401, text="Invalid session")

        with self.assertRaises(SimplApiError):
            self.service.get_budgets()
        # Initial login plus exactly one recovery login.
        self.assertEqual(requests_mock.post.call_count, 2)

    @mock.patch("src.service.simple_finances_service.requests")
    def test_failed_login_raises(self, requests_mock):
        requests_mock.post.return_value = response(status_code=401, text="Invalid credentials")

        with self.assertRaises(SimplApiError):
            self.service.get_budgets()

    # ---------- validation ----------

    def test_invalid_period_rejected_before_any_request(self):
        with self.assertRaises(SimplApiError) as ctx:
            self.service.get_spending(period="FORTNIGHT")
        self.assertIn("FORTNIGHT", str(ctx.exception))

    @mock.patch("src.service.simple_finances_service.requests")
    def test_period_is_normalized(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(json_body={})

        result = self.service.get_spending(period="month")

        self.assertEqual(result["period"], "MONTH")
        params = requests_mock.request.call_args.kwargs["params"]
        self.assertEqual(params["period"], "MONTH")

    # ---------- budgets ----------

    @mock.patch("src.service.simple_finances_service.requests")
    def test_delete_budget_posts_full_payload(self, requests_mock):
        budget = {"budgetId": 7, "budgetName": "Dining", "amount": 200.0, "budget_categories": []}
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.side_effect = [
            response(json_body=[budget]),
            response(json_body={"message": "budget deleted successfully"}),
        ]

        result = self.service.delete_budget(7)

        self.assertEqual(result, {"status": "deleted", "budget_id": 7, "budget_name": "Dining"})
        delete_call = requests_mock.request.call_args_list[1]
        self.assertEqual(delete_call.args[1], f"{self.service.base_url}/budget/delete")
        self.assertEqual(delete_call.kwargs["json"], budget)

    @mock.patch("src.service.simple_finances_service.requests")
    def test_delete_budget_unknown_id_fails_without_deleting(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(json_body=[{"budgetId": 1}])

        with self.assertRaises(SimplApiError):
            self.service.delete_budget(999)
        # Only the lookup ran; nothing was posted to /budget/delete.
        self.assertEqual(requests_mock.request.call_count, 1)

    # ---------- spending ----------

    @mock.patch("src.service.simple_finances_service.requests")
    def test_get_category_spend_totals_and_names(self, requests_mock):
        chart = {
            "2026-08-01": {"1": 25.0, "2": 10.0},
            "2026-08-02": {"1": 5.0},
        }
        categories = [
            {"categoryId": 1, "categoryName": "Groceries"},
            {"categoryId": 2, "categoryName": "Gas"},
        ]
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.side_effect = [
            response(json_body=chart),
            response(json_body=categories),
        ]

        result = self.service.get_category_spend(period="MONTH")

        self.assertEqual(
            result["categories"],
            [
                {"category_id": "1", "category_name": "Groceries", "total_spent": 30.0},
                {"category_id": "2", "category_name": "Gas", "total_spent": 10.0},
            ],
        )

    @mock.patch("src.service.simple_finances_service.requests")
    def test_get_spending_summary_combines_endpoints(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.side_effect = [
            response(json_body=[1000.0, 800.0]),
            response(json_body=[400.0, 450.0]),
            response(json_body=5200.0),
        ]

        result = self.service.get_spending_summary(period="MONTH")

        self.assertEqual(result["needs"], {"budgeted": 1000.0, "spent": 800.0})
        self.assertEqual(result["wants"], {"budgeted": 400.0, "spent": 450.0})
        self.assertEqual(result["income_total"], 5200.0)

    # ---------- transactions ----------

    @mock.patch("src.service.simple_finances_service.requests")
    def test_uncategorized_transactions_are_stripped_of_embeddings(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(
            json_body=[
                {
                    "transactionId": 5,
                    "description": "COSTCO",
                    "amount": 84.12,
                    "embedding": [0.1] * 1536,
                }
            ]
        )

        transactions = self.service.fetch_uncategorized_transactions()

        self.assertEqual(
            transactions,
            [{"transactionId": 5, "description": "COSTCO", "amount": 84.12}],
        )

    @mock.patch("src.service.simple_finances_service.requests")
    def test_categorize_transaction_resolves_id_from_unclassified_list(self, requests_mock):
        transaction = {"transactionId": 5, "description": "COSTCO", "amount": 84.12}
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.side_effect = [
            response(json_body=[dict(transaction, embedding=[0.1, 0.2])]),
            response(json_body={"message": "category updated successfully"}),
        ]

        result = self.service.categorize_transaction(transaction_id=5, category_id=3)

        self.assertEqual(result["status"], "categorized")
        update_call = requests_mock.request.call_args_list[1]
        self.assertEqual(
            update_call.kwargs["json"],
            {"transaction": transaction, "categoryId": 3},
        )

    @mock.patch("src.service.simple_finances_service.requests")
    def test_categorize_transaction_falls_back_to_transaction_feed(self, requests_mock):
        transaction = {"transactionId": 9, "description": "SHELL", "amount": 40.0}
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.side_effect = [
            response(json_body=[]),  # nothing unclassified
            response(json_body=[transaction]),  # feed page 1
            response(json_body={"message": "category updated successfully"}),
        ]

        result = self.service.categorize_transaction(transaction_id=9, category_id=2)

        self.assertEqual(result["transaction_id"], 9)

    @mock.patch("src.service.simple_finances_service.requests")
    def test_categorize_transaction_unknown_id_gives_actionable_error(self, requests_mock):
        requests_mock.post.return_value = LOGIN_OK
        requests_mock.request.return_value = response(json_body=[])

        with self.assertRaises(SimplApiError) as ctx:
            self.service.categorize_transaction(transaction_id=123, category_id=1)
        self.assertIn("fetch_uncategorized_transactions", str(ctx.exception))


class SimplFinancesToolRegistrationTest(unittest.TestCase):
    """The registered tool definitions must actually match the service."""

    def test_tool_callables_resolve_and_schemas_bind(self):
        import inspect

        from scripts.register_project_tools import SIMPL_FINANCES_TOOLS

        for definition in SIMPL_FINANCES_TOOLS:
            config = definition["config"]
            module_name, class_name, method_name = config["callable_path"].rsplit(".", 2)
            self.assertEqual(module_name, "src.service.simple_finances_service")
            self.assertEqual(class_name, "SimpleFinancesService")

            method = getattr(SimpleFinancesService, method_name, None)
            self.assertIsNotNone(method, f"{definition['name']} points at a missing method")

            # Every schema property must be a real keyword of the method, and
            # every required schema property must be a required parameter.
            signature = inspect.signature(method)
            parameters = {name for name in signature.parameters if name != "self"}
            schema = config["input_schema"]
            for property_name in schema.get("properties", {}):
                self.assertIn(
                    property_name,
                    parameters,
                    f"{definition['name']}: schema property '{property_name}' "
                    f"is not a parameter of {method_name}",
                )
            for required_name in schema.get("required", []):
                self.assertIn(required_name, schema.get("properties", {}))


if __name__ == "__main__":
    unittest.main()
