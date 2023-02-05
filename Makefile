check: lint test

SOURCE_FILES=commandeer

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
	autoflake --in-place --recursive --remove-all-unused-imports --ignore-init-module-imports ${SOURCE_FILES} --exclude=commandeer/clis
	isort --project=commandeer ${SOURCE_FILES} --skip=commandeer/clis
	black ${SOURCE_FILES} --exclude=commandeer/clis

lint:
	isort --check --diff --project=commandeer ${SOURCE_FILES} --skip=commandeer/clis
	black --check --diff ${SOURCE_FILES} --exclude=commandeer/clis
	flake8 $(SOURCE_FILES) --count --show-source --statistics --exclude=commandeer/clis
	flake8 $(SOURCE_FILES) --count --exit-zero --statistics --exclude=commandeer/clis

shell:
	source $(poetry env info --path)/bin/activate

.PHONY: test clean