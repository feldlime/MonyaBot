import asyncio
from concurrent.futures.thread import ThreadPoolExecutor

import uvloop
from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from asyncpg import create_pool

from .db import DBService
from .handlers import add_handlers
from .log import setup_logging, app_logger
from .settings import get_config
import typing as tp


def setup_asyncio(thread_name_prefix: str) -> None:
    uvloop.install()

    loop = asyncio.get_event_loop()

    executor = ThreadPoolExecutor(thread_name_prefix=thread_name_prefix)
    loop.set_default_executor(executor)

    def handler(_, context: tp.Dict[str, tp.Any]) -> None:
        message = "Caught asyncio exception: {message}".format_map(context)
        app_logger.warning(message)

    loop.set_exception_handler(handler)


setup_asyncio("monya_")
config = get_config()
setup_logging(config)
bot = Bot(token=config.telegram_config.bot_token)

dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware(logger=app_logger))

# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)

loop = asyncio.get_event_loop_policy().new_event_loop()
# loop = asyncio.get_event_loop()


