import datetime
import dateutil.parser
import fitbit
import json
import logging
import plugin
import schedule
import time
import os
import sys


def transform_body_log_fat_datapoint(datapoint):
    ret_dps = [{
        'dateTime': datetime.fromtimestamp(int(datapoint['logId']) / 1000),
        'meas': 'body_log',
        'series': 'fat_fat',
        'value': datapoint.get('fat', 0.0)
    }]
    logging.debug('returning body_log_fat datapoints: %s', ret_dps)
    return ret_dps


def transform_body_log_weight_datapoint(datapoint):
    ret_dps = [
        {
            'dateTime': datetime.fromtimestamp(int(datapoint['logId'])/1000),
            'meas': 'body_log',
            'series': 'weight_bmi',
            'value': datapoint.get('bmi', 0.0)
        },
        {
            'dateTime': datetime.fromtimestamp(int(datapoint['logId'])/1000),
            'meas': 'body_log',
            'series': 'weight_fat',
            'value': datapoint.get('fat', 0.0)
        },
        {
            'dateTime': datetime.fromtimestamp(int(datapoint['logId'])/1000),
            'meas': 'body_log',
            'series': 'weight_weight',
            'value': datapoint.get('weight', 0.0)
        }
    ]
    logging.debug('returning body_log_weight datapoints: %s', ret_dps)
    return ret_dps


def transform_activities_heart_datapoint(datapoint):
    logging.debug('transform_activities_heart_datapoint: %s', datapoint)
    d_t = datapoint['dateTime']
    dp_value = datapoint['value']
    ret_dps = [
        {
            'dateTime': d_t,
            'meas': 'activities',
            'series': 'restingHeartRate',
            'value': dp_value.get('restingHeartRate', 0.0)
        }
    ]
    if dp_value.get('heartRateZones'):
        for zone in dp_value['heartRateZones']:
            for one_val in ['caloriesOut', 'max', 'min', 'minutes']:
                series_name = '_'.join(['hrz', zone['name'].replace(' ', '_').lower(), one_val])
                ret_dps.append({
                    'dateTime': d_t,
                    'meas': 'activities',
                    'series': series_name,
                    'value': zone.get(one_val, 0.0)
                })
    logging.debug('returning activities_heart datapoints: %s', ret_dps)
    return ret_dps


def transform_sleep_datapoint(datapoint):
    d_t = datapoint['startTime']
    ret_dps = [
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'duration',
            'value': datapoint.get('duration', 0) / 1000
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'efficiency',
            'value': datapoint.get('efficiency')
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'isMainSleep',
            'value': datapoint.get('isMainSleep', False)
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'timeInBed',
            'value': datapoint.get('timeInBed')
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'minutesAfterWakeup',
            'value': datapoint.get('minutesAfterWakeup')
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'minutesAsleep',
            'value': datapoint.get('minutesAsleep')
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'minutesAwake',
            'value': datapoint.get('minutesAwake')
        },
        {
            'dateTime': d_t,
            'meas': 'sleep',
            'series': 'minutesToFallAsleep',
            'value': datapoint.get('minutesToFallAsleep')
        }
    ]
    if datapoint.get('levels'):
        if datapoint.get('summary'):
            for one_level, dict_level in datapoint['levels']['summary'].items():
                for one_val in ['count', 'minutes', 'thirtyDayAvgMinutes']:
                    ret_dps.append({
                        'dateTime': d_t,
                        'meas': 'sleep_levels',
                        'series': one_level.lower() + '_' + one_val,
                        'value': dict_level.get(one_val)
                    })
        if datapoint.get('data'):
            for data_entry in datapoint['levels']['data']:
                for one_val in ['level', 'seconds']:
                    ret_dps.append({
                        'dateTime': data_entry['datetime'],
                        'meas': 'sleep_data',
                        'series': 'level_' + data_entry['level'],
                        'value': data_entry['seconds']
                    })
        if datapoint.get('shortData'):
            for data_entry in datapoint['levels']['shortData']:
                for one_val in ['level', 'seconds']:
                    ret_dps.append({
                        'dateTime': data_entry['datetime'],
                        'meas': 'sleep_shortData',
                        'series': 'level_' + data_entry['level'],
                        'value': data_entry['seconds']
                    })
    logging.debug('returning sleep datapoints: %s', ret_dps)
    return ret_dps


