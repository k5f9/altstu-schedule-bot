import asyncio
import json
import aiohttp
import os

from aiogram import F
from aiogram.filters import Command
from database import set_chat_group, get_chat_group
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from datetime import date, timedelta
from schedule import get_day_schedule
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from database import init_db


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не задана переменная окружения BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
GROUPS_PATH = Path(__file__).parent / "groups.json"
GROUPS_URL = "https://www.altstu.ru/m/s/ajax/"


async def search_groups(query: str) -> list[dict]:
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            GROUPS_URL,
            params={"query": query}
        ) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)

    return data

def load_groups() -> dict[str, str]:
    with GROUPS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def schedule_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="schedule_today"
                ),
                InlineKeyboardButton(
                    text="📅 Завтра",
                    callback_data="schedule_tomorrow"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Сменить группу",
                    callback_data="change_group"
                )
            ],
        ]
    )



@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
            "Привет! Это бот для расписания АлтГТУ.",
            parse_mode="HTML",
            reply_markup=schedule_keyboard()
        )
    

@dp.message(Command("group"))
async def choose_group(message: Message):
    await message.answer(
        "Напиши название своей группы, например ИБ-63."
    )

@dp.message(F.text)
async def save_group(message: Message):
    if not message.text or message.text.startswith("/"):
        return

    query = message.text.strip()

    try:
        groups = await search_groups(query)
    except Exception as e:
        print("Ошибка поиска групп:", repr(e))
        await message.answer("Не удалось найти группы на сайте. Попробуй позже.")
        return

    if not groups:
        await message.answer(
            "Группа не найдена. Попробуй ввести название, например ИБ-63."
        )
        return

    if len(groups) == 1:
        group = groups[0]
        await set_chat_group(
            message.chat.id,
            group["id"],
            group["value"]
        )
        await message.answer(
            f"Группа сохранена: {group['value']}\n"
            "Теперь можешь использовать кнопки 'сегодня' и 'завтра' на предыдущем сообщении."
        )
        return

    # Пока просто покажем найденные варианты.
    text = "Найдено несколько групп. Уточни запрос:\n\n"
    text += "\n".join(f"• {g['value']}" for g in groups[:20])
    await message.answer(text)

async def show_schedule(message, target_date: date):
    saved = await get_chat_group(message.chat.id)

    if saved is None:
        await message.answer(
            "Сначала выбери группу командой /group"
        )
        return

    group_id, group_name = saved

    try:
        lessons = await get_day_schedule(group_id, target_date)
    except Exception as e:
        print(f"Ошибка получения расписания: {e!r}")
        await message.answer(
            "Не удалось получить расписание. Попробуй позже."
        )
        return

    weekdays = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    weekday = weekdays[target_date.weekday()]

    if not lessons:
        await message.answer(
            f"На {target_date:%d.%m.%Y} ({weekday}) "
            "занятий нет или сайт не содержит эту дату."
        )
        return

    lines = [
        f"📚 <b>Расписание · {group_name}</b>",
        f"📅 {target_date:%d.%m.%Y} · {weekday.capitalize()}",
        "",
    ]

    for lesson in lessons:
        lines.append(
            f"🕒 <b>{lesson['start']}–{lesson['end']}</b>"
        )
        lines.append(f"📖 {lesson['subject']}")

        if lesson.get("room"):
            lines.append(f"📍 {lesson['room']}")

        if lesson.get("subgroup"):
            lines.append(f"👥 {lesson['subgroup'].capitalize()}")

        if lesson.get("teacher"):
            lines.append(f"👨‍🏫 {lesson['teacher']}")

        lines.append("")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=schedule_keyboard()
    )


@dp.message(Command("today"))
async def today(message):
    await show_schedule(message, date.today())


@dp.message(Command("tomorrow"))
async def tomorrow(message):
    await show_schedule(
        message,
        date.today() + timedelta(days=1)
    )

@dp.callback_query(F.data == "schedule_today")
async def callback_today(callback: CallbackQuery):
    await callback.answer()
    await show_schedule(
        callback.message,
        date.today()
    )


@dp.callback_query(F.data == "schedule_tomorrow")
async def callback_tomorrow(callback: CallbackQuery):
    await callback.answer()
    await show_schedule(
        callback.message,
        date.today() + timedelta(days=1)
    )


@dp.callback_query(F.data == "change_group")
async def callback_change_group(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Отправь /group, чтобы выбрать другую группу."
    )


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())