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


def recent_detection_exists(tag, timestamp_now_ms):
    recent_detections = dynamo.query(
        TableName='DoorSensorDetection',
        KeyConditionExpression='Tag = :tag AND EventTime > :time_limit',
        ExpressionAttributeValues={':tag': {'S': tag},
                                   ':time_limit': {'N': str(timestamp_now_ms - 60000)}}
    )['Items']
    return len(recent_detections) > 0


def target_breached(target_tag_outer, target_tag_inner, detecting_tag, timestamp_now_ms):
    return detecting_tag == target_tag_inner and recent_detection_exists(target_tag_outer, timestamp_now_ms)


def handle(event, context):
    req_body = json.loads(event['body'])
    tag = req_body['tag']
    now = datetime.utcnow()
    timestamp_ms = math.floor(1000 * now.timestamp())
    expires = math.floor((now + timedelta(days=30)).timestamp())

    # todo: replace hard-coded target configuration with something else
    if tag == 'TK Door':
        target = 'Front Entrance'
        target_tag_outer = 'Front Door'
        target_tag_inner = 'TK Door'
    elif tag == 'Back Door':
        target = 'Back Entrance'
        target_tag_outer = 'Back Door Out'
        target_tag_inner = 'Back Door'
    else:
        target = None
        target_tag_outer = None
        target_tag_inner = None

    if target and is_target_active_now(dynamo, target) and target_breached(target_tag_outer, target_tag_inner, tag, timestamp_ms):
        notification_url = 'https://maker.ifttt.com/trigger/door_alarm_notification/with/key/' + ifttt_key + '?value1=' + urllib.parse.quote(target)
        siren_trigger_url = 'https://maker.ifttt.com/trigger/alarm_siren/with/key/' + ifttt_key
        requests.post(notification_url)
        requests.post(siren_trigger_url)

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

    response = {
        'statusCode': 200,
        'body': 'Registered motion for tag ' + tag
    }
    return response
