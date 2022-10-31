#!/bin/bash

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir package

echo "Copying python script to package directory"
cp apple_update_notification.py package/

echo "Installing requirements"
pip install --target ./package/ -r ./requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -rq apple_update_notification.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/apple_update_notification.zip .
echo $PWD

echo "Removing package directory"
rm -rf package/