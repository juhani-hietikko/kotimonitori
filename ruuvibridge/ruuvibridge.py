#!/usr/bin/env python -u

import boto3

from datetime import datetime, timedelta
from ruuvitag_sensor.ruuvi import RuuviTagSensor

cloudwatch = boto3.client('cloudwatch')

tags = {
    'D2:B4:89:37:FE:5E': {
        'name': 'Freezer'
    },
    'C6:57:4E:37:1E:66': {
        'name': 'Fridge'
    },
    'E4:C5:67:4E:6B:37': {
        'name': 'Small Bedroom'
    },
    'FC:CA:62:B3:1F:6B': {
        'name': 'Large Bedroom'
    },
    'D3:08:3A:26:44:84': {
        'name': 'Bathroom'
    },
    'DD:18:D0:A1:50:D7': {
        'name': 'Living Room'
    },
    'F2:F6:4B:B0:A7:27': {
        'name': 'Garden'
    },
    'EF:6D:A7:E0:25:63': {
        'name': 'Back Door',
        'is_door_sensor': True
    },
    'E2:A8:17:03:41:6D': {
        'name': 'Front Door',
        'is_door_sensor': True
    }
}


def metricdata(tag, sample, metric_name, metric_key, unit='None'):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'tagname',
                'Value': tag['name']
            },
        ],
        'Value': sample[1][metric_key],
        'Unit': unit
    }

def report_motion(tag, motion_value):
    cloudwatch.put_metric_data(
        Namespace='DetectionV1',
        MetricData=[
            {
                'MetricName': 'Motion',
                'Dimensions': [
                    {
                        'Name': 'tagname',
                        'Value': tag['name']
                    },
                ],
                'Value': motion_value,
                'Unit': 'None'
            }
        ]
    )


def process_sample(sample):
    tag_mac = sample[0]
    tag = tags.get(tag_mac)

    if tag.get('is_door_sensor'):
        now = datetime.now()
        acc = sample[1]['acceleration_z']
        if tag.get('last_sample'):
            delta_time = (now - tag['last_sample']).total_seconds()
            delta_acc = acc - tag['last_acc']
            motion = abs(delta_acc / delta_time)

            if motion + tag['last_motion']  > 25:
                report_motion(tag, motion + tag['last_motion'])
        else:
            motion = 0.0

        tag['last_sample'] = now
        tag['last_acc'] = acc
        tag['last_motion'] = motion

    if tag:
        now = datetime.now()
        if now - tag['last_upload'] >= timedelta(minutes=1):
            cloudwatch.put_metric_data(
                Namespace='HomeEnvironV1',
                MetricData=[
                    metricdata(tag, sample, 'Temperature', 'temperature'),
                    metricdata(tag, sample, 'Pressure', 'pressure'),
                    metricdata(tag, sample, 'Humidity', 'humidity', 'Percent')
                ]
            )
            tag['last_upload'] = now


if __name__ == '__main__':
    now = datetime.now()
    for mac in tags:
        tags[mac]['last_upload'] = now - timedelta(minutes=1)

    RuuviTagSensor.get_datas(process_sample)
