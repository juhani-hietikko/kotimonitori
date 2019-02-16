import json
import math
import boto3

from datetime import datetime, timedelta

dynamo = boto3.client('dynamodb')

def handle(event, context):
    req_body = json.loads(event['body'])
    detector = req_body['detector']
    timestamp_ms = math.floor(1000 * datetime.utcnow().timestamp())
    expires = math.floor((datetime.utcnow() + timedelta(days=30)).timestamp())

    dynamo.put_item(
        TableName='MotionDetection',
        Item={
            'Detector': {'S': detector},
            'EventTime': {'N': str(timestamp_ms)},
            'Expires': {'N': str(expires)}
        }
    )
    response = {
        'statusCode': 200,
        'body': 'Registered motion from detector ' + detector
    }
    return response
