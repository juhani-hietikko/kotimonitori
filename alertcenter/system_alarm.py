import json
import boto3
import urllib.parse
from botocore.vendored import requests

ssm = boto3.client('ssm')
ifttt_key = ssm.get_parameter(Name='ifttt-webhook-key', WithDecryption=True)['Parameter']['Value']

def handle(event, context):
    sns_notification = event['Records'][0]['Sns']
    cloudwatch_message = json.loads(sns_notification['Message'])
    alarm_name = cloudwatch_message["AlarmName"]

    notification_url = 'https://maker.ifttt.com/trigger/system_alarm_notification/with/key/' + ifttt_key + '?value1=' + urllib.parse.quote(alarm_name)
    requests.post(notification_url)
