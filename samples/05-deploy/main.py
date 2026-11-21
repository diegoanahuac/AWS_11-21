"""AgentCore entrypoint for the workshop support agent."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, AgentSkills
from strands.models import BedrockModel

from customer_service_tools import get_order_history, lookup_customer, process_refund
from steering_handlers import DEMO_DATE, RefundWorkflowHandler, ToneGuardrailHandler

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = f"""You are an electronics store's customer service agent.
Use the available tools and workflow skills. Verify the customer and order before
requesting a refund. This workshop uses the simulated business date {DEMO_DATE}.
Explain a refund outcome using the tool result. If approval is denied, do not
retry without a new request. Be concise, professional, and empathetic."""


@dataclass
class RuntimeSession:
    agent: Agent
    pending: dict = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)


_sessions = {}
_sessions_lock = Lock()


def build_agent():
    return Agent(
        model=BedrockModel(
            model_id=os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        ),
        tools=[lookup_customer, get_order_history, process_refund],
        plugins=[
            AgentSkills(skills=[str(Path(__file__).parent / "skills")]),
            RefundWorkflowHandler(),
            ToneGuardrailHandler(),
        ],
        system_prompt=SYSTEM_PROMPT,
        context_manager="auto",
        callback_handler=None,
    )


def get_session(session_id):
    if session_id is None:
        return RuntimeSession(build_agent())
    with _sessions_lock:
        if session_id not in _sessions:
            _sessions[session_id] = RuntimeSession(build_agent())
        return _sessions[session_id]


def interrupt_response(session):
    return {"status": "interrupted", "interrupts": list(session.pending.values())}


@app.entrypoint
def invoke(payload, context):
    session = get_session(getattr(context, "session_id", None))
    with session.lock:
        responses = payload.get("interrupt_responses")
        if responses is not None:
            if not isinstance(responses, list) or not responses or not all(
                isinstance(response, dict)
                and isinstance(response.get("interruptId"), str)
                and isinstance(response.get("response"), bool)
                for response in responses
            ):
                raise ValueError("Provide a list of interrupt IDs and boolean responses.")
            ids = {response["interruptId"] for response in responses}
            if ids != session.pending.keys() or len(ids) != len(responses):
                raise ValueError("Answer each pending approval once in the same session.")
            result = session.agent([{"interruptResponse": response} for response in responses])
        elif session.pending:
            return interrupt_response(session)
        else:
            prompt = payload.get("prompt")
            if isinstance(prompt, str):
                try:
                    parsed = json.loads(prompt)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(parsed, dict):
                        prompt = parsed.get("prompt", prompt)
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Provide a non-empty prompt.")
            result = session.agent(prompt)

        session.pending = {
            interrupt.id: {
                "interruptId": interrupt.id,
                "name": interrupt.name,
                "reason": interrupt.reason,
            }
            for interrupt in result.interrupts
        } if result.stop_reason == "interrupt" else {}
        return interrupt_response(session) if session.pending else str(result).strip()


if __name__ == "__main__":
    app.run()
