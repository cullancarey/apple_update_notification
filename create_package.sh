#!/bin/bash

echo "Executing create_package.sh..."

echo "Making package directory"
mkdir package

echo "Copying upload script to package directory"
cp lambda_function.py package/

echo "Copying .env file to package directory"
cp .env package/

echo "Installing requirements"
pip3 install --target ./package/ -r requirements.txt

echo "Moving to package directory"
cd package

echo "Zipping contents into deployment package"
zip -r lambda_function.zip .

echo "Moving back to main directory"
cd ..

echo "Moving deployment package to main directory"
mv package/lambda_function.zip .

echo "Removing package directory"
rm -rf package/

echo "Uploading zip file to S3..."
aws s3 cp lambda_function.zip s3://apple-update-notification-bot-bucket/

echo "Updating lambda function...!"
aws lambda update-function-code \
    --function-name  apple_update_notification_bot \
    --s3-bucket apple-update-notification-bot-bucket \
    --s3-key lambda_function.zip