.PHONY: dev prepare update

dev:
	zola build --drafts && zola serve --drafts -u localhost

prepare:
	pnpm run format

update:
	pnpm run update-projects
