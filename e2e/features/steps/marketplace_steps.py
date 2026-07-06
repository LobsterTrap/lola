"""Step definitions for marketplace HTTP server and catalog preconditions."""

import yaml

from behave import given

from support.http_server import LocalHTTPServer


@given('a marketplace catalog served at "{url_path}" with modules')
def step_marketplace_catalog_served(context, url_path):
    """Start a local HTTP server serving a YAML marketplace catalog.

    Reads module rows from the step's data table (columns: module, version,
    repository). Sets context.server_url for {server_url} placeholder resolution.
    """
    serve_dir = context.tmp_dir / "http_serve"
    serve_dir.mkdir(exist_ok=True)

    modules = []
    for row in context.table:
        module_entry = {
            "name": row["module"],
            "description": f"{row['module']} description",
            "version": row["version"],
            "repository": row.get(
                "repository", f"https://example.com/{row['module']}.git"
            ),
        }
        modules.append(module_entry)

    catalog = {
        "name": "Test Marketplace",
        "description": "E2E test marketplace",
        "version": "1.0.0",
        "modules": modules,
    }

    catalog_path = serve_dir / url_path.lstrip("/")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(yaml.dump(catalog))

    server = LocalHTTPServer(serve_dir)
    server.start()
    context.http_servers.append(server)
    context.server_url = server.url
