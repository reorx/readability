.PHONY: clean test

clean:
	rm -rf build *.egg-info

test:
	PYTHONPATH=. nosetests -w test/ -v

build:
	python setup.py build
