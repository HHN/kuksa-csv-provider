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
'''A provider accepting VSS-signals from a CSV-file
 to write these signals into an Kuksa.val data broker'''

import asyncio
import csv
import argparse
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from kuksa_client.grpc import Datapoint
from kuksa_client.grpc import DataEntry
from kuksa_client.grpc import EntryUpdate
from kuksa_client.grpc import Field
from kuksa_client.grpc import VSSClientError
from kuksa_client.grpc.aio import VSSClient


def init_argparse() -> argparse.ArgumentParser:
    '''This inits the argument parser for the CSV-provider.'''
    parser = argparse.ArgumentParser(
        usage="[URI] -f [FILE]",
        description="This provider writes the content of a csv file to a kuksa.val databroker",
    )
    environment = os.environ
    parser.add_argument("server", nargs="?",
                        default=environment.get("KUKSA_ADDRESS", "grpc://127.0.0.1:55555"),
                        help="URI of the kuksa.val databroker to connect to, e.g. grpc://127.0.0.1:55555"
                        " or grpcs://localhost:55555 for a TLS connection."
                        " The default value is grpc://127.0.0.1:55555")
    parser.add_argument("-f", "--file", default=environment.get("PROVIDER_SIGNALS_FILE",
                                                                "signals.csv"),
                        help="This indicates the csv file containing the signals to update in"
                        " the kuksa.val databroker. The default value is signals.csv.")
    parser.add_argument("-i", "--infinite", default=environment.get("PROVIDER_INFINITE"),
                        action=argparse.BooleanOptionalAction,
                        help="If the flag is set, the provider loops"
                        "the file until stopped, otherwise the file gets processed once.")
    parser.add_argument("-l", "--log", default=environment.get("PROVIDER_LOG_LEVEL", "INFO"),
                        help="This sets the logging level. The default value is WARNING.",
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
    '''the main function as entry point for the CSV-provider'''
    parser = init_argparse()
    args = parser.parse_args()
    numeric_value = getattr(logging, args.log.upper(), None)
    host, port, root_path, tls_server_name = get_connection_details(parser, args)
    if isinstance(numeric_value, int):
        logging.basicConfig(encoding='utf-8', level=numeric_value)
    try:
        async with VSSClient(host, port, root_certificates=root_path,
                             tls_server_name=tls_server_name) as client:
            csvfile = open(args.file, newline='', encoding="utf-8")
            signal_reader = csv.DictReader(csvfile,
                                           delimiter=',',
                                           quotechar='|',
                                           skipinitialspace=True)
            logging.info("Starting to apply the signals read from %s.", str(csvfile.name))
            if args.infinite:
                backup = list(signal_reader)
                while True:
                    rows = backup
                    backup = list(rows)
                    await process_rows(client, rows)
            else:
                await process_rows(client, signal_reader)
    except VSSClientError:
        logging.error("Could not connect to the kuksa.val databroker at %s."
                      " Make sure to set the correct connection details using the server URI"
                      " and that the kuksa.val databroker is running.", args.server)


async def process_rows(client, rows):
    '''Processes a single row from the CSV-file and write the
     recorded signal to the data broker through the client.'''
    for row in rows:
        if row['field'] == "current":
            entry = DataEntry(
                row['signal'],
                value=Datapoint(value=row['value']),
            )
            updates = (EntryUpdate(entry, (Field.VALUE,)),)
            logging.info("Update current value of %s to %s", row['signal'], row['value'])
        elif row['field'] == "target":
            entry = DataEntry(
                row['signal'],
                actuator_target=Datapoint(value=row['value'])
            )
            updates = (EntryUpdate(entry, (Field.ACTUATOR_TARGET,)),)
            logging.info("Update target value of %s to %s", row['signal'], row['value'])
        else:
            updates = []
        try:
            await client.set(updates=updates)
        except VSSClientError as ex:
            logging.error("Error while updating %s\n%s", row['signal'], ex)
        try:
            await asyncio.sleep(delay=float(row['delay']))
        except ValueError:
            logging.error("Error while waiting for %s seconds after updating %s to %s."
                          " Make sure to only use numbers for the delay value.",
                          row['delay'], row['signal'], row['value'])

asyncio.run(main())
