check: format lint test clean

SOURCE_FILES=cliffy tests

install:
	pip install -e .

test:
	pytest -vv -rs

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python -m build

publish: package
	twine upload dist/*

format:
	autoflake --in-place --recursive --remove-all-unused-imports --ignore-init-module-imports ${SOURCE_FILES} --exclude=cliffy/clis
	isort --project=cliffy ${SOURCE_FILES} --skip=cliffy/clis
	black ${SOURCE_FILES} --exclude=cliffy/clis
	ruff ${SOURCE_FILES} --fix

lint:
	isort --check --diff --project=cliffy ${SOURCE_FILES} --skip=cliffy/clis
	black --check --diff ${SOURCE_FILES} --exclude=cliffy/clis
	ruff $(SOURCE_FILES)

shell:
	source .venv/bin/activate

generate-all:
	pip install requests six rich
	cli load examples/*.yaml

generate-cleanup:
	pip uninstall -y requests six rich
	cli rm db environ hello pydev requires template town venv

.PHONY: test clean