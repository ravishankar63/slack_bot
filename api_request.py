import requests

def api_request(method, url, headers=None, params=None, data=None, json=None):

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json
        )
        response.raise_for_status()  # Raise an exception for non-2xx response codes
        print("API Req")
        print(response.json())
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        raise err
    except requests.exceptions.RequestException as err:
        print(f"Request Exception: {err}")
        raise err
