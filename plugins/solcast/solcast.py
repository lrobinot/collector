import datetime
import dateutil.parser
import dateutil.tz
import json
import logging
import plugin
import requests
import schedule


class Solcast(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'solcast'
        self.version = '1.0'
        self.description = 'Solar Power Radiation Collector'
        self.mqtt_topic = '/power/solcast'

        self.url_base = 'https://api.solcast.com.au/'

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every(30).minutes.do(self.run_threaded, self.job)
        return scheduler

    def job(self):
        headers = {
            'Authorization': 'Bearer {}'.format(self.config['api_key']),
            'Accept': 'application/json',
        }

        logging.info('retrieving data from Solcast')
        r = requests.get(
                self.url_base +
                'world_radiation/estimated_actuals?latitude={}&longitude={}'.format(self.config['latitude'], self.config['longitude']),
                headers=headers)
        # logging.debug('result: status=' + str(r.status_code) + ', json=' + json.dumps(r.json()))

        mqtt_client = self.get_mqtt_client(self.name)
        # tz = dateutil.tz.gettz(self.config['timezone'])
        for measure in r.json()['estimated_actuals']:
            dt = dateutil.parser.parse(measure['period_end'])
            # dt = dt.astimezone(tz)
            data = [
                {
                    'timestamp': int(datetime.datetime.timestamp(dt)),
                    'measurement': 'solcast',
                    'fields': {
                        'global_horizontal_irradiance': measure['ghi'],
                        'direct_normal_irradiance': measure['dni'],
                        'diffuse_horizontal_irradiance': measure['dhi'],
                        'cloud_opacity': measure['cloud_opacity'],
                    },
                }
            ]
            mqtt_client.publish(self.mqtt_topic, json.dumps(data))
