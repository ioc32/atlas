#!/usr/bin/env python
""" Class to use the ripe atlas platform to do nagios checks """
import sys
import time
import argparse
import requests
import json
import pprint

from measurements import *

def ensure_list(list_please):
    """make @list_please a list if it isn't one already"""
    if type(list_please) != list:
        return [(list_please)]
    else:
        return list_please

def get_response(url):
    '''Fetch a Json Object from url'''
    headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            }
    try:
        request = requests.get(url,headers=headers)
        request.raise_for_status()
    except requests.exceptions.RequestException as error:
        print '''Unknown: Fatal error when reading request: %s''' % error
        sys.exit(3)

    if request.status_code in [200, 201, 202]:
        return request.json()
    else:
        print '''Unexpected non-fatal status code: %s''' % request.status_code
        sys.exit(3)

def get_measurements(measurement_id):
    '''Fetch a measuerment with it=measurement_id'''
    url = "https://atlas.ripe.net/api/v1/measurement/%s/latest/" \
            % measurement_id
    return get_response(url)

def parse_measurements(measurements, measurement_type, message):
    '''Parse the measuerment'''
    parsed_measurements = []
    for measurement in measurements:
        probe_id = measurement[1]
        if measurement[5] == None:
            message.add_error(probe_id, "No data")
            continue
        parsed_measurements.append(
            {
                'a': MeasurementDnsA,
                'aaaa': MeasurementDnsAAAA,
                'cname': MeasurementDnsCNAME,
                'ds': MeasurementDnsDS,
                'dnskey' : MeasurementDnsDNSKEY,
                'soa': MeasurementDnsSOA,
                'http': MeasurementHTTP,
                'ping': MeasurementPing,
                'ssl': MeasurementSSL,
            }.get(measurement_type, Measurement)(probe_id, measurement[5])
        )
        #parsed_measurements.append(MeasurementSSL(probe_id, measurement[5]))
    return parsed_measurements

def check_measurements(measurements, args, message):
    '''check the measuerment'''
    for measurement in measurements:
        measurement.check(args, message)
