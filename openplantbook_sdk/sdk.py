#!/usr/bin/env python3

import logging
from datetime import datetime, timedelta

import aiohttp
from json_timeseries import JtsDocument

_LOGGER = logging.getLogger(__name__)


class OpenPlantBookApi:
    """
    Open Plantbook SDK class
    """

    def __init__(self, client_id, secret, base_url="https://open.plantbook.io/api/v1"):
        """Initialize
        :param secret: OAuth client secret from Open PlantBook UI
        :type secret: str
        :param client_id: OAuth client ID from Open PlantBook UI
        :type client_id: str
        :param base_url: Plantbook base URL (only for testing)
        :type base_url: str
        """
        self.token = None
        self.client_id = client_id
        self.secret = secret
        self._PLANTBOOK_BASEURL = base_url

    async def _async_get_token(self):
        """
        Get OAuth token
        """
        if not self.client_id or not self.secret:
            raise MissingClientIdOrSecret
        if self.token:
            expires = datetime.fromisoformat(self.token.get('expires'))
            if expires > datetime.now() + timedelta(minutes=5):
                _LOGGER.debug("Token is still valid")
                return True

        url = f"{self._PLANTBOOK_BASEURL}/token/"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.secret,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as result:
                    token = await result.json()
                    if token.get("access_token"):
                        _LOGGER.debug("Got token from %s", url)
                        token["expires"] = (datetime.now() + timedelta(seconds=token["expires_in"])).isoformat()
                        self.token = token
                        return True
                    raise PermissionError
        except PermissionError:
            _LOGGER.error("Wrong client id or secret")
            raise
        except aiohttp.ServerTimeoutError:
            # Maybe set up for a retry, or continue in a retry loop
            _LOGGER.error("Timeout connecting to {}".format(url))
            raise
        except aiohttp.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            _LOGGER.error("Too many redirects connecting to {}".format(url))
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            raise

        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error("Unable to connect to OpenPlantbook: %s", str(e))
            raise

    async def async_plant_detail_get(self, pid: str):
        """
        Retrieve plant details using Plant ID (or PID)

        :type pid: Plant ID string (PID)
        :return: API response as dict of JSON structure
        :rtype: dict
        """

        try:
            await self._async_get_token()
        except Exception:
            _LOGGER.error("No plantbook token")
            raise

        url = f"{self._PLANTBOOK_BASEURL}/plant/detail/{pid}"
        headers = {
            "Authorization": f"Bearer {self.token.get('access_token')}"
        }
        try:
            async with aiohttp.ClientSession(raise_for_status=True, headers=headers) as session:
                async with session.get(url) as result:
                    _LOGGER.debug("Fetched data from %s", url)
                    res = await result.json()
                    return res
        except aiohttp.ServerTimeoutError:
            # Maybe set up for a retry, or continue in a retry loop
            _LOGGER.error("Timeout connecting to {}".format(url))
            return None
        except aiohttp.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            _LOGGER.error("Too many redirects connecting to {}".format(url))
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            return None
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Unable to get plant from plantbook API: %s", str(exception))
            return None

        # return None

    async def async_plant_search(self, search_text: str):
        """
        Search plant by search string

        :type search_text: Search text
        :return: API response as dict of JSON structure
        :rtype: dict
        """
        try:
            await self._async_get_token()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("No plantbook token")
            raise

        url = f"{self._PLANTBOOK_BASEURL}/plant/search?limit=1000&alias={search_text}"
        headers = {
            "Authorization": f"Bearer {self.token.get('access_token')}"
        }
        try:
            async with aiohttp.ClientSession(raise_for_status=True, headers=headers) as session:
                async with session.get(url) as result:
                    _LOGGER.debug("Fetched data from %s", url)
                    res = await result.json()
                    return res
        except aiohttp.ServerTimeoutError:
            # Maybe set up for a retry, or continue in a retry loop
            _LOGGER.error("Timeout connecting to {}".format(url))
            return None
        except aiohttp.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            _LOGGER.error("Too many redirects connecting to {}".format(url))
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            return None
        # TODO: Handle Minimum len of search string
        # return None

    # async def async_post(self,session, url, api_payload):
    #
    #     async with session.post(url, json=api_payload, raise_for_status=False) as result:
    #         _LOGGER.debug("Registered sensor %s", api_payload)
    #         res = await result.json(content_type=None)

    async def async_plant_instance_register(self, sensor_pid_map: dict, location_by_ip: bool = None,
                                            location_country: str = None):
        """
        Register a plant sensor

        :param sensor_pid_map: Plant Instance to PlantID map. Dictionary id-pid
        :param location_by_ip: Allow to take location from IP address
        :param location_country: Country location of the plant
        :return: JSON dict with API response
        :rtype: dict
        :raise [ValidationError]: [Value of 'series' must be types of TimeSeries or List[TimeSeries]]
        """
        try:
            await self._async_get_token()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("No plantbook token")
            raise

        url = f"{self._PLANTBOOK_BASEURL}/sensor-data/instance"
        headers = {
            "Authorization": f"Bearer {self.token.get('access_token')}"
        }
        api_payload = {
            "location_country": location_country,
            "location_by_IP": location_by_ip
            # "location_lon": "43.11",
            # "location_lat": "-15.88",
            # "location_name": "Sydney",
            # "location_region": "New South Wales"
        }
        try:
            async with aiohttp.ClientSession(raise_for_status=True, headers=headers) as session:

                results = []
                for custom_id_value, pid_value in sensor_pid_map.items():

                    api_payload['custom_id'] = custom_id_value
                    api_payload['pid'] = pid_value

                    async with session.post(url, json=api_payload, raise_for_status=False) as result:
                        _LOGGER.debug("Registered sensor %s", api_payload)
                        # TODO O: Handle 500 here
                        res = await result.json()

                        if str(result.status)[0] != "2":
                            _LOGGER.error(str(result.status) + ' ' + result.reason + ": " + str(res))
                            raise aiohttp.ClientError

                        results.append(res)


                return results
                # TODO 2: Optimize as in https://www.twilio.com/blog/asynchronous-http-requests-in-python-with-aiohttp
                #   tasks.append(asyncio.ensure_future(get_pokemon(session, url)))
                # original_pokemon = await asyncio.gather(*tasks)

        except ValidationError as err:
            _LOGGER.error("Validation error {}".format(err))
            raise

        except aiohttp.ServerTimeoutError:
            # Maybe set up for a retry, or continue in a retry loop
            _LOGGER.error("Timeout connecting to {}".format(url))
            return None
        except aiohttp.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            _LOGGER.error("Too many redirects connecting to {}".format(url))
            return None

        # except aiohttp.ClientError as err:
        #     _LOGGER.error(err)
        #     return None

        # return None

    async def async_plant_data_upload(self, jts_doc: JtsDocument, dry_run=False):
        """
        Upload plant's sensor data

        :param dry_run: It instructs API to only validate JTS payload and does not commit values to the database.
        :type dry_run: bool
        :param jts_doc: One or multiple sensors data as JtsDocument object
        :type jts_doc: JtsDocument
        :return: True if successful
        :rtype: bool
        """

        try:
            await self._async_get_token()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("No plantbook token")
            raise

        headers = {
            "Authorization": f"Bearer {self.token.get('access_token')}"
        }

        url = f"{self._PLANTBOOK_BASEURL}/sensor-data/instance"

        try:
            async with aiohttp.ClientSession(raise_for_status=True, headers=headers) as session:

                url = f"{self._PLANTBOOK_BASEURL}/sensor-data/upload"
                async with session.post(url, json=jts_doc.toJSON(), params={"dry_run": str(dry_run)}) as result:
                    _LOGGER.debug("Uploading sensor data %s", jts_doc)
                    res = await result.json(content_type=None)
                    return result.ok

        except aiohttp.ServerTimeoutError:
            # Maybe set up for a retry, or continue in a retry loop
            _LOGGER.error("Timeout connecting to {}".format(url))
            return None
        except aiohttp.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            _LOGGER.error("Too many redirects connecting to {}".format(url))
            return None
        except aiohttp.ClientError as err:
            _LOGGER.error(err)
            return None

        # return None

    # async def sensor_data_register_upload(self, data: JtsDocument, custom_id=None, location_by_ip=None,
    #                              location_country=None, location_lon=None, location_lat=None, location_name=None,
    #                              location_region=None, dry_run=True):
    #     """
    #     Upload plant's sensor data
    #
    #     :param dry_run: It instructs API to only validate JTS payload and does not commit values to the database.
    #     :type dry_run: bool
    #     :param custom_id: This is a plant identified set by a user. It helps to differentiate plant instances when for example a user has 2 instances of the same plant (the same "pid")
    #     :type custom_id: str
    #     :param pid: Plant ID is unique plant identifier
    #     :type pid: str
    #     :param data: One or multiple sensors data as JtsDocument object
    #     :type data: JtsDocument
    #     :param location_by_ip: Default is "true" if not specified. "false" - disables the location by IP detection.
    #     :param location_country: Location country.
    #     :param location_lon: location longitude coordinate where plant is located.
    #     :param location_lat: location latitude coordinate where plant is located.
    #     :param location_name: Location name in well known to the location format. API will make it is best to parse and derive the specific location.
    #     :param location_region: Location region within country.
    #     :return:
    #     """
    #
    #     try:
    #         await self._get_plantbook_token()
    #     except Exception:  # pylint: disable=broad-except
    #         _LOGGER.error("No plantbook token")
    #         raise
    #
    #     headers = {
    #         "Authorization": f"Bearer {self.token.get('access_token')}"
    #     }
    #
    #     url = f"{PLANTBOOK_BASEURL}/sensor-data/instance"
    #     api_payload = {
    #         "custom_id": custom_id,
    #         "pid": pid,
    #         "location_country": location_country,
    #         "location_by_IP": location_by_ip
    #         # "location_lon": location_lon,
    #         # "location_lat": location_lat,
    #         # "location_name": location_name,
    #         # "location_region": location_region
    #     }
    #     try:
    #         async with aiohttp.ClientSession(raise_for_status=True, headers=headers) as session:
    #             async with session.post(url, json=api_payload) as result:
    #                 _LOGGER.debug("Registered sensor %s", api_payload)
    #                 response = await result.json(content_type=None)
    #
    #             # *** Upload data
    #             instance_id = response.get('id')
    #             # Create timeseries for every measurement
    #             temp = TimeSeries(identifier=instance_id, name="temp")
    #             # soil_moist = TimeSeries(identifier=instance_id, name="soil_moist")
    #             # soil_ec = TimeSeries(identifier=instance_id, name="soil_ec")
    #             # light_lux = TimeSeries(identifier=instance_id, name="light_lux")
    #
    #             # parse generated fake data creating Record in corresponding TimeSeries
    #             # "ts" here is TimeStamp
    #             for ts, values in data.iterrows():
    #                 temp.insert(TsRecord(ts, values[0]))
    #                 # soil_moist.insert(TsRecord(ts, values[1]))
    #                 # soil_ec.insert(TsRecord(ts, values[2]))
    #                 # light_lux.insert(TsRecord(ts, values[3]))
    #
    #             jts_doc = JtsDocument([temp])
    #
    #             # Setting dry_run=True as it is not real data. Removing the parameter will upload real-data into OPB database
    #             # response = client.post("/sensor-data/upload" + "?dry_run=True", json=json.loads(jts_doc.toJSON()))
    #
    #             url = f"{PLANTBOOK_BASEURL}/sensor-data/upload"
    #             async with session.post(url, json=jts_doc.toJSON()) as result:
    #                 _LOGGER.debug("Uploading sensor data %s", jts_doc)
    #                 res = await result.json(content_type=None)
    #                 return res
    #
    #     except aiohttp.ServerTimeoutError:
    #         # Maybe set up for a retry, or continue in a retry loop
    #         _LOGGER.error("Timeout connecting to {}".format(url))
    #         return None
    #     except aiohttp.TooManyRedirects:
    #         # Tell the user their URL was bad and try a different one
    #         _LOGGER.error("Too many redirects connecting to {}".format(url))
    #         return None
    #     except aiohttp.ClientError as err:
    #         _LOGGER.error(err)
    #         return None
    #
    #     return None


class MissingClientIdOrSecret(Exception):
    """Exception for missing client_id or token."""
    pass


class ValidationError(Exception):
    """Exception for validation error"""
    pass
