all:    publish

clean:
	rm -rf build/ dist/ *.egg-info/

publish:
	python setup.py sdist register upload
