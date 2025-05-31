.PHONY: setup
setup: 
	make git-setup

.PHONY: git-setup
git-setup:
	@echo "Setting up Git hooks..."
	./scripts/git/setup-git-hooks.sh