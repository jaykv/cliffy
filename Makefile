check: format lint test clean

SOURCE_FILES=cliffy tests

install:
	uv sync --frozen --all-extras --group dev --group docs

sync:
	uv sync --all-extras --group dev --group docs

test:
	uv run pytest --cov --cov-config=pyproject.toml -vv --capture=tee-sys -n auto

test-cov:
	uv run pytest --cov --cov-config=pyproject.toml --cov-branch --cov-report=xml -vv --capture=tee-sys -n auto

clean:
	rm -rf build/ dist/ *.egg-info .*_cache test-builds test-manifest-builds
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	uv build

publish: package
	uv publish

format:
	uv run ruff format --exclude=cliffy/clis ${SOURCE_FILES}
	uv run ruff check ${SOURCE_FILES} --fix

lint:
	uv run ruff format --check --diff ${SOURCE_FILES} --exclude=cliffy/clis
	uv run ruff check ${SOURCE_FILES}
	uv run mypy cliffy --strict
	uv run mypy tests

docs-serve:
	uv run mkdocs serve

shell:
	source .venv/bin/activate

generate-clis: 
	pip install requests "six<1.0.0" rich keyring
	cli load examples/*.yaml
	cp cliffy/clis/*.py examples/generated/

generate-all: generate-clis generate-schema generate-cleanup
	@echo "~ done"

generate-cleanup:
	pip uninstall -y requests six rich keyring
	cli rm-all

generate-schema:
	python -m cliffy.manifest --json-schema > examples/cliffy_schema.json

.PHONY: test clean