import hmac
import hashlib
import json
import logging
import plugin
import requests
import schedule
import socket
import tempfile
import time


class FreeboxException(Exception):
    pass


class Freebox(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'freebox'
        self.version = '1.0'
        self.description = 'Freebox Network Statistics Collector'
        self.mqtt_topic = '/net/freebox'

        self.url_base = ''
        self.certificate = tempfile.NamedTemporaryFile(suffix='.pem')
        with open(self.certificate.name, 'w') as f:
            f.write(self.config['certificate'])

    def __del__(self):
        logging.debug(f'deleting temporary file {self.certificate.name}')
        self.certificate.close()

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every(5).seconds.do(self.run_threaded, self.job)
        return scheduler

    def get_session(self, challenge):
        logging.debug(
            'starting new session from challenge: ' +
            ('None' if challenge is None else challenge))
        if 'token' not in self.config:
            r = requests.post(
                self.url_base + 'login/authorize/',
                json={
                    'app_id': f'{self.name}-to-mqtt',
                    'app_name': f'{self.name}-to-mqtt',
                    'app_version': self.version,
                    'device_name': socket.gethostname()
                },
                verify=self.certificate.name)
            if r.status_code != 200 or r.json()['success'] is not True:
                logging.error('unable to get authorization')
                return None

            app_token = r.json()['result']['app_token']
            track_id = r.json()['result']['track_id']

            while True:
                r = requests.get(
                    self.url_base + 'login/authorize/' + str(track_id),
                    verify=self.certificate.name)
                if r.status_code != 200:
                    logging.error('unable to track authorization')
                    return None

                status = r.json()['result']['status']
                if status == 'pending':
                    pass
                elif status == 'timeout':
                    logging.error('authorization request timed out')
                    return None
                elif status == 'denied':
                    logging.error('you denied authorization request')
                    return None
                elif status == 'granted':
                    challenge = r.json()['result']['challenge']
                    break

                time.sleep(0.5)

            self.config['token'] = app_token
            self.config_save()
        else:
            r = requests.get(self.url_base + 'login/', verify=self.certificate.name)
            if r.status_code != 200:
                logging.error('unable to login')
                return None

            challenge = r.json()['result']['challenge']

        logging.debug('new challenge: ' + challenge)
        password = hmac.new(bytes(self.config['token'], 'latin-1'), challenge.encode('latin-1'), hashlib.sha1).hexdigest()
        r = requests.post(
            self.url_base + 'login/session/',
            json={
                'app_id': f'{self.name}-to-mqtt',
                'password': password
            },
            verify=self.certificate.name)
        if r.status_code != 200:
            logging.error('unable to start new session')
            return None

        return r.json()['result']['session_token']

    def job(self):
        url = 'http://mafreebox.freebox.fr/api_version'
        r = requests.get(url)
        if r.status_code != 200:
            raise FreeboxException('unable to get Freebox information')

        base = r.json()['api_base_url']
        version = r.json()['api_version'].split('.')[0]
        self.url_base = f'https://mafreebox.freebox.fr{base}v{version}/'

        token = self.get_session(None)

        logging.info('retrieving data from Freebox')
        r = requests.get(self.url_base + 'connection/', headers={'X-Fbx-App-Auth': token}, verify=self.certificate.name)
        logging.debug('result: status=' + str(r.status_code) + ', json=' + json.dumps(r.json()))
        if r.status_code == 200 and r.json()['success'] is True:
            data = r.json()['result']
            data['time'] = int(time.time())

            mqtt_client = self.get_mqtt_client(self.name)
            mqtt_client.publish(self.mqtt_topic, json.dumps(data))
        else:
            raise FreeboxException('failed to get connection information')
