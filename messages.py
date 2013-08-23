#!/usr/bin/env python
""" Class to use the ripe atlas platform to do nagios checks """
import sys
import time
import argparse
import requests
import json
import pprint

class ProbeMessage:
    """Object to store nagios messages"""
    def __init__(self, verbose):
        """
        Initialise Object
        verbose is an interger indicating how Much information to return
        """
        #need to group these by probe id
        self.error = dict()
        self.warn = dict()
        self.ok = dict()
        self.verbose = verbose
        self.error_threshold = 0.15

    def add_error(self, probe, message):
        """Add an error message"""
        try:
            self.error[probe].append(message)
        except KeyError:
            self.error[probe] = [message]

    def add_warn(self, probe, message):
        """Add an warn message"""
        try:
            self.warn[probe].append(message)
        except KeyError:
            self.warn[probe] = [message]

    def add_ok(self, probe, message):
        """Add an ok message"""
        try:
            self.ok[probe].append(message)
        except KeyError:
            self.ok[probe] = [message]

    def exit(self):
        """Parse the message and exit correctly for nagios"""
        result_count = len(self.error) + len(self.warn) + len(self.ok)
        #self.verbose = 2
        #self.verbose = 1

        if len(self.error) > result_count * self.error_threshold:
            if self.verbose > 0:
                print "ERROR: %d: %s" % (len(self.error),
                        ", ".join(map(str,self.error.items())))
                if self.verbose > 1:
                    print "WARN: %d: %s" % (len(self.warn),
                            ", ".join(map(str,self.warn.items())))
                    print "OK: %d: %s" % (len(self.ok),
                        ", ".join(map(str,self.ok.items())))
            else:
                print "ERROR: %d" % len(self.error)
            sys.exit(2)
        elif len(self.warn) > 0:
            if self.verbose > 0:
                print "WARN: %d: %s" % (len(self.warn),
                        ", ".join(map(str,self.warn.items())))
                if self.verbose > 1:
                    print "OK: %d: %s" % (len(self.ok),
                        ", ".join(map(str,self.ok.items())))
            else:
                print "WARN: %d" % len(self.warn)
            sys.exit(1)
        else:
            if self.verbose > 1:
                print "OK: %d: %s" % (len(self.ok),
                    ", ".join(map(str,self.ok.items())))
            else:
                print "OK: %d" % len(self.ok)
            sys.exit(0)
