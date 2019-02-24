import json
import math
import boto3
import urllib.parse
from alarm_activation_schedule import is_target_active_now
from botocore.vendored import requests
from datetime import datetime, timedelta


dynamo = boto3.client('dynamodb')
ssm = boto3.client('ssm')
ifttt_key = ssm.get_parameter(Name='ifttt-webhook-key', WithDecryption=True)['Parameter']['Value']


def dynamo_list(list):
    return [{'N': str(val)} for val in list]


def handle(event, context):
    req_body = json.loads(event['body'])
    tag = req_body['tag']
    now = datetime.utcnow()
    timestamp_ms = math.floor(1000 * now.timestamp())
    expires = math.floor((now + timedelta(days=30)).timestamp())

    acc_total = dynamo_list(req_body['acceleration_samples']['total'])
    acc_x = dynamo_list(req_body['acceleration_samples']['x'])
    acc_y = dynamo_list(req_body['acceleration_samples']['y'])
    acc_z = dynamo_list(req_body['acceleration_samples']['z'])

    dynamo.put_item(
        TableName='DoorSensorDetection',
        Item={
            'Tag': {'S': tag},
            'EventTime': {'N': str(timestamp_ms)},
            'EventTimeStr': {'S': str(now)},
            'AccelerationSamplesTotal': {'L': acc_total},
            'AccelerationSamplesX': {'L': acc_x},
            'AccelerationSamplesY': {'L': acc_y},
            'AccelerationSamplesZ': {'L': acc_z},
            'Expires': {'N': str(expires)}
        }
    )
    notification_url = 'https://maker.ifttt.com/trigger/door_alarm_notification/with/key/' + ifttt_key + '?value1=' + urllib.parse.quote(tag)
    requests.post(notification_url)

    response = {
        'statusCode': 200,
        'body': 'Registered motion for tag ' + tag
    }
    return response
