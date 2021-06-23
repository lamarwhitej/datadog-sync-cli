from requests.exceptions import HTTPError

from datadog_sync.utils.base_resource import BaseResource


RESOURCE_TYPE = "downtimes"
EXCLUDED_ATTRIBUTES = [
    "root['id']",
    "root['updater_id']",
    "root['created']",
    "root['org_id']",
    "root['modified']",
    "root['creator_id']",
    "root['active']",
]
RESOURCES_TO_CONNECT = {"monitors": ["monitor_id"]}
NON_NULLABLE_ATTRIBUTE = ["recurrence.until_date", "recurrence.until_occurrences"]
BASE_PATH = "/api/v1/downtime"


class Downtimes(BaseResource):
    resource_type = RESOURCE_TYPE
    resource_connections = RESOURCES_TO_CONNECT


    def __init__(self, config):
        super().__init__(
            config,
            RESOURCE_TYPE,
            BASE_PATH,
            excluded_attributes=EXCLUDED_ATTRIBUTES,
            resource_connections=RESOURCES_TO_CONNECT,
            non_nullable_attr=NON_NULLABLE_ATTRIBUTE,
        )

    def import_resources(self):
        source_client = self.config.source_client

        try:
            resp = source_client.get(self.base_path).json()
        except HTTPError as e:
            self.logger.error("error importing downtimes %s", e)
            return

        self.import_resources_concurrently(resp)

    def process_resource_import(self, downtime):
        self.source_resources[downtime["id"]] = downtime

    def apply_resources(self):

        connection_resource_obj = self.get_connection_resources()
        self.apply_resources_concurrently(self.source_resources, connection_resource_obj)

    def prepare_resource_and_apply(self, _id, downtime, connection_resource_obj=None):
        if self.resource_connections:
            self.connect_resources(downtime, connection_resource_obj)

        if _id in self.destination_resources:
            self.update_resource(_id, downtime)
        else:
            self.create_resource(_id, downtime)

    def create_resource(self, _id, downtime):
        destination_client = self.config.destination_client
        self.remove_non_nullable_attributes(downtime)
        try:
            resp = destination_client.post(self.base_path, downtime).json()
        except HTTPError as e:
            self.logger.error("error creating downtime: %s", e.response.text)
            return
        self.destination_resources[_id] = resp

    def update_resource(self, _id, downtime):
        destination_client = self.config.destination_client

        diff = self.check_diff(downtime, self.destination_resources[_id])
        self.remove_non_nullable_attributes(downtime)
        if diff:
            try:
                resp = destination_client.put(
                    self.base_path + f"/{self.destination_resources[_id]['id']}", downtime
                ).json()
            except HTTPError as e:
                self.logger.error("error creating downtime: %s", e.response.text)
                return
            self.destination_resources[_id] = resp
