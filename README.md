# Open Plantbook SDK for Python

[![Documentation Status](https://readthedocs.org/projects/openplantbook-sdk-py/badge/?version=latest)](https://openplantbook-sdk-py.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/openplantbook-sdk.svg)](https://badge.fury.io/py/openplantbook-sdk)

This is an SDK to integrate with [Open Plantbook](https://open.plantbook.io) API. 

More information about Open Plantbook and documentation can be found [here](https://github.com/slaxor505/OpenPlantbook-client).
It requires registration and API credentials which can be generated on Open Plantbook website.

See [API documentation](https://documenter.getpostman.com/view/12627470/TVsxBRjD) for details about returned values by the SDK.
[Discord](https://discord.gg/dguPktq9Zh) for support and questions 

## Installation

```shell
pip install openplantbook-sdk
```

Import or require module

```python
from openplantbook_sdk import OpenPlantBookApi
```

## Usage

Quick example (async):

```python
import asyncio
from openplantbook_sdk import OpenPlantBookApi

async def main():
    api = OpenPlantBookApi("YOUR_CLIENT_ID", "YOUR_CLIENT_SECRET")
    # Retrieve plant details with optional ISO 639-1 language code
    details = await api.async_plant_detail_get("abelia chinensis", lang="de")
    print(details["display_pid"])
    # Search plants
    results = await api.async_plant_search("abelia")
    print(results["count"]) 

asyncio.run(main())
```

- The `lang` parameter is optional; pass an ISO 639-1 code like "en", "de", "es" to localize fields when supported by the API.

See [demo.py](demo.py) for a more complete walkthrough.


## License
MIT
