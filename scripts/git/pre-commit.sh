#!/bin/bash

# コミットされる変更された Python ファイルのみを取得
files=$(git diff --cached --name-only --diff-filter=ACMR | grep '\.py$')

# 変更された Python ファイルがない場合は終了
if [[ -z "$files" ]]; then
    exit 0
fi

echo "Running Ruff checks on staged files..."

# Ruff を実行してフォーマットチェック
ruff_output=$(echo "$files" | xargs ruff check --force-exclude 2>&1 --config pyproject.toml)

# エラーがない場合のみ表示を変更
if [[ "$ruff_output" == *"All checks passed!"* ]]; then
  echo "All checks passed!"
else
  echo "$ruff_output"
  echo "Ruff found issues in the following files:"
  
  # エラーがあった場合、コミットを中止
  echo "Aborting commit due to issues found in the code."
  exit 1
fi