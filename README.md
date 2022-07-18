<!--Headings-->
# Tag manual ASG and send SNS
The purpose is to tag all ASG in all regions in order to delete them in the future, all you need is to create a S3 bucket and upload the code as zip (lambda_function.py.zip)![Cloudteam_logo_clean](https://user-images.githubusercontent.com/70803336/177555807-aadeb417-bf96-4fd0-be7d-77a81e638eb8.jpeg)
.

`Parameters 
`
* S3BucketWithCode - Enter the name of s3 bucket who contian the code for lambda function
* ScheduleExpressionTag - AWS Schedule Expression representing how often the Lambda will run. Default is once per week (allow valu between 1 to 9)
* WhereIsYourRegion -Enter your region where you creat the stack, for Example: us-east-1.

**the 3 parameters below is about the SNS:**
* CreateSnsTopic - (True | False) if you have one and you want to use it, please answer False and fill the ExistSnsTopicArn, else for new topic answer True
* ExistSnsTopicArn - Relevant if you have exist Topic and subscription!! Enter exist topic ARN, else do nothing
* EndpointSubscription - Relevant if you want new Topic!! Enter your email to get SNS notification, else do nothing

`tag:
`
* Key - auto_scale_candidate
* Value - the date that lambada run

`Run lambda from cli:`

_aws lambda invoke --function-name STSACK_NAME-FunctionTagManualAsg-XXXXX  out --log-type Tail --profile YOURPROFILE --region STACK_REGION_
   

`In order to get the function name you can execute this command from cli:
`
_aws lambda list-functions_


###### Files:
Cloudformation file (Yaml) and Lambda function (Python) 



