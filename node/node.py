import sys
import json
import asyncio
import fastapi
import uvicorn
from .logger import logger
from .reliable_link import ReliableLink


class Node:
    def __init__(self, node_id: int, config_path: str):
        self.node_id: int = node_id

        with open(config_path, encoding='utf-8') as file:
            config = json.load(file)
        self.addresses: list[str] = list(map(
            lambda x: x[1],
            sorted([
                (int(node_id), host)
                for node_id, host in config['addresses'].items()
            ])
        ))

        self.reliable_links: list[ReliableLink] = [
            ReliableLink(f'http://{host}', config['network_timeout'], config['backoff_factor'], config['max_backoff'])
            for node_id, host in enumerate(self.addresses)
            if node_id != self.node_id
        ]

        self.known_msg: set[str] = set()
        self.send_seq_no: int = 0
        self.delivered: list[int] = [0] * len(self.addresses)
        self.msg_holdback: list[dict] = []
        self.table: dict[str, dict[str, any]] = {}

        self.app = fastapi.FastAPI()

        self.app.patch('/items')(self.change_request_handler)
        self.app.get('/items')(self.get_everything_handler)
        self.app.get('/items/{key}')(self.get_item_handler)

        self.app.post('/on_reliable_broadcast_message')(self.on_reliable_broadcast_message)

    def run(self):
        port = int(self.addresses[self.node_id].split(':')[-1])
        uvicorn.run(self.app, host='0.0.0.0', port=port)

    async def reliable_broadcast(self, data):
        for link in self.reliable_links:
            asyncio.create_task(link.send('on_reliable_broadcast_message', data))

    async def on_reliable_broadcast_message(self, request: fastapi.Request):
        data = await request.json()
        hashed_data = json.dumps(data, sort_keys=True)
        if hashed_data not in self.known_msg:
            self.known_msg.add(hashed_data)
            self.on_reliable_casual_order_broadcast_message(data)
        return None

    async def reliable_casual_order_broadcast(self, changes):
        depends = self.delivered
        depends[self.node_id] = self.send_seq_no
        message = {
            'origin': self.node_id,
            'depends': depends,
            'changes': changes,
        }
        self.send_seq_no += 1
        await self.reliable_broadcast(message)
        self.on_reliable_casual_order_broadcast_message(message)

    def extract_msg_that_can_be_delivered(self):
        for i, msg in enumerate(self.msg_holdback):
            if msg['depends'] <= self.delivered:
                self.msg_holdback[i], self.msg_holdback[-1] = self.msg_holdback[-1], self.msg_holdback[i]
                self.msg_holdback.pop()
                self.delivered[msg['origin']] += 1
                return msg
        return None

    def on_reliable_casual_order_broadcast_message(self, msg):
        self.msg_holdback.append(msg)
        while True:
            msg_can_be_delivered = self.extract_msg_that_can_be_delivered()
            if msg_can_be_delivered is None:
                break
            self.on_sync_msg(msg_can_be_delivered['origin'], msg_can_be_delivered['depends'],
                             msg_can_be_delivered['changes'])

    def on_sync_msg(self, origin, depends, changes):
        for key, value in changes.items():
            candidate = {
                'value': value,
                'clock': depends,
                'origin': origin,
            }
            logger.info(f'Considering operation upon {key}, self.table[key]: {self.table.get(key, None)}, '
                         f'candidate: {candidate}')
            if key in self.table and self.table[key]['clock'] > depends:
                logger.fatal(f"IMPOSSIBLE! existing_clock: {self.table[key]['clock']} cannot be bigger "
                             f"than depends: {depends}")
                sys.exit(1)
            if (key not in self.table
                    or self.table[key]['clock'] < depends
                    or self.table[key]['origin'] < origin):
                self.table[key] = candidate
                logger.info('Decided to apply change')
            else:
                logger.info('Decided to reject change')

    async def change_request_handler(self, request: fastapi.Request):
        data = await request.json()
        asyncio.create_task(self.reliable_casual_order_broadcast(data))
        return None

    async def get_everything_handler(self):
        return {key: metadata['value'] for key, metadata in self.table.items()}

    async def get_item_handler(self, key: str):
        return {'value': self.table[key]['value'] if key in self.table else None}
