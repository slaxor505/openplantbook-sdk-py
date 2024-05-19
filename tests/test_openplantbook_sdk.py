import asyncio
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from json_timeseries import TimeSeries, TsRecord, JtsDocument

import openplantbook_sdk
from openplantbook_sdk import ValidationError


class TestSdk(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        path = Path(__file__).parent / "../config.yaml"
        with (open(path) as f):
            config = yaml.load(f, Loader=yaml.FullLoader)
            self.client_id = config['client_id']
            self.client_secret = config['secret']
            if config.get('base_url'):
                self.base_url = config['base_url']
            else:
                self.base_url = "https://open.plantbook.io/api/v1"
        self.test_pid = "abelia chinensis"
        self.test_sensor_id = "Abelia 1 upstairs"

    # def tearDown(self):
    #     pass

    def test_search(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)
        response = asyncio.run(api.async_plant_search(self.test_pid))

        self.assertEqual(response['count'], 1)
        results_data = response.get('results')[0]
        self.assertEqual(results_data['pid'], "abelia chinensis")
        self.assertEqual(results_data['display_pid'], 'Abelia chinensis')
        self.assertEqual(results_data['alias'], 'chinese abelia')
        self.assertEqual(results_data['category'], 'Caprifoliaceae, Abelia')

    def test_plant_detail(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)

        response = asyncio.run(api.async_plant_detail_get(self.test_pid))

        test_json = '''{"pid": "abelia chinensis", "display_pid": "Abelia chinensis", "alias": "chinese abelia", "category": "Caprifoliaceae, Abelia", "max_light_mmol": 4500, "min_light_mmol": 2500, "max_light_lux": 30000, "min_light_lux": 3500, "max_temp": 35, "min_temp": 8, "max_env_humid": 85, "min_env_humid": 30, "max_soil_moist": 60, "min_soil_moist": 15, "max_soil_ec": 2000, "min_soil_ec": 350, "image_url": "https://opb-img.plantbook.io/abelia%20chinensis.jpg"}'''
        self.assertEqual(json.dumps(response), test_json)

    def test_plant_instance_register(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)
        # ONLY 1 plant registration is currently supported by SDK
        found_plants = asyncio.run(api.async_plant_search("acer"))['results'][:1]
        pid_instance_map = {}
        location_country = "AU"
        for i in range(len(found_plants)):
            the_pid = found_plants[i]['pid']
            pid_instance_map["Sensor-" + str(i)] = the_pid
        res = asyncio.run(
            api.async_plant_instance_register(sensor_pid_map=pid_instance_map))

        for k, v in pid_instance_map.items():
            self.assertIn(k, json.dumps(res))
            self.assertIn(v, json.dumps(res))
            self.assertIn(location_country, json.dumps(res))

    def test_plant_instance_register_invalid_pid(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)

        # Only 1 item creation is currently supported
        found_plants = [({"pid": "non_existent_pid_1"})]

        pid_instance_map = {}
        for i in range(len(found_plants)):
            the_pid = found_plants[i]['pid']
            pid_instance_map["Sensor-" + str(i)] = the_pid

        with self.assertRaises(ValidationError) as cm:
            asyncio.run(api.async_plant_instance_register(sensor_pid_map=pid_instance_map))
        errors = cm.exception.errors

        self.assertEqual(len(errors), 1)
        self.assertIn("non_existent_pid_1", errors[0]['detail'])
        self.assertEqual("invalid_pid", errors[0]['code'])

    def test_plant_instance_register_invalid_country(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)

        # Only 1 item creation is currently supported
        found_plants = asyncio.run(api.async_plant_search("acer"))['results'][:1]

        pid_instance_map = {}
        location_country = "ZZ"
        for i in range(len(found_plants)):
            the_pid = found_plants[i]['pid']
            pid_instance_map["Sensor-" + str(i)] = the_pid

        with self.assertRaises(ValidationError) as cm:
            asyncio.run(api.async_plant_instance_register(sensor_pid_map=pid_instance_map, location_country=location_country))
        errors = cm.exception.errors

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['code'], "invalid_location_country")

    def test_plant_data_upload(self):
        api = openplantbook_sdk.OpenPlantBookApi(self.client_id, self.client_secret, base_url=self.base_url)

        found_plants = asyncio.run(api.async_plant_search("acer"))['results'][:5]
        pid_instance_map = {}
        jts_doc = JtsDocument()
        for i in range(len(found_plants)):

            # Plant instance/Sensor ID
            sensor_id = "Sensor-" + str(i)
            # Corresponding PID/Plant ID
            the_pid = found_plants[i]['pid']

            # pid_instance_map["Sensor-"+str(i)]=the_pid

            # Register Plant Instance
            res = asyncio.run(
                api.async_plant_instance_register(sensor_pid_map={sensor_id: the_pid}, location_country="AU",
                location_lat=-33.8678500, location_lon=151.2073200))

            custom_id = res[0].get('id')
            # the same "plant_id" but different sensors identified by "name"
            temp = TimeSeries(identifier=custom_id, name="temp")
            soil_moist = TimeSeries(identifier=custom_id, name="soil_moist")
            soil_ec = TimeSeries(identifier=custom_id, name="soil_ec")
            light_lux = TimeSeries(identifier=custom_id, name="light_lux")

            # generate fake values - 4 columns to provide 4 values for the above 4 measurements
            NUMBER_OF_PERIODS = 10
            dti = pd.date_range(pd.Timestamp.now(tz="Australia/Sydney"), periods=NUMBER_OF_PERIODS, freq="15min")
            df = pd.DataFrame(np.random.default_rng().uniform(100, 1000, (NUMBER_OF_PERIODS, 4)), index=dti).astype(int)

            for ts, values in df.iterrows():
                temp.insert(TsRecord(ts, values[0]))
                soil_moist.insert(TsRecord(ts, values[1]))
                soil_ec.insert(TsRecord(ts, values[2]))
                light_lux.insert(TsRecord(ts, values[3]))

            jts_doc.addSeries([temp, soil_moist, soil_ec, light_lux])

        res = asyncio.run(api.async_plant_data_upload(jts_doc, dry_run=False))

        # test_json = '''{"pid": "abelia chinensis", "display_pid": "Abelia chinensis", "alias": "chinese abelia", "category": "Caprifoliaceae, Abelia", "max_light_mmol": 4500, "min_light_mmol": 2500, "max_light_lux": 30000, "min_light_lux": 3500, "max_temp": 35, "min_temp": 8, "max_env_humid": 85, "min_env_humid": 30, "max_soil_moist": 60, "min_soil_moist": 15, "max_soil_ec": 2000, "min_soil_ec": 350, "image_url": "https://opb-img.plantbook.io/abelia%20chinensis.jpg"}'''
        self.assertEqual(res, True)


if __name__ == '__main__':
    unittest.main()
