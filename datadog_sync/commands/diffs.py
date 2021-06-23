from click import pass_context, command


@command("diffs", short_help="Log resource diffs.")
@pass_context
def diffs(ctx):
    """Log Datadog resources diffs."""
    cfg = ctx.obj.get("config")

    for resource_type, resource in cfg.resources.items():
        resource.check_diffs()

    if cfg.logger.exception_logged:
        exit(1)
