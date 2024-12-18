import asyncio
import random
import httpx
from .logger import logger


class ReliableLink:
    def __init__(self, base_url: str, timeout: float, backoff_factor: float, max_backoff: float):
        self.base_url = base_url
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))

    async def send(self, endpoint: str, json_data: dict) -> httpx.Response:
        attempt = 0
        max_backoff_dominants = False
        while True:
            try:
                url = f'{self.base_url}/{endpoint}'
                logger.info(f'ReliableLink: attempt No {attempt} to send {json_data} to {url}')
                response = await self.client.post(url, json=json_data)
                response.raise_for_status()
                return response
            except Exception as e:
                attempt += 1
                if not max_backoff_dominants:
                    backoff = self.backoff_factor ** attempt + random.uniform(0, 1)
                    if backoff > self.max_backoff:
                        max_backoff_dominants = True
                        backoff = self.max_backoff
                logger.info(f'ReliableLink: received error {e}, will try again after {backoff}s')
                await asyncio.sleep(backoff)  # Exponential backoff with jitter

    async def close(self):
        await self.client.aclose()
