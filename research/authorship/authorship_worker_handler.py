import asyncio
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class AuthorshipWorkerHandler:
    """
    DB-polling worker for authorship experiments.
    Polls every 5 s for experiments with build_status='queued',
    executes them one at a time (no parallelism).
    """

    async def run(self):
        logger.info("Authorship worker started, polling every 5 s")
        while True:
            experiment = await self.get_queued_experiment()
            if experiment is not None:
                await self.process_experiment(experiment)
            else:
                await asyncio.sleep(5)

    @sync_to_async
    def get_queued_experiment(self):
        from research.authorship.models import TblAttributionExperiment
        return (
            TblAttributionExperiment.objects
            .filter(build_status='queued')
            .order_by('created_at')
            .first()
        )

    @sync_to_async
    def process_experiment(self, experiment):
        from research.authorship.utils.profile_method import execute_existing_experiment as run_profile
        from research.authorship.utils.ml_method import execute_existing_experiment as run_ml

        experiment.build_status = 'running'
        experiment.started_at = timezone.now()
        experiment.error_message = ''
        experiment.save(update_fields=['build_status', 'started_at', 'error_message'])
        logger.info("Running experiment id=%s method=%s", experiment.id, experiment.method)

        try:
            if experiment.method == 'profile':
                run_profile(experiment)
            else:
                run_ml(experiment)
            experiment.build_status = 'completed'
            logger.info("Experiment id=%s completed", experiment.id)
        except Exception as exc:
            experiment.build_status = 'failed'
            experiment.error_message = str(exc)
            logger.exception("Experiment id=%s failed", experiment.id)

        experiment.finished_at = timezone.now()
        experiment.save(update_fields=['build_status', 'finished_at', 'error_message'])
