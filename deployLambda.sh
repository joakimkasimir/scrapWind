#!/bin/bash

if [ -z ${VIRTUAL_ENV+x} ]; then
	echo "No Python virtual environment set (VIRTUAL_ENV)"
	exit 1
fi

# Create temp directory
tempDir=$(mktemp -d) && cd ${tempDir}

# Copy files to temp directory
cp ${VIRTUAL_ENV}/../${1}.py ${tempDir}
cp ${VIRTUAL_ENV}/../config.yaml ${tempDir}
cp -r ${VIRTUAL_ENV}/lib/python2.7/site-packages/* ${tempDir}
cp -r ${VIRTUAL_ENV}/lib64/python2.7/site-packages/* ${tempDir}
rm -rf ${tempDir}/pip*
rm -rf ${tempDir}/pkg_resources
rm -rf ${tempDir}/setuptools*
rm -rf ${tempDir}/_markerlib
rm -rf ${tempDir}/easy_install.py*

# zip all files in temp directory
zip -r ${VIRTUAL_ENV}/../${1}.zip *

cd ${VIRTUAL_ENV}/.. && rm -r ${tempDir}

aws lambda update-function-code --function-name ${1} --zip-file fileb://./${1}.zip
