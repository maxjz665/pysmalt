"""
Обработчик команд из брокера сообщений
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from json import JSONDecodeError

from aiomqtt import MqttError, Client
from asgiref.sync import sync_to_async
from sklearn import ensemble, tree

from research.r_bigrams_app.models.tbl_bigram_dataset import TblBigramDataset
from research.r_tree_app.models.tbl_tree_description import TblTreeDescription
from research.r_tree_app.utils import get_pos
from shower.settings import BROKER_HOST, BROKER_PORT
from text_app.models.tbl_textlist import TblTextListDescription
from text_app.models.tbl_word import TblWord


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
                    await client.subscribe("service/bigrams_worker/#")
                    async for message in client.messages:
                        topic = str(message.topic)
                        logging.error("Got message from topic: " + topic)
                        if topic == "service/bigrams_worker/build":
                            try:
                                await self.build_dataset(json.loads(message.payload))
                            except JSONDecodeError:
                                logging.error("JSON decode error")

            except MqttError as error:
                print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
                await asyncio.sleep(reconnect_interval)
            except KeyboardInterrupt:
                return

    @sync_to_async
    def build_dataset(self, params):
        """
        Построение дерева решений для заданного проекта
        """
        if "project_id" not in params:
            logging.error("Missing project_id")
            return

        try:
            dataset_data = TblBigramDataset.objects.get(id=params["project_id"])
        except TblBigramDataset.DoesNotExist:
            logging.error("Invalid project_id")
            return

        dataset_data.build_status = "Расчет биграмм"
        dataset_data.save()

        # перестраиваем дерево решений

        dataset_data.build_status = "Выполнено"
        dataset_data.build_at = datetime.now(timezone.utc)
        dataset_data.save()
        # graph = graphviz.Source(dot_data)
        # graph.render("iris")
        logging.error(f"project: {params['project_id']}: done")
