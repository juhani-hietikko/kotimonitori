import json
import math
import boto3

from datetime import datetime, timedelta

dynamo = boto3.client('dynamodb')
ssm = boto3.client('ssm')
api_key = ssm.get_parameter(Name='motion-detector-api-key', WithDecryption=True)['Parameter']['Value']

def handle(event, context):
    req_body = json.loads(event['body'])

    req_api_key = req_body.get('apikey')
    if req_api_key != api_key:
        return {
            'statusCode': 403,
            'body': 'Forbidden'
        }

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
    return {
        'statusCode': 200,
        'body': 'Registered motion from detector ' + detector
    }
