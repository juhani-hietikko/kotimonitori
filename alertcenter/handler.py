import json

def sensor_motion(event, context):
    req_body = json.loads(event['body'])
    tag = req_body['tag']
    response = {
        "statusCode": 200,
        "body": 'Registered motion for tag ' + tag
    }
    return response
