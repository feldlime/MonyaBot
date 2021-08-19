import asyncio

from asyncpg import create_pool

from monya.app import bot, dp
from monya.db import DBService
from monya.handlers import add_handlers
from monya.settings import get_config


async def main():
    config = get_config()
    db_config = config.db_config.dict()
    pool_config = db_config.pop("db_pool_config")
    pool_config["dsn"] = pool_config.pop("db_url")
    pool = create_pool(**pool_config)
    db_service = DBService(pool=pool)
    try:
        add_handlers(dp, db_service, config)
        await db_service.setup()
        await dp.start_polling()
    finally:
        await bot.close()
        await db_service.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
