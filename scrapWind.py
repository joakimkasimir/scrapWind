#!/usr/bin/python
from bs4 import BeautifulSoup
import requests
import time
import json
import yaml
from beebotte import *

def loadConfig(filename='config.yaml'):
    with open(filename) as fh:
        content = fh.read()
#    print content
#    print 'yaml:', yaml.dump(yaml.load(content))
    return yaml.load(content)

################################################################

def beebotte_write(config, payload):
    bclient = BBT(config['beebotte']['api_key'], config['beebotte']['secret_key'])

    for resource in payload:
        print "BBT Resource: ", resource, payload[resource]['value'], type(payload[resource]['value'])
        bclient.write('Borstahusen_data', resource, payload[resource]['value'])
    
#    res1 = Resource(bclient, 'Borstahusen_data', 'Vindhastighet_medel')
#    res1.write(11.0)
################################################################

def scrapeDataDog(config, update="False"):
    datan = []
    payload = {}
#    kollaDessaClasser = {'storhetClassName': 'Kol_tx_storhet', 'medelClassName': 'Kol_tx_medel', 'minClassName': 'Kol_tx_mi', 'maxClassName': 'Kol_tx_ma'}
#    typeName = {'Kol_tx_medel': '_medel', 'Kol_tx_mi': '_min', 'Kol_tx_ma': '_max'}

    response = requests.get(config['borstahusenspir']['url'])
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
                        datan[row][value] = float(allColumns[column].get_text().split()[0].replace(',','.'))
                        datan[row]['enhet'] = allColumns[column].get_text().split()[1]

    for unit in datan:
#        print "Unit: ", unit
        if config['borstahusenspir']['kollaDessaClasser']['storhetClassName'] in unit:
            for t, n in config['borstahusenspir']['typeName'].iteritems():
                try:
                    payload[unit['Kol_tx_storhet'].replace(' ','_')+n] = {'value': unit[t], 'timestamp': timestamp, 'context': {'lat': 55.894468, 'lng': 12.799568}}
                except (KeyError) as e:
                    print "Fel DataDog:", e
#    print json.dumps(payload)
    if config['beebotte']['update'] == "True":
        if len(payload) != 0:
            beebotte_write(config, payload)
        else:
            print "No data data collected for Beebotte."

    if config['ubidots']['update'] == "True":
#        print "Update Ubidots: ", update, type(update)
        if len(payload):
            rc = requests.post(config['ubidots']['urlprefix']+'/api/v1.6/devices/'+config['ubidots']['datadog_source']+'/?token='+config['ubidots']['token'], headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
#            print rc
            print rc.content
        else:
            print "No dataDog data collected"
    else:
        print "payload: ", json.dumps(payload)

################################################################

def scrapeSMHI(config, update="False"):
#    seaLevelLocations = {'Barseback': 2099, 'Viken': 2228, 'Klagshamn': 2095, 'Skanor': 30488}
    vattenPayload = {}
    for key, value in config['smhi']['seaLevelLocations'].iteritems():

        headers = {'Content-type': 'application/json'}
        url = config['smhi']['urlprefix']+str(value)+"/period/latest-hour/data.json"
        try:
            response = requests.get(url, headers=headers)
            responseData = response.json()
            vattenPayload[key+'_sea_level'] = {'value': responseData['value'][0]['value'], 'timestamp': responseData['value'][0]['date'], 'context': {'lat': responseData['position'][0]['latitude'], 'lng': responseData['position'][0]['longitude']}}

        except (ValueError) as e:
            print "Fel SMHI:", e
#    print json.dumps(vattenPayload)
    if config['ubidots']['update'] == "True":
        if len(vattenPayload) != 0:
            rc = requests.post(config['ubidots']['urlprefix']+'/api/v1.6/devices/'+config['ubidots']['smhi_source']+'/?token='+config['ubidots']['token'], headers={'Content-Type': 'application/json'}, data=json.dumps(vattenPayload))
#            print rc
            print rc.content
        else:
            print "No SMHI data collected."
    else:
        print json.dumps(vattenPayload)

###############################################################

def lambda_handler(event, context):
    config = loadConfig(filename='config.yaml')
    scrapeDataDog(config)
    scrapeSMHI(config)

if __name__ == '__main__':
    lambda_handler(False, False)
