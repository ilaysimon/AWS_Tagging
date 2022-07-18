import boto3
from datetime import datetime, timedelta
from datetime import date
from datetime import datetime
import os

SNS_ARN_TOPIC = os.getenv('SNS_ARN_TOPIC')
SNS_REGION = os.getenv('SNS_REGION')
EXECUTION_PERIOD_BY_TAG = os.getenv('EXECUTION_PERIOD_BY_TAG')


def check_asg_date_tag(ASG_client):
    response = ASG_client.describe_tags(
        Filters=[
            {
                'Name': 'key',
                'Values': ['auto_scale_candidate']
            }
        ]
    )
    return response


def modify_to_dynamic_asg(ASG_client, asg_name):  # if already exist return Error
    try:
        response = ASG_client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=' Average CPU utilization at 80',  # change
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization'
                },
                'TargetValue': 80.0,
                'DisableScaleIn': False
                # If scaling in is disabled, the target tracking scaling policy doesn't remove instances from the Auto Scaling group. Otherwise, the target tracking scaling policy can remove instances from the Auto Scaling group.
            },
            Enabled=True,  # Indicates whether the scaling policy is enabled or disabled. The default is enabled.
        )
        print(response)
    except Exception as e:
        e


def get_today_date():
    today = date.today()
    return today


def check_delta_date_now_minus_tag(string_date):
    date_str_tag = string_date
    date_object_tag = datetime.strptime(date_str_tag, '%Y-%m-%d').date()  # Converte string to datetime class
    delta = get_today_date() - date_object_tag
    return delta.days


def get_all_region_names():
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions


def send_sns_asg_tag_groups(region, topic_arn, asg_name):
    sns_client = boto3.client('sns')
    message = "The lambda modify manual ASG to dynamic ASG: " + ''.join(
        asg_name) + "\n for more information you can enter to CloudWatch: https://" + SNS_REGION + ".console.aws.amazon.com/cloudwatch/home "
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message
    )


def lambda_handler(event, context):
    all_region = get_all_region_names()
    for region in all_region:
        ASG_client = boto3.client('autoscaling', region)
        response = check_asg_date_tag(ASG_client)
        for item in response['Tags']:
            asg = list(item.values())
            asg_name = asg[0]
            date_tag = asg[3]
            try:  # if the key = cndidate but value of the tag is not date then pass
                if ((check_delta_date_now_minus_tag(date_tag) > EXECUTION_PERIOD_BY_TAG)):
                    send_sns_asg_tag_groups(SNS_REGION, SNS_ARN_TOPIC, asg_name)
                    print(check_delta_date_now_minus_tag(date_tag), asg_name, date_tag, region)  # log to cloudwatch
                    modify_to_dynamic_asg(ASG_client, asg_name)

            except:
                pass
