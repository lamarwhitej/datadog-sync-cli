import os
import time

from click import pass_context, command

from datadog_sync.constants import RESOURCE_FILE_PATH, DESTINATION_RESOURCES_DIR


@command("sync", short_help="Sync Datadog resources to destination.")
@pass_context
def sync(ctx):
    """Sync Datadog resources to destination."""
    cfg = ctx.obj.get("config")
    start = time.time()
    os.makedirs(DESTINATION_RESOURCES_DIR, exist_ok=True)

    for resource_type, resource in cfg.resources.items():
        if os.path.exists(RESOURCE_FILE_PATH.format("source", resource_type)):
            cfg.logger.info("syncing resource: {}".format(resource_type))
            resource.open_resources()
            resource.apply_resources()
            resource.write_resources_file("destination", resource.destination_resources)
            cfg.logger.info("finished syncing resource: {}".format(resource_type))

    cfg.logger.info(f"finished syncing resources: {time.time() - start}s")

    if cfg.logger.exception_logged:
        exit(1)
