#!/bin/bash

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir package

echo "Copying python script to package directory"
cp lambdas/apple_utils.py package/

echo "Installing requirements"
pip install --target ./package/ -r ./requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -rq apple_utils.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/apple_utils.zip .
echo $PWD

echo "Removing package directory"
rm -rf package/
