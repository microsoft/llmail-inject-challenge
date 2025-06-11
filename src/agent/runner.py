import time
from utils.better_logging import logger

from agent.workload import Workload
from agent.job_source import JobSource, JobMessage, JobResult
from agent.telemetry import trace, tracer, Link, StatusCode, SpanKind
from api.models import to_telemetry_attributes


class JobRunner:
    def __init__(self, source: JobSource, workload: Workload):
        self.source = source
        self.workload = workload

    async def run(self):
        while True:
            try:
                with tracer.start_as_current_span("JobRunner.get_next_job", kind=SpanKind.CONSUMER) as trace:
                    job = await self.source.get_next_job()

                if job:
                    result = None
                    with tracer.start_as_current_span(
                        "job",
                        context=job.get_trace_context(),
                        kind=SpanKind.CONSUMER,
                        attributes=to_telemetry_attributes(job),
                    ) as job_span:
                        try:
                            with tracer.start_as_current_span(
                                "job.execute",
                            ):
                                result = await self.workload.execute(job)

                            with tracer.start_as_current_span(
                                "job.handle_result",
                                attributes=to_telemetry_attributes(result),
                            ):
                                await self.source.handle_result(job, result)
                        except Exception as ex:
                            logger.error(f"Error processing job {job.job_id}", exc_info=True)
                            job_span.record_exception(ex)
                            job_span.set_status(StatusCode.ERROR, str(ex))

                            with tracer.start_as_current_span(
                                "job.handle_job_failure",
                                attributes={
                                    **to_telemetry_attributes(job),
                                    **to_telemetry_attributes(result),
                                    "exception": str(ex),
                                },
                            ):
                                await self.source.handle_job_failure(job, result, ex)

                else:
                    logger.info("No more jobs to process.")
                    break
            except Exception as ex:
                time.sleep(5)
                logger.warning("Failed to retrieve a job for processing, trying again...", exc_info=True)
