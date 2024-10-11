
unit-test: 
	python -m unittest

type-check:
	mypy pdfsh

static-check:
	pylint pdfsh

upload:
	rm -rf dist
	python setup.py sdist
	twine upload dist/*
