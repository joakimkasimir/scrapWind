# scrapWind
This is a simple scraping scripng used for show a 24 hour timeserie of data in http://seadog.ddns.net:800/rapporter/BSS.htm and it will show up on https://app.ubidots.com/ubi/public/getdashboard/page/kgHXr7swwIDPf0JdIYW_iOltvb4/#/ 

It also gets sea level from SMHI open data api: http://opendata-catalog.smhi.se/explore/ 

## Preparations ##
Create an account on https://www.ubidots.com and create a source. Edit config.yaml and add source and token for the account.

## How to run it ##
Activate Python virtual Environment: 
```bash
virtualenv env
source env/bin/activate
```

Install all needed packagesi and run the code:
```bash
pip install -r requirements.txt
python scrapWind.py
```
Inactivate the virtualenv with command:
```bash
deactivate
```
## Check in the code ##
Remove all security and credentials information from config.yaml
Before you check in your code run:
```bash
git restore config.yaml
pip freeze > requirements.txt
```

and have those lines in .gitignore:
*.pyc
*.zip
env/

## Run it as Lambda on AWS ##
Sign up with AWS and create an account with Access Key.
Create IAM role. I named it Lambda1. Copy its ARN and use it when you create the lambda function.
```bash
aws configure      # Learn more: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html 
```
Learn more: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html 

```bash
bash deployLambda.sh scrapWind
```

```bash
aws lambda create-function --region eu-west-1 --function-name scrapWind --zip-file fileb:///home/ec2-user/Code/scrapWind/scrapWind.zip --role arn:aws:iam::510136466810:role/Lambda1 --handler  scrapWind.lambda_handler --runtime python2.7 --timeout 300
```

### Create Lambda versioning ###
```bash
aws lambda create-alias --function-name "scrapWind" --name DEV --description "DEV alias pointing to LATEST" --function-version "\$LATEST"
aws lambda publish-version --function-name "scrapWind"
aws lambda create-alias --function-name "scrapWind" --name PROD --description "PROD alias pointing to 1" --function-version 1
```

### Update code and version in Lambda ###
```bash
bash deployLambda.sh scrapWind
aws lambda publish-version --function-name "scrapWind"
aws lambda update-alias --function-name "scrapWind" --name PROD --function-version 2 # or what version you got from publish above
```

### Schedule execution
Create a scheduler as in step 2 in http://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html 

Now the AWS CloudWatch rule scheduler will trigger the lambda script 

