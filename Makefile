SOURCE_FILES=cliffy tests
GENERATE_DEPS=requests "six<1.0.0" keyring

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

# The example manifests declare requirements that are not cliffy dependencies. They have to be
# installed into the project environment (not a `uv run --with` overlay), because cliffy validates
# `requires` against `pip freeze`. `uv sync` in generate-cleanup removes them again.
generate-clis:
	uv pip install ${GENERATE_DEPS}
	uv run --no-sync cli load examples/*.yaml
	cp cliffy/clis/*.py examples/generated/

generate-all: generate-clis generate-schema generate-cleanup
	@echo "~ done"

generate-cleanup:
	uv run --no-sync cli rm-all
	uv sync --all-extras --group docs

generate-schema:
	uv run python -m cliffy.manifest --json-schema > examples/cliffy_schema.json

.PHONY: check install sync test test-cov clean package publish format lint docs-serve \
	generate-clis generate-all generate-cleanup generate-schema