class Fitbit(plugin.Plugin):
    def __init__(self):
        super().__init__()
        self.active = True
        self.name = 'fitbit'
        self.version = '1.0'
        self.description = 'Fitbit Collector'
        self.mqtt_topic = '/health/fitbit'

        self.api_requests = 0
        self.api_pause_until = 0

    def scheduler(self):
        scheduler = schedule.Scheduler()
        scheduler.every(15).minutes.do(self.run_threaded, self.job)
        return scheduler

    SERIES = {
        'activities': {
            # 'activityCalories': None,  # dateTime, value
            # 'calories': None,  # dateTime, value
            # 'caloriesBMR': None,  # dateTime, value
            'distance': None,  # dateTime, value
            'elevation': None,  # dateTime, value
            'floors': None,  # dateTime, value
            'heart': {
                # https://dev.fitbit.com/build/reference/web-api/heart-rate/
                'key_series': 'restingHeartRate',
                'transform': transform_activities_heart_datapoint
            },
            # 'minutesFairlyActive': None,  # dateTime, value
            # 'minutesLightlyActive': None,  # dateTime, value
            # 'minutesSedentary': None,  # dateTime, value
            # 'minutesVeryActive': None,  # dateTime, value
            'steps': None  # dateTime, value
        },
        'activities_tracker': [
            # 'activityCalories',  # dateTime, value
            # 'calories',  # dateTime, value
            'distance',  # dateTime, value
            'elevation',  # dateTime, value
            'floors',  # dateTime, value
            'minutesFairlyActive',  # dateTime, value
            'minutesLightlyActive',  # dateTime, value
            'minutesSedentary',  # dateTime, value
            'minutesVeryActive',  # dateTime, value
            'steps'  # dateTime, value
        ],
        'sleep': {
            'sleep': {
                'key_series': 'efficiency',
                # supercomplex type: https://dev.fitbit.com/build/reference/web-api/sleep/
                'transform': transform_sleep_datapoint
            }
        }
    }

    # Body series have max 31 days at a time, be a bit more conservative
    REQUEST_INTERVAL = datetime.timedelta(days=7)

    def write_updated_credentials(self, info):
        self.config['access_token'] = info['access_token']
        self.config['refresh_token'] = info['refresh_token']
        self.config_save()

    def fitbit_fetch_datapoints(self, fitc, meas, series, resource, intervals_to_fetch):
        datapoints = []
        for one_tuple in intervals_to_fetch:
            results = None
            while True:
                try:
                    self.api_requests += 1
                    results = fitc.time_series(resource, base_date=one_tuple[0], end_date=one_tuple[1])
                    break
                except fitbit.exceptions.Timeout:
                    logging.warning('Request timed out, retrying in 15 seconds...')
                    time.sleep(15)
                except fitbit.exceptions.HTTPServerError as ex:
                    logging.warning('Server returned exception (5xx), retrying in 15 seconds (%s)', ex)
                    time.sleep(15)
                except fitbit.exceptions.HTTPTooManyRequests:
                    # 150 API calls done, and python-fitbit doesn't provide the retry-after header, so stop trying
                    # and allow the limit to reset, even if it costs us one hour
                    logging.info('API limit reached, pause for 3610 seconds!')
                    self.api_pause_until = int(time.time()) + 3610
                except Exception as ex:
                    logging.exception('Got some unexpected exception (%s)', ex)
                    raise

            if not results:
                logging.error('Error trying to fetch results, bailing out')
                sys.exit(1)

            logging.debug('full_request: %s', results)
            for one_d in list(results.values())[0]:
                logging.debug('Creating datapoint for %s, %s, %s', meas, series, one_d)
                datapoints.append(one_d)
        return datapoints

    def create_api_datapoint_meas_series(self, measurement, series, value, in_dt):
        if not value:
            value = 0.0
        try:
            value = float(value)
        except Exception:
            pass

        return {
            "measurement": measurement,
            "timestamp": int(datetime.datetime.timestamp(dateutil.parser.parse(in_dt))),
            "fields": {series: value}
        }

    def job(self):
        if int(time.time()) < self.api_pause_until:
            logging.info('Fitbit api pause until ' + str(datetime.fromtimestamp(self.api_pause_until)))
            return

        self.api_pause_until = 0
        logging.info('retrieving data from Fitbit')

        today = datetime.date.today()
        yesterday = today - self.REQUEST_INTERVAL

        mqtt_client = self.get_mqtt_client(self.name)

        fitc = fitbit.Fitbit(
            self.config['client_id'],
            self.config['client_secret'],
            access_token=self.config['access_token'],
            refresh_token=self.config['refresh_token'],
            refresh_cb=self.write_updated_credentials,
            system=fitbit.Fitbit.METRIC)

        # avoid OAuth/https exception
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        for meas, series_list in self.SERIES.items():
            for series in series_list:
                if meas != series:
                    resource = f'{meas}/{series}'
                else:
                    resource = meas

                resource = resource.replace('_', '/', 1)

                logging.debug(f'resource={resource}')

                # key_series = series
                # if isinstance(series_list, dict) and series_list.get(series):
                #     # Datapoints are retrieved with all keys in the same dict, so makes no sense to retrieve individual
                #     # series names. Use one series as the key series.
                #     key_series = series_list[series]['key_series']

                if meas == 'sleep':
                    fitc.API_VERSION = '1.2'
                datapoints = self.fitbit_fetch_datapoints(fitc, meas, series, resource, [[yesterday, today]])
                if meas == 'sleep':
                    fitc.API_VERSION = '1'

                converted_dps = []
                for one_d in datapoints:
                    if not one_d:
                        continue
                    if isinstance(series_list, dict) and series_list.get(series):
                        new_dps = series_list[series]['transform'](one_d)
                        for one_dd in new_dps:
                            converted_dps.append(
                                self.create_api_datapoint_meas_series(
                                    one_dd['meas'], one_dd['series'], one_dd['value'], one_dd['dateTime']))
                    else:
                        converted_dps.append(
                            self.create_api_datapoint_meas_series(
                                meas, series, one_d.get('value'), one_d.get('dateTime')))

                # precision = 'h'
                # if meas == 'sleep':
                #     precision = 's'

                for data in converted_dps:
                    logging.debug(json.dumps(data))
                    mqtt_client.publish(self.mqtt_topic, json.dumps([data]))
