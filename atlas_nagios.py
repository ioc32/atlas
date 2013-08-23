#!/usr/bin/env python
""" Class to use the ripe atlas platform to do nagios checks """
import argparse

from messages import ProbeMessage
from measurements import *
from dns_answers import *
from utils import ensure_list,get_response,get_measurements,check_measurements, parse_measurements

def arg_parse():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers( 
            title="Supported Measuerment types", dest='name')

    #measuerement types
    MeasurementSSL.add_args(subparsers)
    MeasurementPing.add_args(subparsers)
    MeasurementHTTP.add_args(subparsers)
    dns_parser = subparsers.add_parser('dns', help='DNS check')
    dns_subparsers = dns_parser.add_subparsers( 
            title="Supported DNS Measuerment types", dest='name')
    MeasurementDnsA.add_args(dns_subparsers)
    MeasurementDnsAAAA.add_args(dns_subparsers)
    MeasurementDnsCNAME.add_args(dns_subparsers)
    MeasurementDnsDS.add_args(dns_subparsers)
    MeasurementDnsDNSKEY.add_args(dns_subparsers)
    MeasurementDnsSOA.add_args(dns_subparsers)

    return parser.parse_args()

def main():
    """main function"""
    args = arg_parse()
    message = ProbeMessage(args.verbose)
    measurements =  get_measurements(args.measurement_id)
    parsed_measurements = parse_measurements(
            measurements, args.name, message)
    check_measurements(parsed_measurements, args, message)
    message.exit()

if __name__ == '__main__':
    main()
