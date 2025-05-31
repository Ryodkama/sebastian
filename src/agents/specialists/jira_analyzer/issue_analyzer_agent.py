import asyncio
import os

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # For creating message Content/Parts

from src.infrastructure.jira.client import JiraClient


class IssueAnalyzerAgent(LlmAgent):
    """課題分析専門エージェント"""

    def __init__(self, model: str = "gemini-2.0-flash", tools=[]):
        super().__init__(
            name="IssueAnalyzer",
            model=model,
            description="Jira課題の複雑度、緊急度、依存関係を分析する専門エージェント",
            instruction="""
あなたはJira課題分析の専門家です。課題の情報を分析して以下を評価してください：

## 分析項目
1. **複雑度スコア (1-10)**: 技術的難易度、関係者数、影響範囲を考慮
2. **緊急度スコア (1-10)**: 期限、ビジネス影響度、依存関係を考慮  
3. **推定作業時間**: 課題の内容から現実的な作業時間を推定
4. **リスクレベル**: low/medium/high で評価
5. **依存関係**: 他の課題との関連性を識別
6. **推奨アクション**: 具体的な次のステップを提案

## 課題データ
課題情報は session state の 'current_issues' キーに格納されています。
各課題について個別に分析し、結果をJSONで出力してください。

## 関数実行上の注意
- ユーザーからの入力は、関数を実行するためのトリガーとして扱います。
- 関数を呼び出す際は、引数は必要ありません。
- 関数を実行する際は確認を行う必要はありません。

## 出力形式
結果は session state の 'issue_analysis' キーに保存してください。
            """,
            output_key="issue_analysis",
            tools=tools,
        )


async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Key Concept: run_async executes the agent logic and yields Events.
    # We iterate through events to find the final answer.
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # You can uncomment the line below to see *all* events during execution
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif (
                event.actions and event.actions.escalate
            ):  # Handle potential errors/escalations
                final_response_text = (
                    f"Agent escalated: {event.error_message or 'No specific message.'}"
                )
            # Add more checks here if needed (e.g., specific error codes)
            break  # Stop processing events once the final response is found

    print(f"<<< Agent Response: {final_response_text}")


async def main():
    server_url = os.getenv("JIRA_SERVER_URL")
    username = os.getenv("JIRA_USERNAME")
    api_token = os.getenv("JIRA_API_TOKEN")
    jira = JiraClient(
        server_url,
        username,
        api_token,
    )
    jira_analyzer_agent = IssueAnalyzerAgent(tools=[jira.get_my_issues])
    print("Jira Issue Analyzer Agent initialized.")

    # Define constants for identifying the interaction context

    APP_NAME = "jira_analyzer_app"
    USER_ID = "user_1"
    SESSION_ID = "session_001"  # Using a fixed ID for simplicity

    session_service = InMemorySessionService()

    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    print(
        f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'"
    )

    # --- Runner ---

    # Key Concept: Runner orchestrates the agent execution loop.
    runner = Runner(
        agent=jira_analyzer_agent,  # The agent we want to run
        app_name=APP_NAME,  # Associates runs with our app
        session_service=session_service,  # Uses our session manager
    )

    print(f"Runner created for agent '{runner.agent.name}'.")

    await call_agent_async(
        "私の全ての課題状況を関数を実行して分析してください。関数を呼び出す際は引数は必要ありません。",
        runner=runner,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    print(session.state)


if __name__ == "__main__":
    asyncio.run(main())
