#!/usr/bin/env python

import boto3

from datetime import datetime, timedelta
from ruuvitag_sensor.ruuvi import RuuviTagSensor

cloudwatch = boto3.client('cloudwatch')

tags = {
    'D2:B4:89:37:FE:5E': {
        'name': 'Freezer',
        'last_upload': datetime.now() - timedelta(minutes=1)
    },
    'C6:57:4E:37:1E:66': {
        'name': 'Fridge',
        'last_upload': datetime.now() - timedelta(minutes=1)
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


def process_sample(sample):
    tag_mac = sample[0]
    tag = tags.get(tag_mac)

    if tag:
        now = datetime.now()
        if now - tag['last_upload'] >= timedelta(minutes=1):
            cloudwatch.put_metric_data(
                Namespace='Test5',
                MetricData=[
                    metricdata(tag, sample, 'Temperature', 'temperature'),
                    metricdata(tag, sample, 'Pressure', 'pressure'),
                    metricdata(tag, sample, 'Humidity', 'humidity', 'Percent')
                ]
            )
            tag['last_upload'] = now


if __name__ == '__main__':
    RuuviTagSensor.get_datas(process_sample)
