dev:
	zola build && zola serve -u localhost

update:
	python _projects_update.py
