#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import asyncio
import sys

import numpy as np
import pandas as pd
import yaml
from tabulate import tabulate

from openplantbook_sdk import OpenPlantBookApi, MissingClientIdOrSecret, ValidationError

PID = "abelia chinensis"
SENSOR_ID="Abelia 1 upstairs"

try:
    with open(r'config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
except FileNotFoundError:
    print("Config-file not found.")
    print("Copy config.yaml.dist to config.yaml and add client_id and secret from https://open.plantbook.io/apikey/show/")
    sys.exit()
except Exception as e:
    print(e)
    sys.exit()

api = OpenPlantBookApi(config['client_id'], config['secret'])
# api = OpenPlantBookApi(None, None)

print(f"Searching the OpenPlantbook for {PID}...")

try:
    res = asyncio.run(api.async_plant_search(PID))
except MissingClientIdOrSecret:
    print("Missing or invalid client id or secret")
    sys.exit()
except Exception as e:
    print(e)
    sys.exit()

print("Found:")
print(tabulate(res['results'], headers={'pid': 'PID', 'display_pid': 'Display PID', 'alias': 'Alias'}, tablefmt="psql"))
print("{} plants found".format(len(res['results'])))


print("Getting details for a single plant...")

try:
    plant = res['results'][0]
    res = asyncio.run(api.async_plant_detail_get(plant['pid']))
    print("Found:")
    print(tabulate(res.items(), headers=['Key', 'Value'], tablefmt="psql"))

except Exception as e:
    print(e)
    sys.exit()

"""
Sample sensor-data
"""

# generate fake data for this example
NUMBER_OF_PERIODS = 2
location_country = "Australia"

dti = pd.date_range(pd.Timestamp.now(tz="Australia/Sydney"), periods=NUMBER_OF_PERIODS, freq="15min")

# generate fake values - 4 columns to provide 4 values for the following measurements: temp, soil_moist, soil_ec, light_lux
df = pd.DataFrame(np.random.default_rng().uniform(100, 1000, (NUMBER_OF_PERIODS, 4)), index=dti).astype(int)

custom_id = "Sample instance of " + PID


"""
Create Plant instance
"""

print(f"Registering sensor for {PID}...")

try:
    res = asyncio.run(api.async_plant_instance_register(sensor_pid_map={SENSOR_ID: PID}, location_country="Australia"))
except ValidationError as err:
    print(err)
    sys.exit()

except Exception as e:
    print(e)
    sys.exit()

print("Registered:")
print(res)


# """
# Upload sensor-data
# """
#
# print(f"Uploading sensor data for {PID}...")
#
# res = asyncio.run(api.plant_instance_register(sensor_pid_map={custom_id: PID}, location_country="Australia"))
# custom_id = res[0].get('id')
# res = asyncio.run(api.plant_data_upload(
#     custom_id=custom_id, pid=PID, data=df, location_country="Australia"))

# print(res)


