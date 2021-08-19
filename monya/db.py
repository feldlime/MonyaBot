from uuid import UUID
import typing as tp
from asyncpg import Pool, UniqueViolationError
from pydantic import BaseModel

from monya.log import app_logger


class UserAlreadyExistsError(Exception):
    pass


class UserNotExistsError(Exception):
    pass


class ChatAlreadyExistsError(Exception):
    pass


class DBService(BaseModel):
    pool: Pool

    class Config:
        arbitrary_types_allowed = True

    async def setup(self) -> None:
        await self.pool
        app_logger.info("Db service initialized")

    async def cleanup(self) -> None:
        await self.pool.close()
        app_logger.info("Db service shutdown")

    async def ping(self) -> bool:
        return await self.pool.fetchval("SELECT TRUE")

    async def _get_user_id(self, t_chat_id: int, name: str) -> tp.Optional[UUID]:
        query = """
            SELECT user_id
            FROM users u
                JOIN chats c on u.chat_id = c.chat_id
            WHERE c.t_chat_id = $1::INTEGER AND u.name = $2::VARCHAR
        """
        user_id = await self.pool.fetchval(query, t_chat_id, name)
        return user_id

    async def add_chat(self, t_chat_id: int) -> None:
        query = """
            INSERT INTO chats
                (t_chat_id)
            VALUES
                ($1::INTEGER)
        """
        try:
            await self.pool.execute(query, t_chat_id)
        except UniqueViolationError as e:
            raise ChatAlreadyExistsError from e

    async def reset(self, t_chat_id: int) -> None:
        query = """
            DELETE FROM actions
            WHERE user_id IN (
                SELECT user_id
                FROM users u
                    JOIN chats c on u.chat_id = c.chat_id
                WHERE c.t_chat_id = $1::INTEGER
            )
        """
        await self.pool.execute(query, t_chat_id)

    async def add_user(self, t_chat_id: int, name: str) -> None:
        user_id = await self._get_user_id(t_chat_id, name)

        if user_id is not None:
            raise UserAlreadyExistsError

        query_insert = """
            INSERT INTO users
                (chat_id, name)
            VALUES
                (
                    (SELECT chat_id FROM chats WHERE t_chat_id = $1::INTEGER),
                    $2::VARCHAR
                )
        """
        await self.pool.execute(query_insert, t_chat_id, name)

    async def delete_user(self, t_chat_id: int, name: str):
        user_id = await self._get_user_id(t_chat_id, name)

        if user_id is None:
            raise UserNotExistsError

        query = """
            DELETE FROM users
            WHERE user_id = $1::UUID
        """
        await self.pool.execute(query, user_id)

    async def get_chat_users(self, t_chat_id: int) -> tp.List[str]:
        query = """
            SELECT name
            FROM users u
                JOIN chats c on u.chat_id = c.chat_id
            WHERE c.t_chat_id = $1::INTEGER
        """
        rows = await self.pool.fetch(query, t_chat_id)
        return [row["name"] for row in rows]

    async def add_operation(
        self,
        t_chat_id: int,
        name: str,
        amount: float,
        comment: str,
    ) -> None:
        user_id = await self._get_user_id(t_chat_id, name)
        if user_id is None:
            raise UserNotExistsError

        query = """
            INSERT INTO actions
                (user_id, amount, comment)
            VALUES
                (
                    $1::UUID,
                    $2::FLOAT,
                    $3::VARCHAR
                )
        """
        await self.pool.execute(query, user_id, amount, comment)

    async def get_user_operations(
        self,
        t_chat_id: int,
        name: str,
    ) -> tp.List[tp.Tuple[float, str]]:
        user_id = await self._get_user_id(t_chat_id, name)
        if user_id is None:
            raise UserNotExistsError
        query = """
            SELECT amount, comment
            FROM actions
            WHERE user_id = $1::UUID
            ORDER BY added_at
        """
        operations = await self.pool.fetch(query, user_id)
        return [(op["amount"], op["comment"]) for op in operations]

    async def get_chat_operations(
        self,
        t_chat_id: int,
    ) -> tp.List[tp.Tuple[str, float, str]]:
        query = """
            SELECT u.name, amount, comment
            FROM actions a
                JOIN users u on u.user_id = a.user_id
                JOIN chats c on c.chat_id = u.chat_id
            WHERE c.t_chat_id = $1::INTEGER
            ORDER BY a.added_at
        """
        operations = await self.pool.fetch(query, t_chat_id)
        return [(op["name"], op["amount"], op["comment"]) for op in operations]
