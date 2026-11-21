"""Run the Module 1 customer-service scenario and show the tool calls."""

import os

from strands import Agent
from strands.models import BedrockModel

from chat import SYSTEM_PROMPT
from customer_service_tools import get_order_history, lookup_customer, process_refund


SCENARIO = (
    (
        "I am customer C-1001. Please verify my account and list my recent orders.",
        {"lookup_customer", "get_order_history"},
    ),
    (
        "Please issue a full simulated refund for the wireless headphones in my orders.",
        {"process_refund"},
    ),
)


def main() -> None:
    model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
    agent = Agent(
        model=BedrockModel(model_id=model_id, region_name="us-east-1"),
        system_prompt=SYSTEM_PROMPT,
        tools=[lookup_customer, get_order_history, process_refund],
        callback_handler=None,
    )
    print(f"Bedrock model: {model_id}", flush=True)

    for prompt, expected_tools in SCENARIO:
        print(f"\nCustomer: {prompt}", flush=True)
        start = len(agent.messages)
        result = agent(prompt)
        blocks = [
            block
            for message in agent.messages[start:]
            for block in message["content"]
        ]
        calls = [block["toolUse"] for block in blocks if "toolUse" in block]
        results = {
            block["toolResult"]["toolUseId"]: block["toolResult"]["status"]
            for block in blocks
            if "toolResult" in block
        }
        for call in calls:
            status = results.get(call["toolUseId"], "missing result")
            print(f"Tool: {call['name']} ({status})")
        print(f"Agent: {result}")

        successful_tools = {
            call["name"] for call in calls if results.get(call["toolUseId"]) == "success"
        }
        missing = expected_tools - successful_tools
        if missing:
            raise SystemExit(f"Expected successful tool calls: {', '.join(sorted(missing))}")
        if "process_refund" in expected_tools and not any(
            call["name"] == "process_refund"
            and call["input"] == {"order_id": "ORD-5521", "amount": 79.99}
            and results.get(call["toolUseId"]) == "success"
            for call in calls
        ):
            raise SystemExit("Expected a successful simulated refund of $79.99 for ORD-5521.")

    print("\nModule 1 scenario passed.")


if __name__ == "__main__":
    main()
