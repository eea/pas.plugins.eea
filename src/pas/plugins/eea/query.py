import logging
from concurrent.futures import as_completed
from dataclasses import dataclass
from time import time
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Literal
from typing import Optional
from typing import TypedDict
from typing import Union

import requests
from requests_futures.sessions import FuturesSession

from plone.memoize import ram

logging.basicConfig(level=logging.DEBUG)
reqlogger = logging.getLogger("urllib3")
reqlogger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

ENDPOINT_ENTRA = "https://login.microsoftonline.com"
ENDPOINT_GRAPH_API = "https://graph.microsoft.com/v1.0"

ApiUser = TypedDict(
    "ApiUser",
    {
        "@odata.type": Literal["#microsoft.graph.user"],
        "id": str,
        "businessPhones": List[str],
        "displayName": str,
        "givenName": Optional[str],
        "jobTitle": Optional[str],
        "mail": Optional[str],
        "mobilePhone": Optional[str],
        "officeLocation": Optional[str],
        "preferredLanguage": Optional[str],
        "surname": Optional[str],
        "userPrincipalName": str,
        "userType": str,
    },
)

ApiGroup = TypedDict(
    "ApiGroup",
    {
        "@odata.type": Literal["#microsoft.graph.group"],
        "id": str,
        "description": str,
        "displayName": str,
        "mail": Optional[str],
        "mailEnabled": bool,
        "visibility": Optional[str],
    },
)

ApiMember = TypedDict(
    "ApiMember",
    {
        "@odata.type": Union[
            Literal["#microsoft.graph.group"], Literal["#microsoft.graph.user"]
        ],
        "id": str,
    },
)


def _cachekey_query_api_endpoint(
    method, self, url, consistent=None, extra_headers=None
):
    headers = tuple(extra_headers.items()) if extra_headers else None
    return time() // (60 * 60), url, consistent, headers


@dataclass
class QueryConfig:
    client_id: str
    client_secret: str
    domain: str


class QueryEntra:

    session: requests.Session
    session_futures: FuturesSession

    config: QueryConfig

    _token_cache: Dict[str, Union[str, int]] = {"expires": 0}

    def __init__(self, config, session=None):
        self.session = session or requests.Session()
        self.session_futures = FuturesSession(max_workers=10)
        self.config = config

    def get_access_token(self):
        if QueryEntra._token_cache["expires"] > time():
            return QueryEntra._token_cache["access_token"]

        url = f"{ENDPOINT_ENTRA}/{self.config.domain}/oauth2/v2.0/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        response = requests.post(url, headers=headers, data=data)
        token_data = response.json()

        QueryEntra._token_cache = {
            "expires": time() + token_data["expires_in"] - 60
        }
        QueryEntra._token_cache.update(token_data)
        return QueryEntra._token_cache["access_token"]

    def _build_headers(self, consistent=True, extra_headers=None):
        token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if not consistent:
            headers["ConsistencyLevel"] = "eventual"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def get_url_future(
        self,
        url,
        consistent=True,
        extra_headers=None,
    ):
        headers = self._build_headers(consistent, extra_headers)
        return self.session_futures.get(url, headers=headers)

    @ram.cache(_cachekey_query_api_endpoint)
    def get_url(
        self,
        url,
        consistent=True,
        extra_headers=None,
    ):
        headers = self._build_headers(consistent, extra_headers)
        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()

    def get_all(self, url, consistent=True, extra_headers=None):
        data = self.get_url(
            url, consistent=consistent, extra_headers=extra_headers
        )
        if data:
            yield from data.get("value", [data])
            next_url = data.get("@odata.nextLink")
            if next_url:
                yield from self.get_all(
                    next_url,
                    consistent=consistent,
                    extra_headers=extra_headers,
                )

    def get_user(self, user_id) -> ApiUser:
        url = f"{ENDPOINT_GRAPH_API}/users/{user_id}"
        data = self.get_url(url)
        return data.get("value") if data else None

    def get_all_users(self, properties=None) -> Iterator[ApiUser]:
        url = "{ENDPOINT_GRAPH_API}/users?$top=999"
        if properties:
            url = f"{url}&$select={','.join(properties)}"
        return self.get_all(url)

    def search_users(self, query, properties=None) -> Iterator[ApiUser]:
        url = "{ENDPOINT_GRAPH_API}/users"

        custom_query = ""

        if not properties and query:
            custom_query = f"displayName:{query}"

        if properties and properties.get("fullname"):
            custom_query = f"displayName:{properties.get('fullname')}"

        elif properties and properties.get("email"):
            custom_query = f"mail:{properties.get('email')}"

        if custom_query:
            url = f'{url}?$search="{custom_query}"'

        return self.get_all(url, consistent=False)

    def get_user_groups(self, user_id) -> Iterator[ApiGroup]:
        base_url = f"{ENDPOINT_GRAPH_API}/users/{user_id}"
        url = f"{base_url}/memberOf/microsoft.graph.group?$top=999&$select=id"
        return self.get_all(url)

    def get_group(self, group_id) -> ApiGroup:
        url = f"{ENDPOINT_GRAPH_API}/groups/{group_id}"
        data = self.get_url(url)
        return data.get("value") if data else None

    def get_all_groups(self) -> Iterator[ApiGroup]:
        url = "{ENDPOINT_GRAPH_API}/groups?$top=999"
        return self.get_all(url)

    def get_group_members(self, group_id) -> Iterator[ApiMember]:
        base_url = f"{ENDPOINT_GRAPH_API}/groups/{group_id}"
        url = f"{base_url}/members?$top=999&$select=id"
        return self.get_all(url)

    def get_group_members_parallel(
        self, group_ids: Iterable[str]
    ) -> Iterator[Union[str, ApiMember]]:
        futures = []
        for group_id in group_ids:
            base_url = f"{ENDPOINT_GRAPH_API}/groups/{group_id}"
            url = f"{base_url}/members?$top=999&$select=id"
            f = self.get_url_future(url)
            f.group_id = group_id
            futures.append(f)

        for future in as_completed(futures):
            resp = future.result()
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    yield future.group_id  # noqa
                    yield from data.get("value", [data])
                    next_url = data.get("@odata.nextLink")
                    if next_url:
                        yield from self.get_all(next_url)
