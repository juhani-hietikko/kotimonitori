from datetime import datetime
from pytz import timezone


def is_target_active_now(dynamo, target):
    # helsinki_time_now = datetime.now(tz=timezone('Europe/Helsinki'))
    #
    # schedule_items = dynamo.query(
    #     TableName='AlarmActivationSchedule',
    #     KeyConditionExpression='Target = :target',
    #     ExpressionAttributeValues={':target': {'S': target}}
    # )['Items']

    # todo: implement function :)
    return True

