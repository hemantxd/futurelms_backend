#!/bin/bash

echo "Updating zappa Application Version ..."
virtualenv venv -p python3;\
. venv/bin/activate; make install;\
zappa update development;\
make pmigrate
echo "Done!"
