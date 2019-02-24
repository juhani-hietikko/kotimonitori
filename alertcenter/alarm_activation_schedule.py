import boto3

dynamo = boto3.client('dynamodb')


def is_target_active_now(dynamo, target):
