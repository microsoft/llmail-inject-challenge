import argparse
import asyncio
import json
import sys
from os.path import dirname

sys.path.insert(0, dirname(dirname(__file__)))

from utils.better_logging import logger
from agent.job_sources.azure_queue import AzureQueueJobSource
from agent.job_sources.local import LocalJobSource
from agent.job_sources.stress_test import StressTestJobSource
from agent.runner import JobRunner
from agent.telemetry import tracer, SpanKind
from agent.workload import Workload
import os


def parse_args():
    parser = argparse.ArgumentParser(description="Run the challenge agent in local or azure mode.")
    parser.add_argument(
        "source",
        choices=["local", "azure", "stress"],
        help="Mode to run the agent. 'local' for local job processing, 'azure' for Azure Queue processing.",
    )
    parser.add_argument(
        "--enable-task-tracker",
        action="store_true",
        default=False,
        help="Enable TaskTracker",
    )
    parser.add_argument(
        "--no-op-workload",
        action="store_true",
        default=False,
        help="Use a no-op workload which simply echoes the job message.",
    )
    parser.add_argument(
        "--phase",
        choices=["phase1", "phase2"],
        required=True,
        help="Competition phase to control which defenses to use.",
    )
    return parser.parse_known_args()


async def main(source: str, enable_task_tracker: bool, no_op_workload: bool, unknown_args: list[str]):
    sources = {
        "local": LocalJobSource,
        "azure": AzureQueueJobSource,
        "stress": StressTestJobSource,
    }

    if source not in sources:
        logger.error(f"Unknown source: {source}")
        return

    job_source = sources[source](unknown_args)

    workload: Workload | None = None
    if no_op_workload:
        from agent.workloads.example import ExampleWorkload

        workload = ExampleWorkload(unknown_args)
    else:
        from agent.workloads.scenarios import GeneralWorkload

        workload = GeneralWorkload(task_tracker=enable_task_tracker)

    runner = JobRunner(job_source, workload)

    await runner.run()


if __name__ == "__main__":
    """
    Run the agent in local or azure mode.

    For task-tracker agents, we will generally need to configure the dispatch queue name:

    > export STORAGE_ACCOUNT_NAME="llmail-example"
    > export DISPATCH_QUEUE_NAME="dispatch-task-tracker"
    > python ./src/agent azure --enable-task-tracker
    """
    args, unknown_args = parse_args()
    os.environ["COMPETITON_PHASE"] = args.phase

    # Run the agent
    asyncio.run(main(args.source, args.enable_task_tracker, args.no_op_workload, unknown_args))
