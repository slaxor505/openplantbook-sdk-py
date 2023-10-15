#!/bin/bash

python3 -m unittest tests/test_openplantbook_sdk.py && python3 -m build && twine check dist/* && twine upload dist/*
