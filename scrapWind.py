#!/usr/bin/python
# coding: utf-8

from __future__ import print_function
import sys
from bs4 import BeautifulSoup
import requests
import time
import json
import yaml
from beebotte import *
import logging
import os
import pandas as pd
import numpy as np
from datetime import tzinfo, timedelta, datetime
#import datetime
import pickle
import boto3

def loadConfig(filename='config.yaml'):
    with open(filename) as fh:
        content = fh.read()
    logging.debug("configuration: "+content)
#    print 'yaml:', yaml.dump(yaml.load(content))
    return yaml.load(content, Loader=yaml.FullLoader)

################################################################

def beebotte_write(config, payload):
    bclient = BBT(config['beebotte']['api_key'], config['beebotte']['secret_key'])

    for resource in payload:
#        print "BBT Resource: ", resource, payload[resource]['value'], type(payload[resource]['value'])
        bclient.write('Borstahusen_data', resource, payload[resource]['value'])
    logging.debug("BeeBotte updated")    
#    res1 = Resource(bclient, 'Borstahusen_data', 'Vindhastighet_medel')
#    res1.write(11.0)
################################################################

def scrapeDataDog(config, update="False"):
    datan = []
    payload = {}
#    kollaDessaClasser = {'storhetClassName': 'Kol_tx_storhet', 'medelClassName': 'Kol_tx_medel', 'minClassName': 'Kol_tx_mi', 'maxClassName': 'Kol_tx_ma'}
#    typeName = {'Kol_tx_medel': '_medel', 'Kol_tx_mi': '_min', 'Kol_tx_ma': '_max'}
    response = requests.get(config['borstahusenspir']['url'])
    soup = BeautifulSoup(response.content, 'html.parser')
    new_url = soup.find("frame")["src"]
    logging.info("Scraping %s", new_url)

    response = requests.get(new_url)
    timestamp = int(time.time())*1000 # Milliseconds since 1970

    soup = BeautifulSoup(response.content, 'html.parser')

    pList = soup.find_all('p')
    next_p = False
    for i in range(len(pList)):
        if next_p & (str(pList[i])[9:15] == '°C</p>'):
            print(str(pList[i])[9:15])
            print(str(pList[i])[3:-6].split()[0])
            payload['temp_ovregatan'] = {'value': float(str(pList[i])[3:-6].split()[0].replace(',','.')), 'timestamp': timestamp, 'context': {'lat': 55.894823, 'lng': 12.807266}}
            print(payload['temp_ovregatan'])
            next_p = False
        if str(pList[i]) == '<p>Temperatur</p>':
            next_p = True
            print('next_p')
        if str(pList[i])[7:20] == 'rten skapad :':
            #print(str(pList[i])[20:39])

            local_time = time.strptime(str(pList[i])[20:39], "%Y-%m-%d %H:%M:%S") # 2020-12-28 12:46:00
            timestamp = time.mktime(local_time)*1000 # Milliseconds since 1970
        if str(pList[i])[-7:] == 'lux</p>':
            payload['illuminans'] = {'value': str(pList[i])[3:-4].split()[0], 'timestamp': timestamp, 'context': {'lat': 55.894823, 'lng': 12.807266}}
            print(payload['illuminans'])

    allRows = soup.find_all('tr')
    for row in range(len(allRows)):
        datan.append({})
        for key, value in config['borstahusenspir']['kollaDessaClasser'].items():
            if key == 'storhetClassName':
                allColumns = allRows[row].find_all('td', class_=value)
                for column in range(len(allColumns)):
                    datan[row][value] = allColumns[column].get_text()
            else:
                allColumns = allRows[row].find_all('td', class_=value)
                for column in range(len(allColumns)):
                    if allColumns[column].get_text()[0] != '#':
                        logging.debug("Text:"+allColumns[column].get_text())
                        datan[row][value] = float(allColumns[column].get_text().split()[0].replace(',','.'))
                        logging.debug("Datan:"+str(datan[row][value]))
                        datan[row]['enhet'] = allColumns[column].get_text().split()[1]
                        logging.debug("Enhet:"+datan[row]['enhet'])

    for unit in datan:
        if config['borstahusenspir']['kollaDessaClasser']['storhetClassName'] in unit:
            for t, n in config['borstahusenspir']['typeName'].items():
                try:
                    payload[unit['Kol_tx_storhet'].replace(' ','_')+n] = {'value': unit[t], 'timestamp': timestamp, 'context': {'lat': 55.894468, 'lng': 12.799568}}
                except (KeyError) as e:
                    logging.warning("Fel DataDog:"+str(e))


    if config['beebotte']['update'] == "True":
        if len(payload) != 0:
            beebotte_write(config, payload)
        else:
            logging.info("No data data collected for Beebotte.")

    if config['ubidots']['update'] == "True":
        logging.info("Updating UbiDots")
        if len(payload):
            # Minska antalet varden till 10 sa det blir kostandsfritt hos Ubidots
            for varde in ('Vatten_Temperatur_min', 'Vatten_Temperatur_max', 'Luft_Temperatur_min', 'Luft_Temperatur_max', 'Lufttryck_relativ_min', 'Lufttryck_relativ_max'):
                if varde in payload:
                    del payload[varde]
            rc = requests.post(config['ubidots']['urlprefix']+'/api/v1.6/devices/'+config['ubidots']['datadog_source']+'/?token='+config['ubidots']['token'], headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
            logging.info(rc.content)
        else:
            logging.info("No dataDog data collected")
    else:
        print("Payload: "+str(json.dumps(payload)))

    payload['site'] = {'value': 'bss', 'timestamp': timestamp}
    return payload

################################################################

def scrapeSMHI(config, update="False"):
#    seaLevelLocations = {'Barseback': 2099, 'Viken': 2228, 'Klagshamn': 2095, 'Skanor': 30488}
    logging.debug('Start av scrapeSMHI')
    vattenPayload = {}
    for key, value in config['smhi']['seaLevelLocations'].items():

        headers = {'Content-type': 'application/json'}
        url = config['smhi']['urlprefix']+str(value)+"/period/latest-hour/data.json"
        try:
            response = requests.get(url, headers=headers)
            responseData = response.json()
            vattenPayload[key+'_sea_level'] = {'value': responseData['value'][0]['value'], 'timestamp': responseData['value'][0]['date'], 'context': {'lat': responseData['position'][0]['latitude'], 'lng': responseData['position'][0]['longitude']}}
            smhi_timestamp = responseData['value'][0]['date']

        except (ValueError) as e:
            logging.info("Fel SMHI: "+str(e))
    if config['ubidots']['update'] == "True":
        if len(vattenPayload) != 0:
            rc = requests.post(config['ubidots']['urlprefix']+'/api/v1.6/devices/'+config['ubidots']['smhi_source']+'/?token='+config['ubidots']['token'], headers={'Content-Type': 'application/json'}, data=json.dumps(vattenPayload))
            logging.info(rc.content)
        else:
            logging.info("No SMHI data collected.")
    else:
        print(json.dumps(vattenPayload))
        pass
    print(json.dumps(vattenPayload))
    vattenPayload['site'] = {'value': 'smhi', 'timestamp': smhi_timestamp}
    return vattenPayload

###############################################################

class p_data():

    s3_bucket = 'bss-stats'

    def __init__(self):
        self.bss_stats = pd.DataFrame({})

    def read_data_file_from_s3(self, staging=True):
        if staging:
            pickel_file = 'bss_dataframe_staging.pkl'
        else:
            pickel_file = 'bss_dataframe.pkl'
        data_pkl = self.s3_read(self.s3_bucket, pickel_file)
        self.bss_stats = pickle.loads(data_pkl)
        return True

    def s3_read(self, bucket, file_name):
        """
        Read a file from an S3 source.

        Parameters
        ----------
        bucket : str
            bucket name
        file_name: str
            file or key

        Returns
        -------
        content : bytes

        botocore.exceptions.NoCredentialsError
            Botocore is not able to find your credentials. Either specify
            profile_name or add the environment variables AWS_ACCESS_KEY_ID,
            AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN.
            See https://boto3.readthedocs.io/en/latest/guide/configuration.html
        """
        s3_client = boto3.client('s3')
        s3_object = s3_client.get_object(Bucket=bucket, Key=file_name)
        body = s3_object['Body']
        return body.read()

    def write_data_file_s3(self, days_back=None, staging=True):
        if staging:
            pickel_file = 'bss_dataframe_staging.pkl'
        else:
            pickel_file = 'bss_dataframe.pkl'
        self.bss_stats = self.bss_stats.drop_duplicates()
        if days_back:
            td = pd.Timedelta(days_back, unit='days')
            i_start = self.bss_stats.index.max() - td
            mask = (self.bss_stats.index > i_start) & (self.bss_stats.index <= self.bss_stats.index.max())
            self.bss_stats = self.bss_stats.loc[mask]
            #print(self.bss_stats)

        data_pkl = pickle.dumps(self.bss_stats)
        s3_client = boto3.client('s3')
        s3_client.put_object(Body=data_pkl, Bucket=self.s3_bucket, Key=pickel_file, ACL = 'public-read')

    def append_data(self, data):
        print('AAAA', self.bss_stats)
        print(data)
#        {'illuminans': {'value': '1519', 'timestamp': 1609148820000, 'context': {'lat': 55.894823, 'lng': 12.807266}}, 'Vindhastighet_medel': {'value': 7.9, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vindhastighet_min': {'value': 4.0, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vindhastighet_max': {'value': 11.8, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vindriktning_medel': {'value': 107.0, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vindriktning_min': {'value': 104.0, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vindriktning_max': {'value': 116.0, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Lufttryck_relativ_medel': {'value': 983.3, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Luft_Temperatur_medel': {'value': 5.3, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}, 'Vatten_Temperatur_medel': {'value': 2.9, 'timestamp': 1609148820000, 'context': {'lat': 55.894468, 'lng': 12.799568}}}
        data_dict = dict()
        for i in data:
            data_dict[i] = [data[i]['value']]
            dti = pd.to_datetime([datetime.fromtimestamp(data[i]['timestamp']/1000)])

        print('YYYY', data_dict, dti)
#        d = {'illuminans': [data['illuminans']['value']], 'Vindhastighet_medel': [data['Vindhastighet_medel']['value']], 'Vindhastighet_min': [data['Vindhastighet_min']['value']], 'Vindhastighet_max': [data['Vindhastighet_max']['value']], 'Vindriktning_medel': [data['Vindriktning_medel']['value']], 'Vindriktning_min': [data['Vindriktning_min']['value']], 'Vindriktning_max': [data['Vindriktning_max']['value']], 'Lufttryck_relativ_medel': [data['Lufttryck_relativ_medel']['value']], 'Luft_Temperatur_medel': [data['Luft_Temperatur_medel']['value']], 'Vatten_Temperatur_medel': [data['Vatten_Temperatur_medel']['value']]}
        df_latest = pd.DataFrame(data_dict, index=dti)
        print('Joakim', df_latest)
        self.bss_stats = self.bss_stats.append(df_latest)
        print('ZZZZZZ', self.bss_stats.index.max())

###############################################################

def lambda_handler(event, context):

    ### Read configuration
    config = loadConfig(filename='config.yaml')

    ### Set logging
    logger = logging.getLogger()
    numeric_level = getattr(logging, config['loglevel'].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logger.setLevel(numeric_level)
    logging.info("AWS_LAMBDA_FUNCTION_VERSION: %s", os.environ.get('AWS_LAMBDA_FUNCTION_VERSION'))

    wind_pandas = p_data()
    wind_pandas.read_data_file_from_s3(staging=False)
    wind_pandas.append_data(scrapeDataDog(config))
    wind_pandas.append_data(data = scrapeSMHI(config))
    wind_pandas.write_data_file_s3(days_back=8, staging=False)

###############################################################

if __name__ == '__main__':
    lambda_handler(False, False)
