#!/bin/bash


echo "----------------------"
echo "Setting up the git"
echo "----------------------"

# gitのコミットメッセージのテンプレートを設定
echo "Setting commit template..."
git config --local commit.template ./scripts/git/.commit_template

echo "Copying pre-commit hook..."
cp scripts/git/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "Copying prepare-commit-msg hook..."
cp scripts/git/prepare-commit-message.sh .git/hooks/prepare-commit-msg
chmod +x .git/hooks/prepare-commit-msg

echo "Git hooks copied and made executable!"

echo "----------------------"
echo "git Setup is complete!"
echo "----------------------"
