#!/usr/bin/env python
""" Class to use the ripe atlas platform to do nagios checks """
import sys
import time
import argparse
import requests
import json
import pprint

class Measurement:
    """Parent object for an atlas Measurement"""

    def __init__(self, probe_id, payload):
        """Initiate generic message data"""
        self.probe_id = probe_id
        self.payload = payload
        self.check_time = self.payload[1]
        self.msg = "%s (%s)"

    @staticmethod
    def add_args(parser):
        """add measurement arguments"""
        parser.add_argument('-v', '--verbose', action='count',
                help='increase verbosity')
        parser.add_argument("measurement_id",
                help="Measurement ID to check")
        parser.add_argument('-w', '--warn-probes', type=int, default=2,
                help='WARN if % probes have a warn condition')
        parser.add_argument('-c', '--crit-probes', type=int, default=1,
                help='ERROR if % probes have a warn condition')
        parser.add_argument('-W', '--warn-measurement', type=int, default=2,
                help='WARN if % measurement have a warn condition')
        parser.add_argument('-C', '--crit-measurement', type=int, default=1,
                help='ERROR if % measurement have a warn condition')
        parser.add_argument('--max_measurement_age', type=int, default=3600,
                help='The max age of a measurement in unix time')

    def check_measurement_age(self, max_age, message):
        """Check if a measerment is fresh enough"""
        min_time = time.time() - max_age
        check_time_str = time.ctime(self.check_time)
        if self.check_time < min_time:
            message.add_error(self.probe_id, self.msg % \
                    ("measurement to old", check_time_str))
        else:
            message.add_ok(self.probe_id, self.msg % \
                    ("measurement fresh", check_time_str))

    def check_string(self, check_string, Measurement_string,
            check_type, message):
        """Generic check to compare two strings"""
        if check_string == Measurement_string:
            message.add_ok(self.probe_id, self.msg % \
                    (check_type, Measurement_string))
        else:
            message.add_error(self.probe_id, self.msg % \
                     (check_type, Measurement_string))

    def check(self, args, message):
        """main check fucntion"""
        if args.max_measurement_age != False:
            self.check_measurement_age(
                    args.max_measurement_age, message)


class MeasurementSSL(Measurement):
    """Object for an atlas SSL Measurement"""

    def __init__(self, probe_id, payload):
        """Initiate object"""
        #super(Measurement, self).__init__(payload)
        Measurement.__init__(self, probe_id, payload)
        self.common_name = self.payload[2][0][0]
        self.expiry = time.mktime(
                time.strptime(self.payload[2][0][4],"%Y%m%d%H%M%SZ"))
        self.sha1 = self.payload[2][0][5]

    @staticmethod
    def add_args(subparser):
        """add SSL arguments"""
        parser = subparser.add_parser('ssl', help='SSL check')
        Measurement.add_args(parser)
        parser.add_argument('--common_name',
                help='Ensure a cert has this cn')
        parser.add_argument('--sslexpiry', type=int, default=30,
                help="Ensure certificate dosne't expire in x days")
        parser.add_argument('--sha1hash',
                help="Ensure certificate has this sha1 hash")

    def check_expiry(self, warn_expiry, message):
        """Check if the certificat is going to expire before warn_expiry"""
        current_time = time.time()
        warn_time = current_time - (warn_expiry * 60 * 60 * 24)
        expiry_str = time.ctime(self.expiry)
        if self.expiry < current_time:
            message.add_error(self.probe_id, self.msg % (
                    "certificate expierd", expiry_str))
        elif self.expiry < warn_time:
            message.add_warn(self.probe_id, self.msg % (
                    "certificate expires soon", expiry_str))
        else:
            message.add_ok(self.probe_id, self.msg % (
                    "certificate expiry good", expiry_str))

    def check(self, args, message):
        """Main SSL check routine"""
        Measurement.check(self, args, message)
        if args.sha1hash:
            self.check_string( args.sha1hash,
                    self.sha1, 'sha1hash', message)
        if args.common_name:
            self.check_string( args.common_name,
                    self.common_name, 'cn', message)
        if args.sslexpiry:
            self.check_expiry(args.sslexpiry, message)


