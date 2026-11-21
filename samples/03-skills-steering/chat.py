"""Interactive multi-turn chat for Module 3: Skills + Steering.

The notebook runs the agent one prompt at a time (each cell is one turn). This
script wraps the same agent - with the workflow skills and both steering
handlers from the module - in a loop so you can hold a real multi-turn
conversation in the terminal.

From the cloned repo root:

    cd samples/03-skills-steering
    pip install -r requirements.txt
    python chat.py

Type 'quit', 'exit', or press Ctrl+C to stop.
"""

import os
from pathlib import Path

from strands import Agent, AgentSkills
from strands.models import BedrockModel
from customer_service_tools import lookup_customer, get_order_history, process_refund

# AWS-sponsored events / AWS credits: credits only cover Amazon Nova models, not Claude.
# To switch, pass model=BedrockModel(model_id="...") to Agent(...).
# Nova model IDs: https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-amazon.html
#   amazon.nova-micro-v1:0  — fastest, text-only, lowest cost
#   amazon.nova-lite-v1:0   — low-cost, multimodal (text, image, video)
#   amazon.nova-pro-v1:0    — balanced accuracy/speed, multimodal (recommended)
#
# Run locally without AWS credentials using Ollama (https://ollama.com/download):
#   1. Install Ollama and run: ollama pull llama3.1
#   2. pip install strands-agents[ollama]
#   3. Use OllamaModel: from strands.models import OllamaModel
#      model = OllamaModel(host="http://localhost:11434", model_id="llama3.1")
#      agent = Agent(model=model, tools=[...], plugins=[...], system_prompt=...)
#   Other models with tool support: llama3.2, qwen2.5, qwen3, mistral
from steering_handlers import DEMO_DATE, RefundWorkflowHandler, ToneGuardrailHandler

SYSTEM_PROMPT = f"""You are a customer service agent for an online electronics store.
Be helpful, professional, and concise. Use the available tools to look up customer
information and process requests. When a customer needs help, activate the appropriate
skill for step-by-step guidance.

Important guidelines:
- Always ask for the customer ID first if you don't have it.
- Use the data returned by tools to answer questions.
- Be warm but efficient.
- For the workshop return window, use the simulated date {DEMO_DATE}.
- Call process_refund only for an eligible order. The tool pauses for approval.
- If approval is denied, explain the outcome and do not retry without a new request."""


def build_agent(*, callback_handler=None):
    # One agent instance reused across turns keeps conversation history in
    # agent.messages, which is what makes the conversation multi-turn. The skills
    # and steering handlers apply on every turn.
    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        callback_handler=callback_handler,
        tools=[lookup_customer, get_order_history, process_refund],
        plugins=[
            AgentSkills(skills=[str(Path(__file__).parent / "skills")]),
            RefundWorkflowHandler(),
            ToneGuardrailHandler(),
        ],
        system_prompt=SYSTEM_PROMPT,
    )


def main():
    agent = build_agent()
    print("Customer service agent (skills + steering) - type 'quit' to exit.")
    print("Try: \"I'm customer C-1001. I want a refund for order ORD-5521.\"\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break
        if not user_input:
            continue

        result = agent(user_input)

        # A steering handler can pause a tool call for human approval (interrupt).
        # Answer each pending interrupt, then resume the agent with the responses.
        while result.stop_reason == "interrupt":
            responses = []
            for interrupt in result.interrupts:
                reason = interrupt.reason
                if isinstance(reason, dict):
                    reason = reason.get("message", reason)
                answer = input(f"\nApproval needed: {reason}\nApprove? (y/N): ")
                responses.append({
                    "interruptResponse": {
                        "interruptId": interrupt.id,
                        "response": answer.strip().lower() == "y",
                    }
                })
            result = agent(responses)
        print(f"\nAgent: {result}\n")


if __name__ == "__main__":
    main()
