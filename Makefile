
unit-test: 
	python -m unittest

type-check:
	mypy pdfls

static-check:
	pylint pdfls

upload:
	rm -rf dist
	python setup.py sdist
	twine upload dist/*
