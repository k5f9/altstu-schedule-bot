
import re
from datetime import date, timedelta

import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime


BASE_URL = "https://www.altstu.ru/m/s/{}/"


async def fetch_schedule(group_id: str) -> str:
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(BASE_URL.format(group_id)) as response:
            response.raise_for_status()
            response.encoding = "utf-8"
            return await response.text()


def parse_schedule(html: str) -> dict[str, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for day_block in soup.select(".block-index"):
        heading = day_block.find("h2")
        if not heading:
            continue

        match = re.search(r"\d{2}\.\d{2}\.\d{2}", heading.get_text())
        if not match:
            continue

        day_date = datetime.strptime(match.group(), "%d.%m.%y").date()
        lessons = []

        for item in day_block.select(".list-group-item"):
            text = item.get_text(" ", strip=True)
            time_match = re.search(
                r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})",
                text,
            )

            subject_tag = item.find("strong")
            if not time_match or not subject_tag:
                continue

            nobrs = [
                tag.get_text(" ", strip=True)
                for tag in item.find_all("nobr")
            ]

            nobrs = [
                " ".join(value.split())
                for value in nobrs
            ]

            lesson_type_match = re.search(
                r"\((л\.р\.|л\.|пр\.)",
                text
            )

            lesson_type = None

            if lesson_type_match:
                lesson_type = {
                    "л.": "Лекция",
                    "пр.": "Практика",
                    "л.р.": "Лабораторная работа",
                }.get(lesson_type_match.group(1))
            
            lesson = {
                "start": time_match.group(1),
                "end": time_match.group(2),
                "subject": subject_tag.get_text(" ", strip=True),
                "details": text,
                "room": None,
                "teacher": None,
                "subgroup": None,
                "type": lesson_type,
            }

            for value in nobrs:
                value = " ".join(value.split())

                if value.lower().startswith("подгруппа"):
                    lesson["subgroup"] = value

                elif (
                    value.startswith("кабинет ")
                    or re.match(r"^\d+(-\d+)?\s+[А-ЯЁ]+$", value)
                ):
                    lesson["room"] = value

                else:
                    lesson["teacher"] = value

            lessons.append(lesson)

        result[day_date.isoformat()] = lessons

    return result


async def get_day_schedule(group_id: str, target_date: date):
    html = await fetch_schedule(group_id)
    schedule = parse_schedule(html)
    return schedule.get(target_date.isoformat(), [])


async def get_today(group_id: str):
    return await get_day_schedule(group_id, date.today())


async def get_tomorrow(group_id: str):
    return await get_day_schedule(
        group_id,
        date.today() + timedelta(days=1),
    )
