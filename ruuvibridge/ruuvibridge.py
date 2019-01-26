#!/usr/bin/env python

import boto3

from datetime import datetime
from ruuvitag_sensor.ruuvi import RuuviTagSensor

cloudwatch = boto3.client('cloudwatch')

tags = {
    'D2:B4:89:37:FE:5E': {
        'name': 'Fridge',
        'hour_last_upload': -1
    },
    'C6:57:4E:37:1E:66': {
        'name': 'Freezer',
        'hour_last_upload': -1
    }
}

def process_sample(sample):
    tag_mac = sample[0]
    tag = tags.get(tag_mac)

    if tag:
        hour_now = datetime.now().hour
        if tag['hour_last_upload'] != hour_now:
            print(tag_mac)
            print(tag['name'])
            print(sample[1]['temperature'])
            cloudwatch.put_metric_data(
                Namespace='Test2',
                MetricData=[
                    {
                        'MetricName': 'Temperature',
                        'Dimensions': [
                            {
                                'Name': 'tagname',
                                'Value': tag['name']
                            },
                        ],
                        'Value': sample[1]['temperature'],
                        'Unit': 'Count'
                    }
                ]
            )
            tag['hour_last_upload'] = hour_now


if __name__ == '__main__':
    RuuviTagSensor.get_datas(process_sample)
