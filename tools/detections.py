#!/usr/bin/env python
import boto3
import math
import argparse
import json
import requests
from datetime import datetime
from argparse import RawTextHelpFormatter


actions = ['list', 'simulate']


description = """

tool for listing recent detections from AWS DynamoDB, and for simulating detection handling
"""


def read_args():
    parser = argparse.ArgumentParser(description='', formatter_class=RawTextHelpFormatter)
    parser.add_argument('action',
                        help='Configuration action to execute',
                        choices=set(actions))
    parser.add_argument('--tag',
                        help='Name of tag to list detections for')
    parser.add_argument('--minutes',
                        help='For how many minutes in the past to list')
    parser.add_argument('--apikey',
                        help='API key for detection simulation')
    return parser.parse_args()


if __name__ == '__main__':
    args = read_args()
    dynamo = boto3.client('dynamodb')

    if args.action == 'list':
        assert(args.tag)
        assert(args.minutes)

        timestamp_now_ms = math.floor(1000 * datetime.now().timestamp())

        detection_items = dynamo.query(
            TableName='DoorSensorDetection',
            KeyConditionExpression='Tag = :tag AND EventTime > :time_limit',
            ExpressionAttributeValues={':tag': {'S': args.tag},
                                       ':time_limit': {'N': str(timestamp_now_ms - 60000 * int(args.minutes))}}
        )['Items']
        print(detection_items)
    elif args.action == 'simulate':
        assert(args.tag)
        assert(args.apikey)
        requests.post('https://jhie.name/doorsensordetection',
                                  headers={'X-Api-Key': args.apikey,
                                           'Content-type': 'application/json'},
                                  data = json.dumps({
                                      'tag': args.tag,
                                      'acceleration_samples': {
                                          'total': [20, 20, 20],
                                          'x': [20, 20, 20],
                                          'y': [20, 20, 20],
                                          'z': [20, 20, 20]
                                      }
                                  }))