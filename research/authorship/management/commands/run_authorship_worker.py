import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Authorship worker: polls DB every 5 s and executes queued experiments."

    def handle(self, *args, **options):
        from research.authorship.authorship_worker_handler import AuthorshipWorkerHandler
        self.stdout.write("Starting authorship worker (Ctrl+C to stop)...")
        asyncio.run(AuthorshipWorkerHandler().run())
