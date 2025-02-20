"""
Команда для запуска генератора датасетов N-грамм
"""
import asyncio

from django.core.management import BaseCommand

from research.r_ngrams_app.ngrams_worker_hanlder import BigramsWorkerHandler


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Запуск подписки на выполнение команд из брокера
        """
        worker_handler = BigramsWorkerHandler()
        loop = asyncio.get_event_loop()
        task = loop.create_task(worker_handler.run())

        try:
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            pass
