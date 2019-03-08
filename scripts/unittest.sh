#!/bin/bash

rm junit.xml
rm  pylint.out
rm -rf localconfig
wget ftp://172.16.10.107/pub/build_for_test/nebula_resources_`cat unittests/nebula_resources_tag`.tar.gz
mkdir nebula_website/localconfig
tar xzf nebula_resources_`cat unittests/nebula_resources_tag`.tar.gz config/web/*
mv config/web/* nebula_website/localconfig/
rm nebula_resources_`cat unittests/nebula_resources_tag`.tar.gz

venv/bin/python -m py.test --cov=nebula_website --cov-report=term-missing --cov-report=xml --junitxml junit.xml unittests
venv/bin/pylint --rcfile=pylint.rc -f parseable nebula_website | tee pylint.out

rm -rf unittests/__pycache__
