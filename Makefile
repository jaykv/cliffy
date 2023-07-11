check: format lint test clean

SOURCE_FILES=cliffy tests

install:
	pip install -e .

test:
	pytest -vv --capture=tee-sys

clean:
	rm -rf build/ dist/ *.egg-info .*_cache
	find . -name '*.pyc' -type f -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +

package: clean
	python -m build

publish: package
	twine upload dist/*

format:
	black ${SOURCE_FILES} --exclude=cliffy/clis
	ruff ${SOURCE_FILES} --fix

lint:
	black --check --diff ${SOURCE_FILES} --exclude=cliffy/clis
	ruff ${SOURCE_FILES}
	mypy ${SOURCE_FILES}

shell:
	source .venv/bin/activate

generate-all:
	pip install requests six rich
	cli load examples/*.yaml

generate-cleanup:
	pip uninstall -y requests six rich
	cli rm db environ hello pydev requires template town penv

.PHONY: test clean