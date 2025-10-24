#!/bin/bash

python3 -m unittest discover -s tests -p "test_*.py" && python3 -m build && twine check dist/* && twine upload dist/*
