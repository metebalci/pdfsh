
unit-test: 
	python -m unittest

type-check:
	mypy pdfsh

run-checks:
	black --check pdfsh
	pylint pdfsh

upload:
	rm -rf build
	rm -rf dist
	python -m build
	python -m twine upload dist/*
