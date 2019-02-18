import json
import math
import boto3

from datetime import datetime, timedelta

dynamo = boto3.client('dynamodb')
cloudwatch = boto3.client('cloudwatch')
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
    now = datetime.utcnow()
    timestamp_ms = math.floor(1000 * now.timestamp())
    expires = math.floor((now + timedelta(days=30)).timestamp())

    dynamo.put_item(
        TableName='MotionDetection',
        Item={
            'Detector': {'S': detector},
            'EventTime': {'N': str(timestamp_ms)},
            'Expires': {'N': str(expires)},
            'EventTimeStr': {'S': str(now)}
        }
    )
    cloudwatch.put_metric_data(
        Namespace='MovementDetectionV1',
        MetricData=[
            {
                'MetricName': 'MovementDetections',
                'Dimensions': [
                    {
                        'Name': 'detector',
                        'Value': detector
                    },
                ],
                'Value': 1,
                'Unit': 'Count'
            }
        ]
    )
    return {
        'statusCode': 200,
        'body': 'Registered motion from detector ' + detector
    }
