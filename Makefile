.PHONY: dev prepare update deploy

dev:
	zola build --drafts && zola serve --drafts -u localhost

prepare:
	pnpm run format

update:
	pnpm run update-projects

deploy:
	pnpm run format:check
# 	pnpm run update-projects
	COMMIT_SHA=$$(git rev-parse --short HEAD) zola build
	pnpm run deploy
