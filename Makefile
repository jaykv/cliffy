check: format lint test clean

SOURCE_FILES=cliffy tests

install:
	pip install -e .

test:
	pytest -vv --capture=tee-sys

clean:
	rm -rf build/ dist/ *.egg-info .*_cache test-builds test-manifest-builds
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python -m build

publish: package
	twine upload dist/*

format:
	ruff format --exclude=cliffy/clis ${SOURCE_FILES}
	ruff check ${SOURCE_FILES} --fix

lint:
	ruff format --check --diff ${SOURCE_FILES} --exclude=cliffy/clis
	ruff check ${SOURCE_FILES}
	mypy ${SOURCE_FILES}

shell:
	source .venv/bin/activate

generate-all:
	pip install requests "six<1.0.0" rich
	cli load examples/*.yaml
	cp cliffy/clis/*.py examples/generated/

generate-cleanup:
	pip uninstall -y requests six rich
	cli rm-all

.PHONY: test clean