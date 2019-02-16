#!/usr/bin/env python -u

import boto3
import logging
import requests
import json

from datetime import datetime, timedelta
from collections import deque
from statistics import median
from ruuvitag_sensor.ruuvi import RuuviTagSensor


logging.basicConfig()
logger = logging.getLogger('ruuvibridge')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('/home/pi/ruuvibridge.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

cloudwatch = boto3.client('cloudwatch')
ssm = boto3.client('ssm')
api_key = ssm.get_parameter(Name='ruuvibridge-api-key', WithDecryption=True)['Parameter']['Value']

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
    'F2:F6:4B:B0:A7:27': {
        'name': 'Garden'
    },
    'DD:18:D0:A1:50:D7': {
        'name': 'Back Door',
        'is_door_sensor': True,
        # 'opening_direction': 1,
        # 'x_direction': 1,
        # 'y_direction': 1
    },
    'EF:6D:A7:E0:25:63': {
        'name': 'Back Door Out',
        'is_door_sensor': True,
        # 'opening_direction': -1,
        # 'x_direction': 1,
        # 'y_direction': 1
    },
    'E2:A8:17:03:41:6D': {
        'name': 'Front Door',
        'is_door_sensor': True,
        # 'opening_direction': -1,
        # 'x_direction': -1,
        # 'y_direction': 1
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


def keep_track_of_acceleration(tag, sample):
    if tag['samplecounter'] == 0:
        tag['acc_history_total'].append(sample[1]['acceleration'])
        tag['acc_history_x'].append(sample[1]['acceleration_x'])
        tag['acc_history_y'].append(sample[1]['acceleration_y'])
        tag['acc_history_z'].append(sample[1]['acceleration_z'])

        if len(tag['acc_history_total']) > 20:
            tag['acc_history_total'].popleft()
            tag['acc_history_x'].popleft()
            tag['acc_history_y'].popleft()
            tag['acc_history_z'].popleft()

        tag['normal_acc_total'] = median(tag['acc_history_total'])
        tag['normal_acc_x'] = median(tag['acc_history_x'])
        tag['normal_acc_y'] = median(tag['acc_history_y'])
        tag['normal_acc_z'] = median(tag['acc_history_z'])

    tag['samplecounter'] = (tag['samplecounter'] + 1) % 5


def abs_sum(values):
    result = 0.0
    for val in values:
        result += abs(val)
    return result


def record_potential_motion(tag, sample):
    if len(tag['acc_history_total']) >= 20:
        
        if not tag['door_sensing_initialized']:
            tag['door_sensing_initialized'] = True
            logger.info('Door sensing initialized for tag ' + tag['name'])

        deviation_total = sample[1]['acceleration'] - tag['normal_acc_total']
        deviation_x = sample[1]['acceleration_x'] - tag['normal_acc_x']
        deviation_y = sample[1]['acceleration_y'] - tag['normal_acc_y']
        deviation_z = sample[1]['acceleration_z'] - tag['normal_acc_z']

        tag['acc_deviation_total'].append(deviation_total)
        tag['acc_deviation_x'].append(deviation_x)
        tag['acc_deviation_y'].append(deviation_y)
        tag['acc_deviation_z'].append(deviation_z)

        if len(tag['acc_deviation_total']) > 5:
            tag['acc_deviation_total'].popleft()
            tag['acc_deviation_x'].popleft()
            tag['acc_deviation_y'].popleft()
            tag['acc_deviation_z'].popleft()

        deviation_sum_total = abs_sum(tag['acc_deviation_total'])
        deviation_sum_x = abs_sum(tag['acc_deviation_x'])
        deviation_sum_y = abs_sum(tag['acc_deviation_y'])
        deviation_sum_z = abs_sum(tag['acc_deviation_z'])

        if deviation_sum_x + deviation_sum_y + deviation_sum_z > 70:
            requests.post('https://jhie.name/motion',
                          headers={'X-Api-Key': api_key,
                                   'Content-type': 'application/json'},
                          data = json.dumps({
                              'tag': tag['name'],
                              'acceleration_samples': {
                                  'total': list(tag['acc_deviation_total']),
                                  'x': list(tag['acc_deviation_x']),
                                  'y': list(tag['acc_deviation_y']),
                                  'z': list(tag['acc_deviation_z'])
                              }
                          }))


def process_sample(sample):
    tag_mac = sample[0]
    tag = tags.get(tag_mac)

    if tag.get('is_door_sensor'):
        keep_track_of_acceleration(tag, sample)
        record_potential_motion(tag, sample)

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
    logger.info('ruuvibridge startup...')
    now = datetime.now()
    for mac in tags:
        tag = tags[mac]
        if tag.get('is_door_sensor'):
            tag['acc_history_total'] = deque()
            tag['acc_history_x'] = deque()
            tag['acc_history_y'] = deque()
            tag['acc_history_z'] = deque()
            tag['acc_deviation_total'] = deque()
            tag['acc_deviation_x'] = deque()
            tag['acc_deviation_y'] = deque()
            tag['acc_deviation_z'] = deque()
            tag['samplecounter'] = 0
            tag['door_sensing_initialized'] = False

        tags[mac]['last_upload'] = now - timedelta(minutes=1)

    RuuviTagSensor.get_datas(process_sample)
