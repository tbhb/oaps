# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportImplicitStringConcatenation=false
"""Flow commands for running templated workflows."""

import sys
from typing import Annotated

from cyclopts import Parameter

from ._app import app

__all__ = ["app"]


@app.command(name="start")
def _start(
    workflow_spec: Annotated[
        str,
        Parameter(
            help="Workflow spec: <namespace>:<workflow> or just <namespace> for default"
        ),
    ],
    /,
    *args: Annotated[str, Parameter(help="Arguments to pass to the workflow")],
) -> None:
    """Start a templated workflow.

    Discovers the workflow in flows/<namespace>/<workflow>/ or
    .oaps/flows/<namespace>/<workflow>/, executes its parse() function
    with the provided arguments, and renders the WORKFLOW.md template.

    If only a namespace is provided (without :workflow), the default workflow
    for that namespace is used.

    Args:
        workflow_spec: Workflow spec in format namespace:workflow, or just namespace.
        args: Additional arguments passed to the workflow's parse() function.
    """
    from oaps.flow import (
        discover_flows,
        find_default_flow,
        find_flow,
        format_flow_not_found_error,
        render_flow,
    )

    # Parse the workflow spec
    if ":" not in workflow_spec:
        # Namespace only - try to find default workflow
        namespace = workflow_spec
        default_flow = find_default_flow(namespace)
        if default_flow is not None:
            namespace = default_flow.namespace
            workflow = default_flow.workflow
        else:
            # No default found - show available workflows
            available = discover_flows()
            namespace_flows = {
                spec: flow
                for spec, flow in available.items()
                if flow.namespace == namespace
            }
            if namespace_flows:
                error_msg = format_flow_not_found_error(
                    f"{namespace}:<workflow>", namespace_flows
                )
                print(error_msg)
                print(
                    f"\nError: No default workflow for namespace '{namespace}'. "
                    "Specify a workflow explicitly.",
                    file=sys.stderr,
                )
            else:
                error_msg = format_flow_not_found_error(namespace, available)
                print(error_msg)
                print(
                    f"\nError: Unknown namespace '{namespace}'.",
                    file=sys.stderr,
                )
            sys.exit(1)
    else:
        namespace, workflow = workflow_spec.split(":", 1)

    # Find the flow
    flow_dir = find_flow(namespace, workflow)
    if flow_dir is None:
        available = discover_flows()
        error_msg = format_flow_not_found_error(workflow_spec, available)
        print(error_msg)
        sys.exit(1)

    # Render the flow
    try:
        output = render_flow(flow_dir, list(args))
        print(output)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except AttributeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except TypeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
