SOURCE_FILES=cliffy tests

check: format lint test clean

install:
	uv sync --frozen --all-extras --group docs

sync:
	uv sync --all-extras --group docs

test:
	uv run pytest --cov --cov-config=pyproject.toml -vv --capture=tee-sys -n auto

test-cov:
	uv run pytest --cov --cov-config=pyproject.toml --cov-branch --cov-report=xml -vv --capture=tee-sys -n auto

clean:
	rm -rf build/ dist/ site/ *.egg-info .*_cache coverage.xml test-builds test-manifest-builds test-manifest-builds-response
	find . -name '*.pyc' -type f -not -path './.venv/*' -exec rm -f {} +
	find . -name '__pycache__' -not -path './.venv/*' -prune -exec rm -rf {} +

package: clean
	uv build

publish: package
	uv publish

format:
	uv run ruff format ${SOURCE_FILES}
	uv run ruff check ${SOURCE_FILES} --fix

lint:
	uv run ruff format --check --diff ${SOURCE_FILES}
	uv run ruff check ${SOURCE_FILES}
	uv run mypy cliffy --strict
	uv run mypy tests

docs-serve:
	uv run --group docs mkdocs serve

# docs/reference/*.md are generated from the click commands, the manifest models and examples/.
docs-generate:
	uv run python scripts/docs.py generate

# Fails when the generated pages are stale or a manifest in docs/snippets does not pass its tests.
docs-check:
	uv run python scripts/docs.py check

docs-build: docs-check
	uv run --group docs mkdocs build --strict

# examples/generated/*.py are what cliffy generates for the manifests in examples/. Nothing is installed or
# loaded for this: the manifests are only rendered. tests/test_examples.py fails when a file is stale.
generate-clis:
	uv run python scripts/examples.py

generate-all: generate-clis generate-schema
	@echo "~ done"

generate-schema:
	uv run python -m cliffy.manifest --json-schema > examples/cliffy_schema.json

.PHONY: check install sync test test-cov clean package publish format lint \
	docs-serve docs-generate docs-check docs-build \
	generate-clis generate-all generate-schema
