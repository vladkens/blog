.PHONY: dev prepare update deploy

dev:
	zola build --drafts && zola serve --drafts -u localhost

prepare:
	pnpm run format

update:
	node scripts/stats-at-glance.mjs
	node scripts/update-projects.mjs
	$(MAKE) prepare

deploy:
	pnpm run format:check
# 	pnpm run update-projects
	COMMIT_SHA=$$(git rev-parse --short HEAD) zola build
	pnpm run deploy
