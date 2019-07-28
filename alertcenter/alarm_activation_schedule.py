from datetime import datetime, time, timedelta
from pytz import timezone


def helsinki_timestamp(datetime_now, hours, minutes):
    return timezone('Europe/Helsinki').localize(datetime.combine(datetime_now.date(), time(int(hours), int(minutes))))


def is_schedule_active_now(schedule_item, time_now):
    if not schedule_item['Enabled']['BOOL']:
        return False
    [start_hours, start_minutes] = schedule_item['StartTime']['S'].split(':')
    [end_hours, end_minutes] = schedule_item['EndTime']['S'].split(':')
    start_time = helsinki_timestamp(time_now, start_hours, start_minutes)
    end_time = helsinki_timestamp(time_now, end_hours, end_minutes)

    if start_time > end_time:
        start_time_yesterday = start_time - timedelta(days=1)
        end_time_tomorrow = end_time + timedelta(days=1)
        return (time_now > start_time and time_now < end_time_tomorrow) or (time_now > start_time_yesterday and time_now < end_time)
    else:
        return time_now > start_time and time_now < end_time


def is_target_active_now(dynamo, target):
    helsinki_time_now = datetime.now(tz=timezone('Europe/Helsinki'))

    schedule_items = dynamo.query(
        TableName='AlarmActivationSchedule',
        KeyConditionExpression='Target = :target',
        ExpressionAttributeValues={':target': {'S': target}}
    )['Items']

    for schedule_item in schedule_items:
        if is_schedule_active_now(schedule_item, helsinki_time_now):
            return True

    return False
