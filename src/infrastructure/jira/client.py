#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests


class JiraClient:
    """Jira API クライアント"""

    def __init__(self, server_url: str, username: str, api_token: str):
        """
        Jiraクライアントを初期化

        Args:
            server_url: JiraサーバーのURL (例: https://yourcompany.atlassian.net)
            username: Jiraのユーザー名（メールアドレス）
            api_token: JiraのAPIトークン
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.session = requests.Session()

        # Basic認証のヘッダーを設定
        auth_string = f"{username}:{api_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        self.session.headers.update(
            {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def test_connection(self) -> bool:
        """
        Jiraへの接続テスト

        Returns:
            bool: 接続が成功した場合True
        """
        try:
            response = self.session.get(f"{self.server_url}/rest/api/3/myself")
            print(f"接続テストステータスコード: {response.status_code}")
            if response.status_code == 401:
                print("認証エラー: ユーザー名またはAPIトークンが正しくありません。")
                return False
            elif response.status_code == 404:
                print("URLが正しくありません。JiraサーバーのURLを確認してください。")
                return False
            elif response.status_code != 200:
                print(f"接続に失敗しました。ステータスコード: {response.status_code}")
                return False
            print("接続に成功しました。")
            return response.status_code == 200
        except Exception as e:
            print(f"接続エラー: {e}")
            return False

    def get_my_issues(
        self,
        status_filter: Optional[List[str]] = None,
        project_keys: Optional[List[str]] = None,
        max_results: int = 50,
    ) -> List[Dict]:
        """
        自分にアサインされた課題を取得

        Args:
            status_filter: ステータスでフィルタ（例: ["To Do", "In Progress"]）
            project_keys: プロジェクトキーでフィルタ（例: ["PROJ1", "PROJ2"]）
            max_results: 最大取得件数

        Returns:
            List[Dict]: 課題のリスト
        """
        # JQLクエリを構築
        jql_parts = ["assignee = currentUser()"]

        if status_filter:
            status_list = "', '".join(status_filter)
            jql_parts.append(f"status IN ('{status_list}')")

        if project_keys:
            project_list = "', '".join(project_keys)
            jql_parts.append(f"project IN ('{project_list}')")

        jql = " AND ".join(jql_parts)
        jql += " ORDER BY created DESC"

        return self._search_issues(jql, max_results)

    def get_reported_by_me(
        self, status_filter: Optional[List[str]] = None, max_results: int = 50
    ) -> List[Dict]:
        """
        自分が報告した課題を取得

        Args:
            status_filter: ステータスでフィルタ
            max_results: 最大取得件数

        Returns:
            List[Dict]: 課題のリスト
        """
        jql_parts = ["reporter = currentUser()"]

        if status_filter:
            status_list = "', '".join(status_filter)
            jql_parts.append(f"status IN ('{status_list}')")

        jql = " AND ".join(jql_parts)
        jql += " ORDER BY created DESC"

        return self._search_issues(jql, max_results)

    def get_recent_activity(self, days: int = 7, max_results: int = 50) -> List[Dict]:
        """
        最近更新された自分の課題を取得

        Args:
            days: 何日前からの課題を取得するか
            max_results: 最大取得件数

        Returns:
            List[Dict]: 課題のリスト
        """
        jql = f"(assignee = currentUser() OR reporter = currentUser()) AND updated >= -{days}d ORDER BY updated DESC"
        return self._search_issues(jql, max_results)

    def _search_issues(self, jql: str, max_results: int) -> List[Dict]:
        """
        JQLクエリで課題を検索

        Args:
            jql: JQLクエリ文字列
            max_results: 最大取得件数

        Returns:
            List[Dict]: 課題のリスト
        """
        url = f"{self.server_url}/rest/api/3/search"

        payload = {
            "jql": jql,
            "maxResults": max_results,
            "fields": [
                "summary",
                "status",
                "assignee",
                "reporter",
                "priority",
                "created",
                "updated",
                "duedate",
                "project",
                "issuetype",
            ],
        }

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            return self._format_issues(data.get("issues", []))

        except requests.RequestException as e:
            print(f"API リクエストエラー: {e}")
            return []

    def _format_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        課題データを整形

        Args:
            issues: Jira APIからの生の課題データ

        Returns:
            List[Dict]: 整形された課題データ
        """
        formatted_issues = []

        for issue in issues:
            fields = issue.get("fields", {})

            formatted_issue = {
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "assignee": self._get_user_display_name(fields.get("assignee")),
                "reporter": self._get_user_display_name(fields.get("reporter")),
                "project": fields.get("project", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "created": self._format_date(fields.get("created")),
                "updated": self._format_date(fields.get("updated")),
                "due_date": self._format_date(fields.get("duedate")),
                "url": f"{self.server_url}/browse/{issue.get('key')}",
            }

            formatted_issues.append(formatted_issue)

        return formatted_issues

    def _get_user_display_name(self, user_data: Optional[Dict]) -> str:
        """ユーザー表示名を取得"""
        if not user_data:
            return "未設定"
        return user_data.get("displayName", user_data.get("emailAddress", "不明"))

    def _format_date(self, date_str: Optional[str]) -> str:
        """日付文字列を整形"""
        if not date_str:
            return ""

        try:
            # ISO形式の日付をパース
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return date_str

    def print_issues(self, issues: List[Dict]) -> None:
        """
        課題を整形して表示

        Args:
            issues: 課題のリスト
        """
        if not issues:
            print("課題が見つかりませんでした。")
            return

        print(f"\n--- 取得した課題 ({len(issues)}件) ---")

        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. [{issue['key']}] {issue['summary']}")
            print(f"   ステータス: {issue['status']}")
            print(f"   優先度: {issue['priority']}")
            print(f"   担当者: {issue['assignee']}")
            print(f"   プロジェクト: {issue['project']}")
            print(f"   作成日: {issue['created']}")
            print(f"   更新日: {issue['updated']}")
            if issue["due_date"]:
                print(f"   期限: {issue['due_date']}")
            print(f"   URL: {issue['url']}")


def main():
    """メイン実行関数"""

    # 環境変数から設定を読み込み（推奨）
    server_url = os.getenv("JIRA_SERVER_URL")
    username = os.getenv("JIRA_USERNAME")
    api_token = os.getenv("JIRA_API_TOKEN")

    # 環境変数が設定されていない場合は入力を求める
    if not all([server_url, username, api_token]):
        print("Jira接続情報を入力してください:")
        server_url = server_url or input("JiraサーバーURL: ")
        username = username or input("ユーザー名（メールアドレス）: ")
        api_token = api_token or input("APIトークン: ")

    # Jiraクライアントを初期化
    client = JiraClient(server_url, username, api_token)

    # 接続テスト
    print("Jiraへの接続をテスト中...")
    if not client.test_connection():
        print("Jiraへの接続に失敗しました。設定を確認してください。")
        return

    print("接続に成功しました！")

    while True:
        print("\n--- Jira課題取得メニュー ---")
        print("1. 自分にアサインされた課題")
        print("2. 自分が報告した課題")
        print("3. 最近の活動（過去7日）")
        print("4. カスタム検索（進行中の課題のみ）")
        print("5. 終了")

        choice = input("\n選択してください (1-5): ")

        try:
            if choice == "1":
                issues = client.get_my_issues()
                client.print_issues(issues)

            elif choice == "2":
                issues = client.get_reported_by_me()
                client.print_issues(issues)

            elif choice == "3":
                issues = client.get_recent_activity()
                client.print_issues(issues)

            elif choice == "4":
                # 進行中の課題のみ取得
                issues = client.get_my_issues(
                    status_filter=["To Do", "In Progress", "In Review"]
                )
                client.print_issues(issues)

            elif choice == "5":
                print("終了します。")
                break

            else:
                print("無効な選択です。")

        except KeyboardInterrupt:
            print("\n\n操作がキャンセルされました。")
            break
        except Exception as e:
            print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
