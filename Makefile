
unit-test: 
	python -m unittest

type-check:
	mypy pdfsh

static-check:
	pylint pdfsh

upload:
	rm -rf build
	rm -rf dist
	python -m build
	python -m twine upload dist/*
