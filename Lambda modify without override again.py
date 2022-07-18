import boto3
from datetime import datetime, timedelta
from datetime import date
from datetime import datetime
import os

# Get the env variables
SNS_ARN_TOPIC = os.getenv('SNS_ARN_TOPIC')
SNS_REGION = os.getenv('SNS_REGION')
EXECUTION_PERIOD_BY_TAG = int(os.getenv('EXECUTION_PERIOD_BY_TAG')) # because we will compere it with int


def check_asg_date_tag(ASG_client):
    """
    This function will return a list of all the Auto Scaling Groups that have the tag key 'auto_scale_candidate' and the
    value of the tag is the date Tag lambda tagged ASG

    :param ASG_client: The boto3 client for the Auto Scaling Group service
    :return: A list of dictionaries.
    """
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
    """
    This function takes an ASG client and an ASG name as input and creates a scaling policy (Average CPU utilization at 80 ) for the ASG

    :param ASG_client: The boto3 client for Auto Scaling Groups
    :param asg_name: The name of the Auto Scaling group
    """
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
    """
    This function returns the current date.
    :return: The date of today.
    """
    today = date.today()
    return today


def check_delta_date_now_minus_tag(string_date):
    """
    It takes a string date in the format of 'YYYY-MM-DD' and returns the number of days between that date and today's date

    :param string_date: The date in string format
    :return: The number of days between the date of the tag and today.
    """
    date_str_tag = string_date
    date_object_tag = datetime.strptime(date_str_tag, '%Y-%m-%d').date()  # Converte string to datetime class
    delta = get_today_date() - date_object_tag
    return delta.days


def get_all_region_names():
    """
    It uses the boto3 library to get a list of all the regions in AWS
    :return: A list of all the region names.
    """
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions


def send_sns_asg_tag_groups(region, topic_arn, asg_name):
    """
    It sends an SNS message to the topic ARN that you pass in

    :param region: The region where the ASG is located
    :param topic_arn: The ARN of the SNS topic to send the message to
    :param asg_name: The name of the ASG you want to modify
    """
    sns_client = boto3.client('sns')
    message = "The lambda modify manual ASG to dynamic ASG: " + ''.join(
        asg_name) + "\n for more information you can enter to CloudWatch: https://" + SNS_REGION + ".console.aws.amazon.com/cloudwatch/home "
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message
    )


def check_scaling_policies(ASG_name, ASG_client):
    """
    It takes an ASG name and an ASG client as input, and returns the ASG name if the ASG has no scaling policies, and
    returns False if the ASG has scaling policies

    :param ASG_name: The name of the Auto Scaling Group
    :param ASG_client: the boto3 client for the Auto Scaling service
    :return: the ASG name if the ASG has no ScalingPolicies.
    """
    respone = ASG_client.describe_policies(AutoScalingGroupName=ASG_name)
    list_scaling_policies = respone["ScalingPolicies"]
    if not list_scaling_policies:  # check if the ScalingPolicies is empty
        return ASG_name
    else:
        return False  # ASG with ScalingPolicies


def lambda_handler(event, context):
    """
    The function will check all the ASG in all the regions and if the tag value is a date and the delta between the date and
    now is greater than the EXECUTION_PERIOD_BY_TAG then it will send a notification to the SNS topic and change the ASG to
    dynamic scaling, and print to CloudWatch

    :param event: This is the event that triggered the lambda function
    :param context: This is an object that contains information about the invocation, function, and execution environment
    """
    all_region = get_all_region_names()
    for region in all_region:
        ASG_client = boto3.client('autoscaling', region)
        response = check_asg_date_tag(ASG_client)
        for item in response['Tags']:
            asg = list(item.values())
            asg_name = asg[0]
            date_tag = asg[3]
            # print(type(EXECUTION_PERIOD_BY_TAG))
            try:  # if the key = cndidate but value of the tag is not date then pass
                if ((check_delta_date_now_minus_tag(date_tag) > EXECUTION_PERIOD_BY_TAG) and (
                        check_scaling_policies(asg_name, ASG_client))):
                    send_sns_asg_tag_groups(SNS_REGION, SNS_ARN_TOPIC, asg_name)
                    print(check_delta_date_now_minus_tag(date_tag), asg_name, date_tag, region)  # log to cloudwatch
                    modify_to_dynamic_asg(ASG_client, asg_name)

            except:
                pass
