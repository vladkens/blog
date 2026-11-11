.PHONY: prepare check test build update clean

# `brew install oxfmt`, or override it as CI does: make check OXFMT="npx --yes oxfmt@0.76.0"
OXFMT ?= oxfmt

prepare:
	$(OXFMT)

check:
	$(OXFMT) --check
	uvx ruff check .

test: build
	uv run python scripts/check-rhythm.py

build:
	uv run python src/freeze.py

update:
	uv run python scripts/update-projects.py
	$(MAKE) prepare

clean:
	rm -rf public src/__pycache__

.PHONY: dev deploy

dev: # run the Flask debug server on localhost
	uv run flask --app src/app run --debug --host 127.0.0.1 --port 1111

deploy: check test # check, test, build and upload public/
	COMMIT_SHA=$$(git rev-parse --short HEAD) uv run python src/freeze.py
	npx --yes wrangler@4.131.0 pages deploy public --project-name=blog
