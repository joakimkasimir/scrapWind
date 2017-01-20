#!/usr/bin/python
from bs4 import BeautifulSoup
import requests
import time
import json
import yaml

def loadConfig(filename='config.yaml'):
    with open(filename) as fh:
        content = fh.read()
#    print content
#    print 'yaml:', yaml.dump(yaml.load(content))
    return yaml.load(content)

def scrape(config, update=False):
    datan = []
    payload = {}
    kollaDessaClasser = {'storhetClassName': 'Kol_tx_storhet', 'medelClassName': 'Kol_tx_medel', 'minClassName': 'Kol_tx_mi', 'maxClassName': 'Kol_tx_ma'}
    typeName = {'Kol_tx_medel': '_medel', 'Kol_tx_mi': '_min', 'Kol_tx_ma': '_max'}
#    seaLevelLocations = {'Barseback': 2099, 'Viken': 2228, 'Klagshamn': 2228, 'Skanor': 30488, 'Ystad': 2093}
    seaLevelLocations = {'Barseback': 2099, 'Viken': 2228, 'Klagshamn': 2228, 'Skanor': 30488}

    response = requests.get(config['borstahusenspir_url'])
    timestamp = int(time.time())*1000 # Milliseconds since 1970

    soup = BeautifulSoup(response.content, 'html.parser')

    pList = soup.find_all('p')
    for i in range(len(pList)):
        if str(pList[i])[-7:] == 'lux</p>':
            payload['illuminans'] = {'value': str(pList[i])[3:-4].split()[0], 'timestamp': timestamp, 'context': {'lat': 55.894823, 'lng': 12.807266}}

    allRows = soup.find_all('tr')
    for row in range(len(allRows)):
        datan.append({})
        for key, value in kollaDessaClasser.iteritems():
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
        if kollaDessaClasser['storhetClassName'] in unit:
            for t, n in typeName.iteritems():
                try:
                    payload[unit['Kol_tx_storhet'].replace(' ','_')+n] = {'value': unit[t], 'timestamp': timestamp, 'context': {'lat': 55.894468, 'lng': 12.799568}}
                except (KeyError) as e:
                    pass

    vattenPayload = {}
    for key, value in seaLevelLocations.iteritems():

        headers = {'Content-type': 'application/json'}
        url = "http://opendata-download-ocobs.smhi.se/api/version/latest/parameter/6/station/"+str(value)+"/period/latest-hour/data.json"
        response = requests.get(url, headers=headers)
        responseData = response.json()
        vattenPayload[key+'_sea_level'] = {'value': responseData['value'][0]['value'], 'timestamp': responseData['value'][0]['date'], 'context': {'lat': responseData['position'][0]['latitude'], 'lng': responseData['position'][0]['longitude']}}

#    print json.dumps(payload)
    if update:
        rc = requests.post(config['ubidots_urlprefix']+'/api/v1.6/devices/'+config['ubidots_source']+'/?token='+config['ubidots_token'], headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        print rc
        print rc.content
        rc = requests.post(config['ubidots_urlprefix']+'/api/v1.6/devices/'+'smhi'+'/?token='+config['ubidots_token'], headers={'Content-Type': 'application/json'}, data=json.dumps(vattenPayload))
        print rc
        print rc.content
    else:
        print json.dumps(payload)
        print json.dumps(vattenPayload)


def lambda_handler(event, context):
    config = loadConfig(filename='config.yaml')
    if config['ubidots_update'] == 'True':
        scrape(config, update=True)
    else:
        scrape(config, update=False)

if __name__ == '__main__':
    lambda_handler(False, False)
