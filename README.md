# scrapWind

** How to run it **
virtualenv env
source env/bin/activate

Install all needed packages:
pip install -r requirements.txt

Before you check in your code run:
remove all security and credentials information from config.yaml
pip freeze > requirements.txt
and have those lines in .gitignore:
*.pyc
*.zip
env/

Inactivate the virtualenv with command:
deactivate

** Run it as Lambda on AWS **
Sign up with AWS and create an account with Access Key.
Create IAM role. I named it Lambda1. Copy its ARN and use it when you create the lambda function.
aws configure      # Learn more: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html 

bash deployLambda.sh scrapWind

aws lambda create-function --region eu-west-1 --function-name scrapWind --zip-file fileb:///home/ec2-user/Code/scrapWind/scrapWind.zip --role arn:aws:iam::510136466810:role/Lambda1 --handler  scrapWind.lambda_handler --runtime python2.7 --timeout 300

After the lambda is created you can updated like:
bash deployLambda.sh scrapWind

Create a scheduler as in step 2 in http://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html with 

Now the AWS CloudWatch rule scheduler will trigger the lambda script 

