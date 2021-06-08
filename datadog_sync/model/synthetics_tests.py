from concurrent.futures import ThreadPoolExecutor, wait

from requests.exceptions import HTTPError

from datadog_sync.utils.base_resource import BaseResource


RESOURCE_TYPE = "synthetics_tests"
EXCLUDED_ATTRIBUTES = [
    "root['deleted_at']",
    "root['org_id']",
    "root['public_id']",
    "root['monitor_id']",
    "root['modified_at']",
    "root['created_at']",
]
EXCLUDED_ATTRIBUTES_RE = ["updatedAt", "notify_audit", "locked", "include_tags", "new_host_delay", "notify_no_data"]
BASE_PATH = "/api/v1/synthetics/tests"
RESOURCE_CONNECTIONS = {"synthetics_private_locations": ["locations"]}


class SyntheticsTests(BaseResource):
    def __init__(self, config):
        super().__init__(
            config,
            RESOURCE_TYPE,
            BASE_PATH,
            resource_connections=RESOURCE_CONNECTIONS,
            excluded_attributes=EXCLUDED_ATTRIBUTES,
            excluded_attributes_re=EXCLUDED_ATTRIBUTES_RE,
        )

    def import_resources(self):
        synthetics_tests = {}
        source_client = self.config.source_client

        try:
            resp = source_client.get(self.base_path).json()
        except HTTPError as e:
            self.logger.error("error importing synthetics_tests: %s", e)
            return

        self.import_resources_concurrently(synthetics_tests, resp["tests"])

        # Write resources to file
        self.write_resources_file("source")

    def process_resource_import(self, synthetics_test, synthetics_tests):
        synthetics_tests[f"{synthetics_test['public_id']}#{synthetics_test['monitor_id']}"] = synthetics_test

    def apply_resources(self):
        self.open_resources()
        connection_resource_obj = self.get_connection_resources()
        self.apply_resources_concurrently(self.source_resources, connection_resource_obj)
        self.write_resources_file("destination")

    def prepare_resource_and_apply(self, _id, synthetics_test, connection_resource_obj=None):

        if self.resource_connections:
            self.connect_resources(synthetics_test, connection_resource_obj)

        if _id in self.destination_resources:
            self.update_resource(_id, synthetics_test)
        else:
            self.create_resource(_id, synthetics_test)

    def create_resource(self, _id, synthetics_test):
        destination_client = self.ctx.obj.get("destination_client")
        self.remove_excluded_attr(synthetics_test)

        try:
            resp = destination_client.post(self.base_path, synthetics_test).json()
        except HTTPError as e:
            self.logger.error("error creating synthetics_test: %s", e.response.text)
            return
        self.destination_resources[_id] = resp

    def update_resource(self, _id, synthetics_test):
        destination_client = self.ctx.obj.get("destination_client")

        diff = self.check_diff(synthetics_test, self.destination_resources[_id])
        if diff:
            self.remove_excluded_attr(synthetics_test)
            try:
                resp = destination_client.put(
                    self.base_path + f"/{self.destination_resources[_id]['public_id']}", synthetics_test
                ).json()
            except HTTPError as e:
                self.logger.error("error creating synthetics_test: %s", e.response.text)
                return
            self.destination_resources[_id] = resp
