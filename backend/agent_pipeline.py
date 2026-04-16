import os
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Literal

from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle
from browser_use.browser.profile import BrowserProfile

load_dotenv()


class ParsedQuery(BaseModel):
    intent: str = Field(description="One of: CREATE_USER, TOGGLE_STATUS, DELETE_USER, VIEW_DATA")
    email: str | None = Field(default=None, description="User email address if present")
    name: str | None = Field(default=None, description="Full name for create user requests")
    role: str | None = Field(default=None, description="User role for create user requests")
    department: str | None = Field(default=None, description="Department for create user requests")
    status: str | None = Field(default=None, description="activate or deactivate for status changes")


class PlanStep(BaseModel):
    action: str
    description: str
    expected_result: str


class Plan(BaseModel):
    intent: str
    needs_approval: bool = False
    steps: list[PlanStep]


@dataclass
class VerificationResult:
    ok: bool
    message: str
    should_retry: bool = False


def parse_query(query: str) -> ParsedQuery:
    client = OpenAI(
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url="https://models.github.ai/inference",
    )

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the IT admin intent and relevant fields from the user request. "
                    "Return only the structured data fields specified."
                ),
            },
            {"role": "user", "content": query},
        ],
        response_format=ParsedQuery,
    )

    return response.choices[0].message.parsed


def build_plan(parsed: ParsedQuery) -> Plan:
    if parsed.intent == "CREATE_USER":
        return Plan(
            intent=parsed.intent,
            needs_approval=False,
            steps=[
                PlanStep(
                    action="navigate",
                    description="Open the admin panel and go to the New User page",
                    expected_result="New user form is visible",
                ),
                PlanStep(
                    action="fill_form",
                    description=f"Fill full name, email, role, and department for {parsed.email}",
                    expected_result="All fields are populated",
                ),
                PlanStep(
                    action="submit",
                    description="Submit the new user form",
                    expected_result="Success message appears",
                ),
            ],
        )

    if parsed.intent == "TOGGLE_STATUS":
        return Plan(
            intent=parsed.intent,
            needs_approval=False,
            steps=[
                PlanStep(
                    action="navigate",
                    description="Open the user list page",
                    expected_result="User list is visible",
                ),
                PlanStep(
                    action="locate_user",
                    description=f"Find the row for {parsed.email}",
                    expected_result="Target user row is visible",
                ),
                PlanStep(
                    action="toggle_status",
                    description=f"Change status to {'active' if parsed.status == 'activate' else 'inactive'}",
                    expected_result="Status badge updates",
                ),
            ],
        )

    if parsed.intent == "DELETE_USER":
        return Plan(
            intent=parsed.intent,
            needs_approval=True,
            steps=[
                PlanStep(
                    action="navigate",
                    description="Open the user list page",
                    expected_result="User list is visible",
                ),
                PlanStep(
                    action="locate_user",
                    description=f"Find the row for {parsed.email}",
                    expected_result="Target user row is visible",
                ),
                PlanStep(
                    action="delete",
                    description=f"Delete the account for {parsed.email}",
                    expected_result="User no longer appears in the table",
                ),
            ],
        )

    return Plan(
        intent=parsed.intent,
        needs_approval=False,
        steps=[
            PlanStep(
                action="navigate",
                description="Open the admin dashboard",
                expected_result="Dashboard is visible",
            )
        ],
    )


def verify_result(result_text: str, plan: Plan) -> VerificationResult:
    text = result_text.lower()

    if plan.intent == "CREATE_USER":
        if "success" in text or "created" in text:
            return VerificationResult(True, "User creation verified")
        return VerificationResult(False, "Creation not confirmed", should_retry=True)

    if plan.intent == "TOGGLE_STATUS":
        if "active" in text or "inactive" in text or "updated" in text:
            return VerificationResult(True, "Status change verified")
        return VerificationResult(False, "Status change not confirmed", should_retry=True)

    if plan.intent == "DELETE_USER":
        if "deleted" in text or "removed" in text:
            return VerificationResult(True, "Deletion verified")
        return VerificationResult(False, "Deletion not confirmed", should_retry=True)

    return VerificationResult(True, "No strict verification required")


async def execute_plan(plan: Plan) -> str:
    task_lines = []
    task_lines.append("Open the IT admin panel at http://localhost:3000.")
    task_lines.append("Follow these steps carefully:")
    for index, step in enumerate(plan.steps, start=1):
        task_lines.append(f"{index}. {step.description}")
        task_lines.append(f"   Expected result: {step.expected_result}")
    task_lines.append("Report the final outcome clearly.")

    task = "\n".join(task_lines)

    llm = ChatGoogle(
        model="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    browser_profile = BrowserProfile(headless=False)

    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=browser_profile,
    )

    result = await agent.run()
    return str(result)


async def handle_support_request(request_text: str) -> dict:
    parsed = parse_query(request_text)
    plan = build_plan(parsed)

    if plan.needs_approval:
        approval = input(f"Approval required for {plan.intent}. Type yes to continue: ").strip().lower()
        if approval != "yes":
            return {
                "intent": plan.intent,
                "query": request_text,
                "plan": plan.model_dump(),
                "status": "cancelled",
                "result": "User did not approve the action",
            }

    result_text = await execute_plan(plan)
    verification = verify_result(result_text, plan)

    if not verification.ok and verification.should_retry:
        retry_text = await execute_plan(plan)
        verification = verify_result(retry_text, plan)
        result_text = retry_text

    return {
        "intent": plan.intent,
        "query": request_text,
        "plan": plan.model_dump(),
        "verified": verification.ok,
        "verification_message": verification.message,
        "status": "completed" if verification.ok else "needs_review",
        "result": result_text,
    }


async def main():
    while True:
        query = input("You: ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue

        try:
            result = await handle_support_request(query)
            print(f"Bot: {result['status']}")
            print(f"Bot: {result['verification_message']}")
            print(f"Bot: {str(result['result'])[:200]}")
        except Exception as e:
            print(f"Bot: Error - {e}")


if __name__ == "__main__":
    asyncio.run(main())