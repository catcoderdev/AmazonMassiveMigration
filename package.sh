rm -rf package
mkdir package
pip install -r requirements.txt -t package/
rm -rf lambda_function.zip
cp *.py package/
cp -r App package
cd package
zip -r ../lambda_function.zip .
cd ..
aws lambda update-function-code --function-name shopifyPull --zip-file fileb://lambda_function.zip >> /tmp/null