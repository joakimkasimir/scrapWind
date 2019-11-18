#!/usr/bin/python
from __future__ import print_function
import sys
from bs4 import BeautifulSoup
import requests
import time
import json
import yaml
from beebotte import *
import logging

def loadConfig(filename='config.yaml'):
    with open(filename) as fh:
        content = fh.read()
    logging.debug("configuration: "+content)
#    print 'yaml:', yaml.dump(yaml.load(content))
    return yaml.load(content)

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
    for i in range(len(pList)):
        if str(pList[i])[-7:] == 'lux</p>':
            payload['illuminans'] = {'value': str(pList[i])[3:-4].split()[0], 'timestamp': timestamp, 'context': {'lat': 55.894823, 'lng': 12.807266}}

    allRows = soup.find_all('tr')
    for row in range(len(allRows)):
        datan.append({})
        for key, value in config['borstahusenspir']['kollaDessaClasser'].iteritems():
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
            for t, n in config['borstahusenspir']['typeName'].iteritems():
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

################################################################

def scrapeSMHI(config, update="False"):
#    seaLevelLocations = {'Barseback': 2099, 'Viken': 2228, 'Klagshamn': 2095, 'Skanor': 30488}
    logging.debug('Start av scrapeSMHI')
    vattenPayload = {}
    for key, value in config['smhi']['seaLevelLocations'].iteritems():

        headers = {'Content-type': 'application/json'}
        url = config['smhi']['urlprefix']+str(value)+"/period/latest-hour/data.json"
        try:
            response = requests.get(url, headers=headers)
            responseData = response.json()
            vattenPayload[key+'_sea_level'] = {'value': responseData['value'][0]['value'], 'timestamp': responseData['value'][0]['date'], 'context': {'lat': responseData['position'][0]['latitude'], 'lng': responseData['position'][0]['longitude']}}

        except (ValueError) as e:
            logging.info("Fel SMHI: "+str(e))
    if config['ubidots']['update'] == "asdfasdfasdf":
        if len(vattenPayload) != 0:
            rc = requests.post(config['ubidots']['urlprefix']+'/api/v1.6/devices/'+config['ubidots']['smhi_source']+'/?token='+config['ubidots']['token'], headers={'Content-Type': 'application/json'}, data=json.dumps(vattenPayload))
        else:
            logging.info("No SMHI data collected.")
    else:
        print(json.dumps(vattenPayload))

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

    scrapeDataDog(config)
#    scrapeSMHI(config)

if __name__ == '__main__':
    lambda_handler(False, False)
