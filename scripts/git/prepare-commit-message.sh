#!/bin/bash

# 現在のブランチ名を取得
branch=$(git rev-parse --abbrev-ref HEAD)

# "feature/BIBLO-1234" や "feature/BIBLO-1234.text" から "NB-1234" を抽出
issue_number=$(echo "$branch" | grep -oE '[A-Z]+-[0-9]+')

# {branch} を issue_number に置換
perl -i.bak -ne "s/{branch}/$issue_number/g; print" "$1"
