"""
Обработчик команд из брокера сообщений
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from itertools import islice
from json import JSONDecodeError

from aiomqtt import MqttError, Client
from asgiref.sync import sync_to_async

from research.r_ngrams_app.models.tbl_ngram_dataset import TblBigramDataset
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_text import TblText


class BigramsWorkerHandler(object):

    async def run(self):
        """
        Запуск бесконечного цикла обработки сообщений
        """
        reconnect_interval = 5  # In seconds
        while True:
            try:
                async with Client(BROKER_HOST, BROKER_PORT, identifier="tg_bot_" + str(id(self))) as client:
                    logging.debug("TG bot broker connected successfully")
                    await client.subscribe("service/ngrams_worker/#")
                    async for message in client.messages:
                        topic = str(message.topic)
                        logging.debug("Got message from topic: %s", topic)
                        if topic == "service/ngrams_worker/build":
                            try:
                                await self.build_dataset(json.loads(message.payload))
                            except JSONDecodeError:
                                logging.error("JSON decode error")

            except MqttError as error:
                logging.error(f'Error "%s". Reconnecting in %s seconds.', error, reconnect_interval)
                await asyncio.sleep(reconnect_interval)
            except KeyboardInterrupt:
                return

    @sync_to_async
    def build_dataset(self, params):
        """
        Построение датасета N-грамм для заданного проекта
        """
        if "project_id" not in params:
            logging.error("Missing project_id")
            return

        try:
            dataset_data = TblBigramDataset.objects.get(id=params["project_id"])
        except TblBigramDataset.DoesNotExist:
            logging.error("Invalid project_id")
            return

        dataset_data.build_status = "Расчет N-грамм"
        dataset_data.save()

        if dataset_data.text_group is None:
            texts = TblText.get_texts(exclude_deleted=True, exclude_not_verified=True)
        else:
            texts = dataset_data.text_group.items

        ngrams = {}
        for text in texts:
            content = text.get_content()
            dataset_data.extract_ngrams(content, ngrams)

        # сохраняем датасет
        ngrams = dict(sorted(ngrams.items(), key=lambda x:x[1], reverse=True))
        ngrams = list(islice(ngrams.items(), dataset_data.max_ngrams))
        dataset_data.build_status = "Выполнено"
        dataset_data.build_at = datetime.now(timezone.utc)
        dataset_data.content = ngrams
        dataset_data.save()
        # graph = graphviz.Source(dot_data)
        # graph.render("iris")
        logging.debug(f"project: %s: done", params['project_id'])
