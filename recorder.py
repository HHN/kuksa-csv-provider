#! /usr/bin/env python3

########################################################################
# Copyright (c) 2023 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License 2.0 which is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
########################################################################
'''A recording writing signals from an instance of the KUKSA.val databroker
 to a CSV-file'''
import argparse
import asyncio
import csv
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from kuksa_client.grpc.aio import VSSClient
from kuksa_client.grpc import VSSClientError
from kuksa_client.grpc import View
from kuksa_client.grpc import SubscribeEntry
from kuksa_client.grpc import MetadataField

from kuksa_client.grpc import Field


def init_argparse() -> argparse.ArgumentParser:
    '''This inits the argument parser for the CSV-recorder.'''
    parser = argparse.ArgumentParser(
        usage="[URI] -s [SIGNALS] -f [FILE] -l [LOGGING LEVEL]",
        description="This provider writes the content of a csv file to a KUKSA.val databroker")
    parser.add_argument("server", nargs="?",
                        default=os.environ.get("KUKSA_ADDRESS", "grpc://127.0.0.1:55555"),
                        help="URI of the KUKSA.val databroker to connect to, e.g. grpc://127.0.0.1:55555"
                        " or grpcs://localhost:55555 for a TLS connection."
                        " The default value is grpc://127.0.0.1:55555")
    parser.add_argument("-f", "--file", default="signalsOut.csv", help="This indicates the csv file"
                        " to write the signals to."
                        " The default value is signals.csv.")
    parser.add_argument("-s", "--signals", help="A list of signals to"
                        " record", nargs='+', required=True)
    parser.add_argument("-d", "--with-datatype", action="store_true",
                        help="If set, the VSS datatype for each signal is also recorded.")
    parser.add_argument("-l", "--log", default="INFO", help="This sets the logging level."
                        " The default value is WARNING.",
                        choices={"INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"})
    parser.add_argument("--cacertificate",
                        help="Specify the path to your CA.pem. Needed when connecting using a"
                        " grpcs:// URI",
                        nargs='?', default=None)
    parser.add_argument("--tls-server-name",
                        help="TLS server name, may be needed if addressing a server by IP-name",
                        nargs='?', default=None)
    return parser


def get_connection_details(parser: argparse.ArgumentParser, args: argparse.Namespace) -> tuple:
    '''Resolve host, port, root certificate and TLS server name from the server URI.'''
    parts = urlparse(args.server)
    if parts.scheme.lower() not in ("grpc", "grpcs"):
        parser.error("Unsupported URI scheme %s. Use grpc:// or grpcs://"
                     % (parts.scheme or "(none)"))
    if parts.hostname is None:
        parser.error("No hostname or IP given in server URI")
    try:
        port = parts.port or 55555
    except ValueError:
        parser.error("Invalid port in server URI %s" % parts.netloc)
    root_certificates = Path(args.cacertificate) if args.cacertificate else None
    if parts.scheme.lower() == "grpcs" and root_certificates is None:
        parser.error("TLS cannot be used as no CA Certificate specified."
                     " Provide the --cacertificate argument")
    return parts.hostname, port, root_certificates, args.tls_server_name


async def main():
    '''entrypoint to the CSV-recorder'''
    parser = init_argparse()
    args = parser.parse_args()
    for signal in args.signals:
        if "://" in signal:
            parser.error("%s looks like a server URI, not a signal path. Give the server URI"
                         " before the -s argument, e.g. python3 recorder.py %s -s ..."
                         % (signal, signal))
    numeric_value = getattr(logging, args.log.upper(), None)
    if isinstance(numeric_value, int):
        logging.basicConfig(encoding='utf-8', level=numeric_value)
    host, port, root_path, tls_server_name = get_connection_details(parser, args)
    try:
        async with VSSClient(host, port, root_certificates=root_path,
                             tls_server_name=tls_server_name) as client:
            fieldnames = ['field', 'signal', 'value', 'delay']
            if args.with_datatype:
                fieldnames.append('datatype')
            csvfile = open(args.file, 'w', newline='', encoding="utf-8", buffering=1)
            signalwriter = csv.DictWriter(csvfile, fieldnames)
            signalwriter.writeheader()
            signal_datatypes = {}
            previous_time = time.time()
            initial_value = True
            entries = []
            for signal in args.signals:
                entries.append(SubscribeEntry(signal,
                                              View.FIELDS,
                                              (Field.VALUE, Field.ACTUATOR_TARGET)))
            async for updates in client.subscribe(entries=entries):
                if initial_value:
                    time_gap = 0.0
                    initial_value = False
                else:
                    current_time = time.time()
                    time_gap = current_time - previous_time
                    previous_time = current_time
                for update in updates:
                    entry = update.entry
                    if args.with_datatype and entry.path not in signal_datatypes:
                        try:
                            metadata_response = await client.get_metadata(
                                [entry.path], MetadataField.DATA_TYPE)
                            signal_datatypes[entry.path] = (
                                metadata_response[entry.path].data_type.name)
                        except (VSSClientError, KeyError):
                            logging.warning(
                                "Could not resolve datatype for %s, defaulting to UNSPECIFIED",
                                entry.path)
                            signal_datatypes[entry.path] = "UNSPECIFIED"
                    if entry.value is not None:
                        row = {'field': 'current',
                               'signal': entry.path,
                               'value': entry.value.value,
                               'delay': time_gap}
                        if args.with_datatype:
                            row['datatype'] = signal_datatypes.get(entry.path, "UNSPECIFIED")
                        signalwriter.writerow(row)
                    if entry.actuator_target is not None:
                        row = {'field': 'target',
                               'signal': entry.path,
                               'value': entry.actuator_target.value,
                               'delay': time_gap}
                        if args.with_datatype:
                            row['datatype'] = signal_datatypes.get(entry.path, "UNSPECIFIED")
                        signalwriter.writerow(row)
    except VSSClientError as error:
        logging.error("There was a problem in the interaction"
                      " with the KUKSA.val databroker at %s: %s ",
                      args.server, str(error))

asyncio.run(main())
