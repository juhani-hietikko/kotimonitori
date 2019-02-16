import json
import math
import boto3

from datetime import datetime, timedelta

dynamo = boto3.client('dynamodb')

def sensor_motion(event, context):
    print('Timestamp, ms: ' + math.floor(1000 * datetime.utcnow().timestamp()))
    req_body = json.loads(event['body'])
    tag = req_body['tag']
    timestamp_ms = math.floor(1000 * datetime.utcnow().timestamp())
    expires = math.floor((datetime.utcnow() + timedelta(days=30)).timestamp())

    dynamo.put_item(
        TableName='motion',
        Item={
            'Tag': {'S': tag},
            'EventTime': {'N': str(timestamp_ms)},
            'AccelerationSamples': {'M': json.dumps(req_body['acceleration_samples'])},
            'Expires': {'n': str(expires)}
        }
    )
    response = {
        'statusCode': 200,
        'body': 'Registered motion for tag ' + tag
    }
    return response
