"""
Команда для запуска генератора датасетов биграмм
"""
import asyncio

from django.core.management import BaseCommand

from research.r_bigrams_app.bigrams_worker_hanlder import BigramsWorkerHandler


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