class MeasurementPing(Measurement):
    """Object for an atlas Ping Measurement"""

    def __init__(self, probe_id, payload):
        """Initiate object"""
        #super(Measurement, self).__init__(self, payload)
        Measurement.__init__(self, probe_id, payload)
        self.avg_rtt = self.payload[0]

    @staticmethod
    def add_args(subparser):
        """add Ping arguments"""
        parser = subparser.add_parser('ping', help='SSL check')
        Measurement.add_args(parser)
        parser.add_argument('--rtt_max',
                help='Ensure the max ttl is below this')
        parser.add_argument('--rtt_min',
                help='Ensure the min ttl is below this')
        parser.add_argument('--rtt_avg',
                help='Ensure the avg ttl is below this')

    def check_rtt(self, check_type, rtt, message):
        """Check the return trip time islower then rtt"""
        msg = "desierd (%s), real (%s)" % (rtt, self.avg_rtt)
        if self.avg_rtt < rtt:
            message.add_ok(self.probe_id, self.msg % (
                     msg, "Ping %s" % check_type))
        else:
            message.add_error(self.probe_id, self.msg % (
                    msg, "Ping %s" % check_type))

    def check(self, args, message):
        """Main ping check routine"""
        Measurement.check(self, args, message)

        if args.rtt_min:
            self.check_rtt("min", args.rtt_min, message)
        if args.rtt_max:
            self.check_rtt("max", args.rtt_max, message)
        if args.rtt_avg:
            self.check_rtt("avg", args.rtt_avg, message)


class MeasurementHTTP(Measurement):
    """Object for an atlas HTTP Measurement"""

    def __init__(self, probe_id, payload):
        """Initiate object"""
        #super(Measurement, self).__init__(self, payload)
        Measurement.__init__(self, probe_id, payload)
        try:
            self.status = self.payload[2][0]['res']
        except KeyError:
            try:
                self.status = self.payload[2][0]['dnserr']
            except KeyError:
                #probably a time out, should use a better status code
                self.status = 500

    @staticmethod
    def add_args(subparser):
        """add HTTP arguments"""
        parser = subparser.add_parser('http', help='SSL check')
        Measurement.add_args(parser)
        parser.add_argument('--status_code', type=int, default=200,
                help='Ensure the site returns this status code')

    def check_status(self, check_status, message):
        """check the HTTP status is the same as check_status"""
        msg = "desierd (%s), real (%s)" % \
                (check_status, self.status)
        try:
            if int(self.status) == int(check_status):
                message.add_ok(self.probe_id, self.msg % (
                    msg, "HTTP Status Code"))
            else:
                message.add_error(self.probe_id, self.msg % (
                    msg, "HTTP Status Code"))
        except ValueError:
            message.add_error(self.probe_id, self.msg % (
                    msg, "HTTP Status Code"))

    def check(self, args, message):
        """Main HTTP check routine"""
        Measurement.check(self, args, message)
        if args.status_code:
            self.check_status(args.status_code, message)


class MeasurementDns(Measurement):
    """Parent class for a DNS measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        Measurement.__init__(self, probe_id, payload)
        self.additional = self.payload[2]['additional']
        self.question = { 'qname': "", 'qtype': "", 'question':"" }
        self.question['qname'], _, self.question['qtype'] = \
                self.payload[2]['question'].split()
        self.authority = self.payload[2]['authority']
        self.rcode = self.payload[2]['rcode']
        self.flags = self.payload[2]['flags']
        self.answer = []
        if self.rcode == "NOERROR":
            self.answer_raw = ensure_list(self.payload[2]['answer'])

    @staticmethod
    def add_args(parser):
        """add default DNS args"""
        Measurement.add_args(parser)
        parser.add_argument('--flags',
                help='Coma seperated list o flags to expect')
        parser.add_argument('--rcode',
                help='rcode to expect')


    def check_rcode(self, rcode, message):
        """Check the RCODE is the same as rcode"""
        msg = "desierd (%s), real (%s)" % ( rcode, self.rcode)
        if self.rcode == rcode:
            message.add_ok(self.probe_id, self.msg % (
                    msg, "DNS RCODE"))
        else:
            message.add_error(self.probe_id, self.msg % (
                    msg, "DNS RCODE"))

    def check_flags(self, flags, message):
        """Check the flags returned in the check are the same as flags"""
        for flag in flags.split(","):
            if flag in self.flags.split():
                message.add_ok(self.probe_id, self.msg % (
                        "Flag found", flag))
            else:
                message.add_error(self.probe_id, self.msg % (
                        "Flag Missing ", flag))

    def check(self, args, message):
        """Main Check routine"""
        Measurement.check(self, args, message)

        if args.rcode:
            self.check_rcode(args.rcode, message)
        if args.flags:
            self.check_flags(args.flags, message)


class MeasurementDnsA(MeasurementDns):
    """class for a DNS IN A measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsA(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('A', help='A DNS check')
        MeasurementDns.add_args(parser)
        parser.add_argument('--cname-record',
                help='Ensure the RR set from the answer \
                        contains a CNAME record with this string')
        parser.add_argument('--a-record',
                help='Ensure the RR set from the answer \
                        contains a A record with this string')

    def check(self, args, message):
        a_record = False
        cname_record = False
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)
            if args.a_record and ans.rrtype == "A":
                a_record = True
            if args.cname_record and ans.rrtype == "CNAME":
                cname_record = True
        if args.a_record and not a_record:
            message.add_error(self.probe_id, self.msg % (
                "No A Records Found", ""))
        if args.cname_record and not cname_record:
            message.add_error(self.probe_id, self.msg % (
                "No CNAME Records Found", ""))


