"""
Команда для запуска генератора деревьев решений
"""
import asyncio

from django.core.management import BaseCommand

from research.r_tree_app.tree_worker_hanlder import TreeWorkerHandler


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Запуск подписки на выполнение команд из брокера
        """
        worker_handler = TreeWorkerHandler()
        loop = asyncio.get_event_loop()
        task = loop.create_task(worker_handler.run())

        try:
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            pass
