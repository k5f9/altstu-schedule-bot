
import aiosqlite

DB_PATH = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_groups (
                chat_id INTEGER PRIMARY KEY,
                group_id TEXT NOT NULL,
                group_name TEXT NOT NULL
            )
        """)
        await db.commit()


async def set_chat_group(
    chat_id: int,
    group_id: str,
    group_name: str,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO chat_groups
                (chat_id, group_id, group_name)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                group_id = excluded.group_id,
                group_name = excluded.group_name
        """, (chat_id, group_id, group_name))

        await db.commit()


async def get_chat_group(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT group_id, group_name
            FROM chat_groups
            WHERE chat_id = ?
        """, (chat_id,))

        return await cursor.fetchone()
