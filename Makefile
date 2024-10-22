dev:
	zola build && zola serve -u localhost

update:
	python projects_update.py
