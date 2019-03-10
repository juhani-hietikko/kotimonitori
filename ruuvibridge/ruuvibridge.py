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
dynamo = boto3.client('dynamodb')
api_key = ssm.get_parameter(Name='ruuvibridge-api-key', WithDecryption=True)['Parameter']['Value']


def fetch_tag_config():
    config_items = dynamo.scan(TableName='TagConfiguration')['Items']
    config = {}
    for config_item in config_items:
        tag_mac = config_item['MacAddress']['S']
        config[tag_mac] = {
            'name': config_item['Tag']['S'],
            'is_door_sensor': config_item['IsDoorSensor']['BOOL']
        }
    return config


tags = fetch_tag_config()
status = {}


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


def record_potential_motion(tag, sample, now):
    if tag['door_sensing_initialized'] or len(tag['acc_history_total']) >= 20:
        
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

        if len(tag['acc_deviation_total']) > 3:
            tag['acc_deviation_total'].popleft()
            tag['acc_deviation_x'].popleft()
            tag['acc_deviation_y'].popleft()
            tag['acc_deviation_z'].popleft()

        deviation_sum_x = abs_sum(tag['acc_deviation_x'])
        deviation_sum_y = abs_sum(tag['acc_deviation_y'])
        deviation_sum_z = abs_sum(tag['acc_deviation_z'])

        if now - tag['last_motion'] >= timedelta(minutes=1) \
                and deviation_sum_x + deviation_sum_y + deviation_sum_z > 70:
            tag['last_motion'] = now
            requests.post('https://jhie.name/doorsensordetection',
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
    now = datetime.now()

    if tag.get('is_door_sensor'):
        keep_track_of_acceleration(tag, sample)
        record_potential_motion(tag, sample, now)

    if tag:
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

    if now - status['last_heartbeat'] >= timedelta(minutes=5):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = int(float(f.readline().split()[0]))
        cloudwatch.put_metric_data(
            Namespace='DiagnosticsV1',
            MetricData=[
                {
                    'MetricName': 'Uptime',
                    'Dimensions': [
                        {
                            'Name': 'systemname',
                            'Value': 'hallonpaj-ruuvibridge'
                        },
                    ],
                    'Value': uptime_seconds,
                    'Unit': 'Seconds'
                }
            ]
        )
        status['last_heartbeat'] = now


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
            tag['last_motion'] = now - timedelta(minutes=1)

        tags[mac]['last_upload'] = now - timedelta(minutes=1)

    status['last_heartbeat'] = now - timedelta(minutes=5)

    RuuviTagSensor.get_datas(process_sample)
