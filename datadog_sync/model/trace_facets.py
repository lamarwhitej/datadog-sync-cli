# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING, Optional, List, Dict, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class TraceFacets(BaseResource):
    resource_type = "trace_facets"
    resource_config = ResourceConfig(
        base_path="/api/v1/logs",
        excluded_attributes=["bounded", "bundledAndUsed"],
    )
    # Additional TraceFacets specific attributes
    destination_trace_facets: Dict[str, Dict] = dict()

    # TODO stop hardcoding those; see what the web frontend does
    #source_scopeid = "59189"
    source_scopeid = "215896"
    destination_scopeid = "2257191"

    def get_resources(self, client: CustomClient) -> List[Dict]:
        resp = client.get(self.resource_config.base_path + "/facet_lists?type=trace").json()

        return resp["facets"]["trace"]

    def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> None:
        if _id:
            source_client = self.config.source_client
            resource = source_client.get(self.resource_config.base_path + f"/scopes/{self.source_scopeid}/facets/{_id}").json()

        resource = cast(dict, resource)
        if not resource["editable"]:
            return
        self.resource_config.source_resources[resource["id"]] = resource

    def pre_resource_action_hook(self, _id, resource: Dict) -> None:
        pass

    def pre_apply_hook(self) -> None:
        self.destination_trace_facets = self.get_destination_trace_facets()

    def create_resource(self, _id: str, resource: Dict) -> None:
        if _id in self.destination_trace_facets:
            self.resource_config.destination_resources[_id] = self.destination_trace_facets[_id]
            self.update_resource(_id, resource)
            return

        destination_client = self.config.destination_client
        payload = deepcopy(resource)
        payload["_authentication_token"] = destination_client.csrf_token
        resp = destination_client.post(
            self.resource_config.base_path +
            f"/scopes/{self.destination_scopeid}/facets?type=trace",
            payload,
        ).json()

        self.resource_config.destination_resources[_id] = resp

    def update_resource(self, _id: str, resource: Dict) -> None:
        destination_client = self.config.destination_client
        payload = deepcopy(resource)
        payload["_authentication_token"] = destination_client.csrf_token
        resp = destination_client.post(
            self.resource_config.base_path +
            f"/scopes/{self.destination_scopeid}/facets/" +
            f"{self.resource_config.destination_resources[_id]['id']}?type=trace",
            payload,
        ).json()

        self.resource_config.destination_resources[_id] = resp

    def delete_resource(self, _id: str) -> None:
        destination_client = self.config.destination_client
        payload = {}
        payload["_authentication_token"] = destination_client.csrf_token
        destination_client.delete(
            self.resource_config.base_path +
            f"/scopes/{self.destination_scopeid}/facets/" +
            f"{self.resource_config.destination_resources[_id]['id']}?type=trace",
            payload,
        ).json()

    def connect_id(self, key: str, r_obj: Dict, resource_to_connect: str) -> Optional[List[str]]:
        pass

    def get_destination_trace_facets(self) -> Dict[str, Dict]:
        destination_trace_facets = {}
        destination_client = self.config.destination_client

        resp = self.get_resources(destination_client)
        for trace_facet in resp:
            destination_trace_facets[trace_facet["id"]] = trace_facet

        return destination_trace_facets
