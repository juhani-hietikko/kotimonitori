#!/usr/bin/env python
import boto3
import argparse

from argparse import RawTextHelpFormatter


actions = ['put', 'list']


description = """

tool for maintaining ruuvibridge tag configuration in AWS DynamoDB
"""


def read_args():
    parser = argparse.ArgumentParser(description='', formatter_class=RawTextHelpFormatter)
    parser.add_argument('action',
                        help='Configuration action to execute',
                        choices=set(actions))
    parser.add_argument('--tag_name',
                        help='Unique name for the tag to configure')
    parser.add_argument('--mac_addr',
                        help='MAC address of the tag')
    parser.add_argument('--doorsensor',
                        action='store_const',
                        const=True,
                        default=False,
                        help='Configure tag as door sensor')
    return parser.parse_args()


if __name__ == '__main__':
    args = read_args()
    dynamo = boto3.client('dynamodb')

    if args.action == 'put':
        assert(args.tag_name)
        assert(args.mac_addr)

        dynamo.put_item(
            TableName='TagConfiguration',
            Item={
                'Tag': {'S': args.tag_name},
                'MacAddress': {'S': args.mac_addr},
                'IsDoorSensor': {'BOOL': args.doorsensor}
            }
        )
    elif args.action == 'list':
        config_items = dynamo.scan(TableName='TagConfiguration')['Items']

        tags = [item['Tag']['S'] + '\t' + item['MacAddress']['S'] + '\t' + str(item['IsDoorSensor']['BOOL']) for item in config_items]
        print('tag\tMAC\tdoor sensor')
        for tag in tags:
            print(tag)
