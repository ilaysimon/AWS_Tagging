import sys
import boto3
from botocore.exceptions import ClientError
import logging
import os

#Get the env variables
SNS_REGION = os.getenv('SNS_REGION')
SNS_ARN_TOPIC = os.getenv('SNS_ARN_TOPIC')


def check_scaling_policies(list_ASG_names,ASG_client):
    ASG_manual = []
    ASG_dynamic = []
    for ASG_name in list_ASG_names:
        respone = ASG_client.describe_policies(AutoScalingGroupName = ASG_name)
        list_scaling_policies = respone["ScalingPolicies"]
        if not list_scaling_policies : #check if the ScalingPolicies is empty
            ASG_manual.append(ASG_name)
        else :
            ASG_dynamic.append(ASG_name)
    return ASG_manual


def update_tags(list_manual_ASG_names,ASG_client) :
    for ASG_name in list_manual_ASG_names:
        respone_tags = ASG_client.create_or_update_tags(
            Tags=[
            {
                'PropagateAtLaunch': True, #Determines whether the tag is added to new instances as they are launched in the group.
                'ResourceId': ASG_name,
                'ResourceType': 'auto-scaling-group',
                'Key': 'auto_scale_candidate',
                'Value': 'True',
            },

          ],
        )

def get_auto_scaling_groups_names(ASG_client) :
    ASG_names_list = []
    respone_name = ASG_client.describe_auto_scaling_groups()
    all_groups = respone_name['AutoScalingGroups']
    for i in all_groups:
        ASG_names_list.append(i['AutoScalingGroupName'])
    return ASG_names_list


def get_all_region_names():
    client = boto3.client('ec2')
    regions = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regions

def update_tag_manual_ASG():
    list_all_ASG_names = []
    list_manual_ASG_names = []
    list_region = []
    all_region = get_all_region_names()
    for region in all_region :
        ASG_client = boto3.client('autoscaling', region)
        if get_auto_scaling_groups_names(ASG_client):
            list_all_ASG_names = (get_auto_scaling_groups_names(ASG_client))
            if check_scaling_policies(list_all_ASG_names , ASG_client):
                list_manual_ASG_names = check_scaling_policies(list_all_ASG_names , ASG_client)
                list_tag_manual_ASG_names = "{0} : {1}".format(region ,list_manual_ASG_names)
                send_sns_asg_tag_groups(SNS_REGION , SNS_ARN_TOPIC,list_manual_ASG_names)
                print(list_tag_manual_ASG_names) # log to cloudwatch
                update_tags(list_manual_ASG_names, ASG_client)


def send_sns_asg_tag_groups(region, topic_arn , list_tag_manual_ASG_names):
    sns_client = boto3.client('sns', region_name=region)
    message = "The lambda tag manual ASG: " +  ', '.join(list_tag_manual_ASG_names) + "\n for more information you can enter to CloudWatch: https://" +SNS_REGION+ ".console.aws.amazon.com/cloudwatch/home "
    response = sns_client.publish(
        TopicArn = topic_arn,
        Message = message
    )

def lambda_handler(event, context):
    update_tag_manual_ASG()



if __name__ == "__main__":
    main()