class MeasurementDnsAAAA(MeasurementDns):
    """class for a DNS IN AAAA measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsAAAA(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('AAAA', help='AAAA DNS check')
        MeasurementDns.add_args(parser)
        parser.add_argument('--cname-record',
                help='Ensure the RR set from the answer \
                        contains a CNAME record with this string')
        parser.add_argument('--aaaa-record',
                help='Ensure the RR set from the answer \
                        contains a A record with this string')

    def check(self, args, message):
        aaaa_record = False
        cname_record = False
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)
            if args.aaaa_record and ans.rrtype == "AAAA":
                aaaa_record = True
            if args.cname_record and ans.rrtype == "CNAME":
                cname_record = True
        if args.aaaa_record and not aaaa_record:
            message.add_error(self.probe_id, self.msg % (
                "No AAAA Records Found", ""))
        if args.cname_record and not cname_record:
            message.add_error(self.probe_id, self.msg % (
                "No CNAME Records Found", ""))


class MeasurementDnsCNAME(MeasurementDns):
    """class for a DNS IN CNAME measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsCNAME(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('CNAME', help='CNAME DNS check')
        MeasurementDns.add_args(parser)
        parser.add_argument('--cname-record',
                help='Ensure the RR set from the answer \
                        contains a CNAME record with this string')

    def check(self, args, message):
        cname_record = False
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)
            if args.cname_record and ans.rrtype == "CNAME":
                cname_record = True
        if args.cname_record and not cname_record:
            message.add_error(self.probe_id, self.msg % (
                "No CNAME Records Found", ""))


class MeasurementDnsDS(MeasurementDns):
    """class for a DNS IN DS measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsDS(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('DS', help='CNAME DS check')
        MeasurementDns.add_args(parser)
        parser.add_argument('--keytag',
                help='Ensure the RR set from the answer \
                        contains a keytag record with this string')
        parser.add_argument('--algorithm',
                help='Ensure the RR set from the answer \
                        contains a algorithm record with this string')
        parser.add_argument('--digest_type',
                help='Ensure the RR set from the answer \
                        contains a digest type record with this string')
        parser.add_argument('--digest',
                help='Ensure the RR set from the answer \
                        contains a digest record with this string')

    def check(self, args, message):
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)


class MeasurementDnsDNSKEY(MeasurementDns):
    """class for a DNS IN DNSKEY measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsDNSKEY(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('DNSKEY', help='CNAME DNSKEY check')
        MeasurementDns.add_args(parser)

    def check(self, args, message):
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)


class MeasurementDnsSOA(MeasurementDns):
    """class for a DNS IN SOA measurement"""

    def __init__(self, probe_id, payload):
        """Initiate Object"""
        #super(Measurement, self).__init__(self, payload)
        MeasurementDns.__init__(self, probe_id, payload)
        for ans in self.answer_raw:
            self.answer.append(AnswerDnsSOA(self.probe_id, ans))

    @staticmethod
    def add_args(subparser):
        parser = subparser.add_parser('SOA', help='CNAME SOA check')
        MeasurementDns.add_args(parser)
        parser.add_argument('--mname',
                help='Ensure the soa has this mname')
        parser.add_argument('--rname',
                help='Ensure the soa has this rname')
        parser.add_argument('--serial',
                help='Ensure the soa has this serial')
        parser.add_argument('--refresh',
                help='Ensure the soa has this refresh')
        parser.add_argument('--update',
                help='Ensure the soa has this update')
        parser.add_argument('--expire',
                help='Ensure the soa has this expire')
        parser.add_argument('--nxdomain',
                help='Ensure the soa has this nxdomain')

    def check(self, args, message):
        MeasurementDns.check(self, args, message)
        for ans in self.answer:
            ans.check(args, message)