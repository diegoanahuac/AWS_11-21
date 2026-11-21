"""Exercise the runtime HTTP contract without spending Bedrock inference."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from bedrock_agentcore.runtime.models import SESSION_HEADER
from httpx import ASGITransport, AsyncClient

import main


class StubAgent:
    def __call__(self, payload):
        if payload == "start refund":
            request = SimpleNamespace(id="refund-1", name="process_refund", reason={"message": "Approve?"})
            return SimpleNamespace(stop_reason="interrupt", interrupts=[request])
        if isinstance(payload, list):
            approved = payload[0]["interruptResponse"]["response"]
            return StubReply("refund approved" if approved else "refund denied")
        return StubReply(f"reply to {payload}")


class StubReply:
    stop_reason = "end_turn"

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class RuntimeTests(IsolatedAsyncioTestCase):
    async def test_pending_approval_is_isolated_and_can_be_denied(self):
        first = {SESSION_HEADER: "workshop-session-aaaaaaaaaaaaaaaaaaaaaaa"}
        second = {SESSION_HEADER: "workshop-session-bbbbbbbbbbbbbbbbbbbbbbb"}
        with patch.object(main, "_sessions", {}), patch.object(main, "build_agent", side_effect=StubAgent):
            async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
                reply = await client.post("/invocations", headers=first, json={"prompt": "start refund"})
                self.assertEqual(reply.json()["status"], "interrupted")

                reply = await client.post("/invocations", headers=first, json={"prompt": "another prompt"})
                self.assertEqual(reply.json()["interrupts"][0]["interruptId"], "refund-1")

                reply = await client.post("/invocations", headers=second, json={"prompt": "hello"})
                self.assertEqual(reply.status_code, 200)
                self.assertIn("reply to hello", reply.text)

                reply = await client.post("/invocations", headers=first, json={
                    "interrupt_responses": [{"interruptId": "refund-1", "response": False}],
                })
                self.assertEqual(reply.status_code, 200)
                self.assertIn("refund denied", reply.text)
