from __future__ import annotations

from aiohttp import ClientSession

from ..typing import AsyncGenerator
from .base_provider import AsyncGeneratorProvider


class Acytoo(AsyncGeneratorProvider):
    url                   = 'https://chat.acytoo.com'
    working               = True
    supports_gpt_35_turbo = True

    @classmethod
    async def create_async_generator(
        cls,
        model: str,
        messages: list[dict[str, str]],
        proxy: str = None,
        **kwargs
    ) -> AsyncGenerator:

        async with ClientSession(
            headers=_create_header()
        ) as session:
            async with session.post(
                cls.url + '/api/completions',
                proxy=proxy,
                json=_create_payload(messages, **kwargs)
            ) as response:
                response.raise_for_status()
                async for stream in response.content.iter_any():
                    if stream:
                        yield stream.decode()


def _create_header():
    return {
        'accept': '*/*',
        'content-type': 'application/json',
    }


def _create_payload(messages: list[dict[str, str]], temperature: float = 0.5, **kwargs):
    return {
        'key'         : '',
        'model'       : 'gpt-3.5-turbo',
        'messages'    : messages,
        'temperature' : temperature,
        'password'    : ''
    }