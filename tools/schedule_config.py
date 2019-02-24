#!/usr/bin/env python
import boto3
import argparse

from argparse import RawTextHelpFormatter


actions = ['put', 'get', 'list', 'list_target']


description = """

tool for maintaining ruuvibridge tag configuration in AWS DynamoDB
"""


def read_args():
    parser = argparse.ArgumentParser(description='', formatter_class=RawTextHelpFormatter)
    parser.add_argument('action',
                        help='Configuration action to execute',
                        choices=set(actions))
    parser.add_argument('--target',
                        help='Name of target to configure schedule for')
    parser.add_argument('--schedule',
                        help='Name of schedule to configure')
    parser.add_argument('--days_of_week',
                        help='Comma-separated days of week on which the schedule activates')
    parser.add_argument('--starttime',
                        help='Time when the schedule activates on the given days of week')
    parser.add_argument('--endtime',
                        help='Time when the schedule deactivates on the given days of week')
    parser.add_argument('--enabled',
                        action='store_const',
                        const=True,
                        default=False,
                        help='Set schedule enabled')
    return parser.parse_args()


if __name__ == '__main__':
    args = read_args()
    dynamo = boto3.client('dynamodb')

    if args.action == 'put':
        assert(args.target)
        assert(args.schedule)
        assert(args.days_of_week)
        assert(args.starttime)
        assert(args.endtime)

        dynamo.put_item(
            TableName='AlarmActivationSchedule',
            Item={
                'Target': {'S': args.target},
                'ScheduleName': {'S': args.schedule},
                'DaysOfWeek': {'SS': args.days_of_week.split(',')},
                'StartTime': {'S': args.starttime},
                'EndTime': {'S': args.endtime},
                'Enabled': {'BOOL': args.enabled}
            }
        )
    if args.action == 'get':
        assert(args.target)
        assert(args.schedule)

        schedule_item = dynamo.get_item(
            TableName='AlarmActivationSchedule',
            Key={
                'Target': {'S': args.target},
                'ScheduleName': {'S': args.schedule}
            }
        )['Item']
        print(schedule_item)
    if args.action == 'list_target':
        assert(args.target)

        schedule_items = dynamo.query(
            TableName='AlarmActivationSchedule',
            KeyConditionExpression='Target = :target',
            ExpressionAttributeValues={':target': {'S': args.target}}
        )['Items']
        print(schedule_items)

    elif args.action == 'list':
        schedule_items = dynamo.scan(TableName='AlarmActivationSchedule')['Items']

        schedules = [item['Target']['S'] + '\t' + item['ScheduleName']['S'] + '\t' + str(item['Enabled']['BOOL']) for item in schedule_items]
        print('target\tschedule\tenabled')
        for schedule in schedules:
            print(schedule)
