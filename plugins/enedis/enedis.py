import datetime
import dateutil.parser
import json
import logging
import plugin
import requests
import schedule
import os


class Enedis(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'enedis'
        self.version = '1.0'
        self.description = 'Enedis Power Consumption Collector'
        self.mqtt_topic = '/power/enedis'

        self.url_base = 'https://enedisgateway.tech/api'

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every().day.at('06:00').do(self.run_threaded, self.job)
        return scheduler

    def job(self):
        today = datetime.date.today()
        before = today - datetime.timedelta(days=3)

        payload = {
            'type': 'consumption_load_curve',
            'usage_point_id': self.config['pdl'],
            'start': before.strftime('%Y-%m-%d'),
            'end': today.strftime('%Y-%m-%d'),
        }

        headers = {
            'Authorization': self.config['token'],
            'Content-Type': "application/json",
        }

        logging.info('retrieving data from Enedis')
        r = requests.post(self.url_base, json=payload, headers=headers)
        logging.debug(
            'result: status=' +
            str(r.status_code) +
            ', json=' +
            json.dumps(r.json()))
        data = []
        for measure in r.json()['meter_reading']['interval_reading']:
            dt = dateutil.parser.parse(measure['date'])
            # dt = datetime.datetime.strptime(
            #     measure['date'],
            #     '%Y-%m-%d %H:%M:%S')
            data.append({
                'timestamp': int(datetime.datetime.timestamp(dt)),
                'measurement': 'enedis',
                'fields': {
                    'power': measure['value']
                },
            })
        mqtt_client = self.get_mqtt_client(self.name)
        mqtt_client.publish(self.mqtt_topic, json.dumps(data))
