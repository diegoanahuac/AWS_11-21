"""Focused tests for the deterministic gate, independent of model output."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from strands.vended_plugins.steering import Guide, Interrupt

from steering_handlers import RefundWorkflowHandler


def tool_exchange(call_id, name, arguments, *, status="success"):
    return [
        {"role": "assistant", "content": [{"toolUse": {
            "toolUseId": call_id, "name": name, "input": arguments,
        }}]},
        {"role": "user", "content": [{"toolResult": {
            "toolUseId": call_id, "status": status, "content": [{"text": "Workshop result"}],
        }}]},
    ]


class RefundWorkflowTests(IsolatedAsyncioTestCase):
    async def check_refund(self, history, *, order_id="ORD-5521", amount=79.99):
        return await RefundWorkflowHandler().steer_before_tool(
            agent=SimpleNamespace(messages=history),
            tool_use={"name": "process_refund", "input": {"order_id": order_id, "amount": amount}},
        )

    def verified_history(self, customer_id="C-1001"):
        return tool_exchange("lookup", "lookup_customer", {"customer_id": customer_id}) + tool_exchange(
            "orders", "get_order_history", {"customer_id": customer_id},
        )

    async def test_eligible_order_pauses_for_approval(self):
        action = await self.check_refund(self.verified_history())
        self.assertIsInstance(action, Interrupt)
        self.assertIn("ORD-5521", action.reason)
        self.assertIn("79.99", action.reason)

    async def test_lookup_and_matching_order_history_are_required(self):
        self.assertIsInstance(await self.check_refund([]), Guide)
        lookup = tool_exchange("lookup", "lookup_customer", {"customer_id": "C-1001"})
        orders = tool_exchange("orders", "get_order_history", {"customer_id": "C-1002"})
        self.assertIsInstance(await self.check_refund(lookup + orders), Guide)
        self.assertIsInstance(await self.check_refund(orders + lookup), Guide)

    async def test_wrong_order_or_amount_is_blocked(self):
        history = self.verified_history()
        for order_id, amount in (("ORD-5390", 149.99), ("ORD-552", 79.99), ("ORD-5521", 7.99)):
            with self.subTest(order_id=order_id, amount=amount):
                self.assertIsInstance(await self.check_refund(history, order_id=order_id, amount=amount), Guide)

    async def test_duplicate_and_undelivered_refunds_are_blocked(self):
        history = self.verified_history()
        refunded = tool_exchange("refund", "process_refund", {"order_id": "ORD-5521", "amount": 79.99})
        self.assertIsInstance(await self.check_refund(history + refunded), Guide)
        self.assertIsInstance(await self.check_refund(history, order_id="ORD-5488", amount=45), Guide)

    async def test_unknown_customer_cannot_reuse_prior_verification(self):
        history = self.verified_history()
        unknown = tool_exchange("unknown", "lookup_customer", {"customer_id": "C-9999"})
        self.assertIsInstance(await self.check_refund(history + unknown), Guide)
