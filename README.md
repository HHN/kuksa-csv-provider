# KUKSA CSV Provider

![kuksa.val Logo](./doc/img/logo.png)

The aim of this script is to provide and replay VSS data into a [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker).
Therefore, it takes a CSV-file, containting pre-defined sequences of VSS signals including timing delays, and provides it to the KUKSA Databroker.

## Usage

The provider requires an installation of Python in version 3 and can be executed with the following commands:

```console
pip install -r requirements.txt
python3 provider.py
```

This assumes a running KUKSA Databroker at `127.0.0.1:55555` and a file named `signals.csv` containing the signals to apply. See the section [Arguments](#arguments) for more details on possible arguments and default values.

The provider uses the [KUKSA Python SDK](https://github.com/eclipse-kuksa/kuksa-python-sdk), which you need to install on your system, e.g., by applying the [requirement.txt](requirements.txt) with pip.

## Arguments

You can start the provider (`provider.py`) with the following arguments on a command line:

```
usage: provider.py [-h] [-f FILE] [-i | --infinite | --no-infinite] [-l {INFO,ERROR,CRITICAL,DEBUG,WARNING}] [--cacertificate [CACERTIFICATE]]
                   [--tls-server-name [TLS_SERVER_NAME]]
                   [server]

This provider writes the content of a csv file to a kuksa.val databroker

positional arguments:
  server                URI of the kuksa.val databroker to connect to, e.g. grpc://127.0.0.1:55555 or grpcs://localhost:55555 for a TLS connection.
                        The default value is grpc://127.0.0.1:55555

options:
  -h, --help            show this help message and exit
  -f, --file FILE       This indicates the csv file containing the signals to update in the kuksa.val databroker. The default value is signals.csv.
  -i, --infinite, --no-infinite
                        If the flag is set, the provider loopsthe file until stopped, otherwise the file gets processed once.
  -l, --log {CRITICAL,ERROR,INFO,DEBUG,WARNING}
                        This sets the logging level. The default value is WARNING.
  --cacertificate [CACERTIFICATE]
                        Specify the path to your CA.pem. Needed when connecting using a grpcs:// URI
  --tls-server-name [TLS_SERVER_NAME]
                        TLS server name, may be needed if addressing a server by IP-name
```

## CSV File

An example CSV-files is available in [signals.csv](signals.csv) where an example line is:

```csv
current,Vehicle.Speed,48,1
```

The delimiter for the CSV-file is the ',' sign. The first line is interpreted as header and not as data.

Each line in the csv file consists of the following elements:

| header | description | example |
| -- | -----------| --|
| field | indicates whether to update the current value (`current`) or the target value (`target`) for the signal. | current |
| signal | the name of the signal to update | Vehicle.Speed |
| value | the new value | 48 |
| delay | Indicates the time in seconds which the provider shall wait after processing this signal. This way one can emulate the change of signals over time. | 0 |
| datatype (optional) | The VSS data type of the signal. Present only when the recorder is used with `--with-datatype`. | FLOAT |

### Datatype Column

When the recorder is used with the `--with-datatype` flag, a `datatype` column is appended to the CSV. It contains the VSS data type name for each signal, resolved from the KUKSA Databroker's metadata. The following values may appear:

| Datatype | Description |
| -- | -- |
| UNSPECIFIED | Fallback when the type could not be resolved from the Databroker |
| STRING | A string value |
| BOOLEAN | A boolean value (`true` / `false`) |
| INT8 | Signed 8-bit integer |
| INT16 | Signed 16-bit integer |
| INT32 | Signed 32-bit integer |
| INT64 | Signed 64-bit integer |
| UINT8 | Unsigned 8-bit integer |
| UINT16 | Unsigned 16-bit integer |
| UINT32 | Unsigned 32-bit integer |
| UINT64 | Unsigned 64-bit integer |
| FLOAT | 32-bit floating point |
| DOUBLE | 64-bit floating point |
| TIMESTAMP | A timestamp value |
| STRING_ARRAY | Array of string values |
| BOOLEAN_ARRAY | Array of boolean values |
| INT8_ARRAY | Array of signed 8-bit integers |
| INT16_ARRAY | Array of signed 16-bit integers |
| INT32_ARRAY | Array of signed 32-bit integers |
| INT64_ARRAY | Array of signed 64-bit integers |
| UINT8_ARRAY | Array of unsigned 8-bit integers |
| UINT16_ARRAY | Array of unsigned 16-bit integers |
| UINT32_ARRAY | Array of unsigned 32-bit integers |
| UINT64_ARRAY | Array of unsigned 64-bit integers |
| FLOAT_ARRAY | Array of 32-bit floating point values |
| DOUBLE_ARRAY | Array of 64-bit floating point values |
| TIMESTAMP_ARRAY | Array of timestamp values |

## TLS

If connecting to a KUKSA Databroker that require a secure connection use a `grpcs://` server URI and specify
which root certificate to use to identify the Server by the `--cacertificate` argument. If your (test) setup
uses the KUKSA example certificates you must give [CA.pem](https://github.com/eclipse-kuksa/kuksa.val/blob/master/kuksa_certificates/CA.pem)
as root CA. The server name must match the name in the certificate provided by KUKSA.val databroker.
Due to a limitation in the gRPC client, if connecting by IP-address you may need to give a name listed in the certificate
by the `--tls-server-name` argument. The example server certificate lists the names `Server` and `localhost`,
so one of those names needs to be specified if connecting to `127.0.0.1`. An example is shown below:

```console
python provider.py grpcs://localhost:55555 --cacertificate <path-to-certificates>/CA.pem --tls-server-name Server
```

## Limitations

* CSV Provider does not support authentication, i.e. it is impossible to communicate with a Databroker that require authentication!

## Recorder

One way to generate a CSV-file for the CSV-provider is to record it from an KUKSA Databroker. This way one can reproduce an interaction of different providers with the KUKSA Databroker. The script in `csv_provider/recorder.py` allows this recording.
An example call, only recording the vehicle speed and width would be:

```console
pip install -r requirements.txt
python3 recorder.py -s Vehicle.Speed Vehicle.Width
```

The recorder supports the following parameters:

```
usage: recorder.py [-h] [-f FILE] -s SIGNALS [SIGNALS ...] [-d] [-l {DEBUG,WARNING,INFO,ERROR,CRITICAL}] [--cacertificate [CACERTIFICATE]]
                   [--tls-server-name [TLS_SERVER_NAME]]
                   [server]

This provider writes the content of a csv file to a KUKSA.val databroker

positional arguments:
  server                URI of the KUKSA.val databroker to connect to, e.g. grpc://127.0.0.1:55555 or grpcs://localhost:55555 for a TLS connection.
                        The default value is grpc://127.0.0.1:55555

options:
  -h, --help            show this help message and exit
  -f, --file FILE       This indicates the csv file to write the signals to. The default value is signals.csv.
  -s, --signals SIGNALS [SIGNALS ...]
                        A list of signals to record
  -d, --with-datatype   If set, the VSS datatype for each signal is also recorded.
  -l, --log {DEBUG,WARNING,INFO,ERROR,CRITICAL}
                        This sets the logging level. The default value is WARNING.
  --cacertificate [CACERTIFICATE]
                        Specify the path to your CA.pem. Needed when connecting using a grpcs:// URI
  --tls-server-name [TLS_SERVER_NAME]
                        TLS server name, may be needed if addressing a server by IP-name
```

## Container

CSV-provider is also available as container

```console
docker run -it --rm --net=host ghcr.io/eclipse-kuksa/kuksa-csv-provider/csv-provider:main
```

If the ghcr registry is not easily accessible to you, e.g. if you are a China mainland user, starting from release 0.4.4 we  also made the container images available at quay.io:

```console
docker run -it --rm --net=host quay.io/eclipse-kuksa/csv-provider:main
```

## Pre-commit set up

This repository is set up to use [pre-commit](https://pre-commit.com/) hooks.
Use `pip install pre-commit` to install pre-commit.
After you clone the project, run `pre-commit install` to install pre-commit into your git hooks.
Pre-commit will now run on every commit.
Every time you clone a project using pre-commit running pre-commit install should always be the first thing you do.
