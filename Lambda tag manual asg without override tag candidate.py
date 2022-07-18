import boto3
import os
import datetime

# Get the env variables
SNS_REGION = os.getenv('SNS_REGION')
SNS_ARN_TOPIC = os.getenv('SNS_ARN_TOPIC')
DATE = datetime.date.today()


def check_scaling_policies(list_ASG_names, ASG_client):
    """
    It takes a list of ASG names and an ASG client, and returns a list of ASG names that have no scaling policies

    :param list_ASG_names: a list of ASG names
    :param ASG_client: the boto3 client for the Auto Scaling service
    :return: A list of ASG names that are using manual scaling policies.
    """
    ASG_manual = []
    ASG_dynamic = []
    for ASG_name in list_ASG_names:
        respone = ASG_client.describe_policies(AutoScalingGroupName=ASG_name)
        list_scaling_policies = respone["ScalingPolicies"]
        if not list_scaling_policies:  # check if the ScalingPolicies is empty
            ASG_manual.append(ASG_name)
        else:
            ASG_dynamic.append(ASG_name)
    return ASG_manual


def update_tags(list_manual_ASG_names, ASG_client):
    """
    This function takes a list of ASG names and an ASG client and updates the tags of the ASGs with the current date

    :param list_manual_ASG_names: a list of ASG names that you want to update
    :param ASG_client: the boto3 client for the ASG service
    """
    for ASG_name in list_manual_ASG_names:
        respone_tags = ASG_client.create_or_update_tags(
            Tags=[
                {
                    'PropagateAtLaunch': True,
                    # Determines whether the tag is added to new instances as they are launched in the group.
                    'ResourceId': ASG_name,
                    'ResourceType': 'auto-scaling-group',
                    'Key': 'auto_scale_candidate',
                    'Value': str(DATE),
                },

            ],
        )


def get_auto_scaling_groups_names(ASG_client):
    """
    This function takes an AWS client object as an argument and returns a list of all the auto scaling groups names

    :param ASG_client: The boto3 client for the Auto Scaling service
    :return: A list of all the Auto Scaling Groups names.
    """
    ASG_names_list = []
    respone_name = ASG_client.describe_auto_scaling_groups()
    all_groups = respone_name['AutoScalingGroups']
    for i in all_groups:
        ASG_names_list.append(i['AutoScalingGroupName'])
    return ASG_names_list


def get_all_region_names():
    """
    It uses the boto3 library to get a list of all the regions in AWS
    :return: A list of all the region names.
    """
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions

def send_sns_asg_tag_groups(region, topic_arn, list_tag_manual_ASG_names):
    """
    This function sends a message to the SNS topic that you created in the previous step

    :param region: The region where the ASG is located
    :param topic_arn: The ARN of the SNS topic to which you want to send the notification
    :param list_tag_manual_ASG_names: This is a list of ASG names that are not tagged with the tag key and value that you
    specified in the parameters
    """
    sns_client = boto3.client('sns', region_name=region)
    message = "The lambda tag manual ASG: " + ', '.join(
        list_tag_manual_ASG_names) + ", in region: " + region + "\n for more information you can enter to CloudWatch: https://" + SNS_REGION + ".console.aws.amazon.com/cloudwatch/home "
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message
    )

def get_auto_scaling_groups_names_with_tag_candidate(ASG_client):
    """
    This function takes in an AWS Auto Scaling Group client and returns a list of Auto Scaling Group names that have the tag
    'auto_scale_candidate' or 'k8s.io/cluster-autoscaler/enabled'

    :param ASG_client: The boto3 client for the Auto Scaling Group service
    :return: A list of ASG names that have the tag 'auto_scale_candidate' or 'k8s.io/cluster-autoscaler/enabled'
    """
    tagged_candidate_asg = []
    response = ASG_client.describe_auto_scaling_groups()
    for group in response['AutoScalingGroups']:
        for item in group['Tags']:
            for key in item.values():
                if key == 'auto_scale_candidate' or key == 'k8s.io/cluster-autoscaler/enabled':
                    tagged_candidate_asg.append(group['AutoScalingGroupName'])
    asg_list = list(set(tagged_candidate_asg))
    return asg_list


def get_auto_scaling_groups_without_tag_candidate(list_all_ASG_names, list_tag_candidate):
    """
    This function takes two lists as input, and returns a list of items that are in the first list but not in the second
    list

    :param list_all_ASG_names: This is a list of all the ASG names in the account
    :param list_tag_candidate: A list of all the ASG names that have the tag candidate or K8S
    :return: A list of ASG names that do not have the tag candidate.
    """
    asg_without_tag_candidate = list(set(list_all_ASG_names) - set(list_tag_candidate))
    return asg_without_tag_candidate


def lambda_handler(event, context):
    """
    It will iterate through all the regions and check if the ASG has a tag candidate. If it does not, it will check if the
    ASG has a scaling policy. If it does not, it will add the tag candidate to the ASG

    :param event: This is the event that triggered the lambda function
    :param context: The Lambda context object
    """
    list_all_ASG_names = []
    list_manual_ASG_names = []
    list_region = []
    all_region = get_all_region_names()
    for region in all_region:
        ASG_client = boto3.client('autoscaling', region)
        list_all_ASG_names = get_auto_scaling_groups_names(ASG_client)
        list_tag_candidate = get_auto_scaling_groups_names_with_tag_candidate(ASG_client)
        list_asg_without_tag_candidate = get_auto_scaling_groups_without_tag_candidate(list_all_ASG_names,
                                                                                       list_tag_candidate)
        if check_scaling_policies(list_asg_without_tag_candidate, ASG_client):
            list_manual_ASG_names = check_scaling_policies(list_asg_without_tag_candidate, ASG_client)
            update_tags(list_manual_ASG_names, ASG_client)
            send_sns_asg_tag_groups(SNS_REGION, SNS_ARN_TOPIC, list_manual_ASG_names)
            list_tag_manual_ASG_names = "{0} : {1}".format(region, list_manual_ASG_names)
            print(list_tag_manual_ASG_names)  # log to cloudwatch

