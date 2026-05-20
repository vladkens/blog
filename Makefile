.PHONY: dev prepare update

dev:
	zola build && zola serve -u localhost

prepare:
	pnpm run format

update:
	pnpm run update-projects
