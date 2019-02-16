import json
import math
import boto3

from datetime import datetime, timedelta

dynamo = boto3.client('dynamodb')


def dynamo_list(list):
    return [{'N': str(val)} for val in list]


def handle(event, context):
    req_body = json.loads(event['body'])
    tag = req_body['tag']
    timestamp_ms = math.floor(1000 * datetime.utcnow().timestamp())
    expires = math.floor((datetime.utcnow() + timedelta(days=30)).timestamp())

    acc_total = dynamo_list(req_body['acceleration_samples']['total'])
    acc_x = dynamo_list(req_body['acceleration_samples']['x'])
    acc_y = dynamo_list(req_body['acceleration_samples']['y'])
    acc_z = dynamo_list(req_body['acceleration_samples']['z'])

    dynamo.put_item(
        TableName='DoorSensorDetection',
        Item={
            'Tag': {'S': tag},
            'EventTime': {'N': str(timestamp_ms)},
            'AccelerationSamplesTotal': {'L': acc_total},
            'AccelerationSamplesX': {'L': acc_x},
            'AccelerationSamplesY': {'L': acc_y},
            'AccelerationSamplesZ': {'L': acc_z},
            'Expires': {'N': str(expires)}
        }
    )
    response = {
        'statusCode': 200,
        'body': 'Registered motion for tag ' + tag
    }
    return response
