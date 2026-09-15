# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

import aiohttp
from aiohttp import web
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    TelegramObject,
)

# ============================================================================
# سيرفر وهمي لإبقاء البوت نشطاً على المنصات السحابية (Render / Heroku)
# ============================================================================

async def handle(request):
    return web.Response(text="Quran Bot is running online 24/7!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ============================================================================
# الإعدادات العامة والأرقام المعرفية للإيموجيات المخصصة
# ============================================================================

BOT_TOKEN = "8985243390:AAFwMzMbfit3_0OKb77KvGPOj5ZSBQmzRpU"
DEVELOPER_USERNAME = "mh5_c"
OWNER_ID = 1317171223

# معرفات الإيموجيات المخصصة
ID_WELCOME_EMOJI = "5355194215129169036"
ID_BOT_OWNER_EMOJI = "6158862632926319619"
ID_DEV_USERNAME_EMOJI = "6269163801178804220"
ID_RECITER_EMOJI = "6071346841704733378"
ID_RECITER_SELECTED_EMOJI = "6269163801178804220"
ID_WAITING = "5355226302829835543"
ID_GRID_TITLE = "6070970164482939513"
ID_RANGE_TITLE = "6071000899268910391"
ID_ALERT = "6269316311172518259"
ID_PAGE_CAPTION = "6071355019322465070"
ID_SECURITY_PANEL = "6269316311172518259"
ID_SURAH_CHOSEN = "5830252584870351231"

EMOJI_WELCOME = f'<tg-emoji emoji-id="{ID_WELCOME_EMOJI}">👋</tg-emoji>'
EMOJI_BOT_OWNER = f'<tg-emoji emoji-id="{ID_BOT_OWNER_EMOJI}">👑</tg-emoji>'
EMOJI_DEV_USERNAME = f'<tg-emoji emoji-id="{ID_DEV_USERNAME_EMOJI}">👤</tg-emoji>'
EMOJI_RECITER_HTML = f'<tg-emoji emoji-id="{ID_RECITER_EMOJI}">🎙</tg-emoji>'
EMOJI_WAITING_HTML = f'<tg-emoji emoji-id="{ID_WAITING}">⏳</tg-emoji>'
EMOJI_SURAH_CHOSEN = f'<tg-emoji emoji-id="{ID_SURAH_CHOSEN}">✨</tg-emoji>'
EMOJI_SELECT_MODE = f'<tg-emoji emoji-id="{ID_WELCOME_EMOJI}">⚙️</tg-emoji>'
EMOJI_GRID_TITLE = f'<tg-emoji emoji-id="{ID_GRID_TITLE}">📄</tg-emoji>'
EMOJI_RANGE_TITLE = f'<tg-emoji emoji-id="{ID_RANGE_TITLE}">📚</tg-emoji>'
EMOJI_ALERT = f'<tg-emoji emoji-id="{ID_ALERT}">⚠️</tg-emoji>'
EMOJI_CAPTION_HTML = f'<tg-emoji emoji-id="{ID_PAGE_CAPTION}">📖</tg-emoji>'
EMOJI_SECURITY_PANEL = f'<tg-emoji emoji-id="{ID_SECURITY_PANEL}">🛡️</tg-emoji>'

RECITERS = [
    {"key": "dussary", "name": "د. ياسر الدوسري", "audio_url": "https://everyayah.com/data/Yasser_Ad-Dussary_128kbps"},
    {"key": "minshawi", "name": "محمد صديق المنشاوي", "audio_url": "https://everyayah.com/data/Minshawy_Murattal_128kbps"},
    {"key": "abdul_basit", "name": "عبد الباسط عبد الصمد", "audio_url": "https://everyayah.com/data/Abdul_Basit_Murattal_192kbps"},
    {"key": "sudais", "name": "عبد الرحمن السديس", "audio_url": "https://everyayah.com/data/Abdurrahmaan_As-Sudais_192kbps"},
    {"key": "shuraym", "name": "سعود الشريم", "audio_url": "https://everyayah.com/data/Saood_ash-Shuraym_128kbps"},
]
RECITERS_DICT = {r["key"]: r for r in RECITERS}
DEFAULT_RECITER_KEY = RECITERS[0]["key"]
USER_RECITER: dict[int, str] = {}
USER_THEME: dict[int, str] = {}

AZKAR_DATA = {
    "sabah": [
        {"text": "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ لاَ إِلَهَ إِلاَّ اللَّهُ وَحْدَهُ لاَ شَرِيكَ لَهُ.", "count": 1},
        {"text": "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ وَإِلَيْكَ النُّشُورُ.", "count": 1},
        {"text": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ: عَدَدَ خَلْقِهِ، وَرِضَا نَفْسِهِ، وَزِنَةَ عَرْشِهِ، وَمِدَادَ كَلِمَاتِهِ.", "count": 3},
        {"text": "يَا حَيُّ يَا قَيُّومُ بِرَحْمَتِكَ أَسْتَغِيثُ أَصْلِحْ لِي شَأْنِي كُلَّهُ وَلاَ تَكِلْنِي إِلَى نَفْسِي طَرْفَةَ عَيْنٍ.", "count": 1}
    ],
    "mosa": [
        {"text": "أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ لاَ إِلَهَ إِلاَّ اللَّهُ وَحْدَهُ لاَ شَرِيكَ لَهُ.", "count": 1},
        {"text": "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ وَإِلَيْكَ الْمَصِيرُ.", "count": 1},
        {"text": "أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ.", "count": 3}
    ],
    "sleep": [
        {"text": "بِاسْمِكَ رَبِّي وَضَعْتُ جَنْبِي، وَبِاسْمِكَ أَرْفَعُهُ، فَإِنْ أَمْسَكْتَ نَفْسِي فَارْحَمْهَا.", "count": 1},
        {"text": "اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ.", "count": 3}
    ]
}

QURAN_HEADER_TEXT = f'أختر <b>سورة</b> {EMOJI_SELECT_MODE}'
RECITER_HEADER_TEXT = f'أختر <b>القارئ</b> {EMOJI_RECITER_HTML}'

def get_home_text(user_id: Optional[int]) -> str:
    theme = USER_THEME.get(user_id, "light")
    theme_status = "🌙 الوضع الليلي مفعل" if theme == "dark" else "☀️ الوضع النهاري مفعل"
    return (
        f"<b>أهلاً بك في بوت القرآن الكريم والأذكار</b> {EMOJI_WELCOME}\n\n"
        f"الحالة الحالية: <b>{theme_status}</b>\n\n"
        f"<b>Bot Owner</b> {EMOJI_BOT_OWNER} <b>@{DEVELOPER_USERNAME}</b> {EMOJI_DEV_USERNAME}"
    )

PAGE_IMAGE_URL_TEMPLATE = "https://raw.githubusercontent.com/QuranHub/quran-pages-images/main/kfgqpc/hafs-wasat/{page}.jpg"
QURAN_COM_PAGE_VERSES_API_URL = "https://api.quran.com/api/v4/verses/by_page/{page}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("quran_bot")

REQUEST_TIMEOUT_SECONDS = 15
DOWNLOAD_CONCURRENCY = 10
MEDIA_GROUP_CHUNK_SIZE = 10
MAX_RANGE_PAGES = 20
PAGES_PER_GRID_SCREEN = 20
GRID_COLUMNS = 5
SURAHS_PER_PAGE = 15
AUDIO_DOWNLOAD_CONCURRENCY = 8

CACHE_DIR = Path("bot_cache")
PAGE_IMAGES_DIR = CACHE_DIR / "pages"
AUDIO_FILES_DIR = CACHE_DIR / "audio"
PAGE_FILE_ID_CACHE_PATH = CACHE_DIR / "page_file_ids.json"

for _d in (CACHE_DIR, PAGE_IMAGES_DIR, AUDIO_FILES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

def _load_page_file_id_cache() -> dict[int, str]:
    if PAGE_FILE_ID_CACHE_PATH.exists():
        try:
            raw = json.loads(PAGE_FILE_ID_CACHE_PATH.read_text(encoding="utf-8"))
            return {int(k): v for k, v in raw.items()}
        except Exception:
            pass
    return {}

def save_page_file_id_cache() -> None:
    try:
        PAGE_FILE_ID_CACHE_PATH.write_text(
            json.dumps({str(k): v for k, v in PAGE_CACHE.items()}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass

PAGE_CACHE: dict[int, str] = _load_page_file_id_cache()
AUDIO_CACHE: dict[tuple[str, int, int], bytes] = {}

BOT_USERS: dict[int, dict] = {}
DAILY_ACTIVITY: dict[str, dict[int, list[dict]]] = {}

def is_owner(user_id: Optional[int]) -> bool:
    return bool(OWNER_ID) and user_id == OWNER_ID

router = Router()

# ============================================================================
# قائمة السور الـ 114 بالكامل
# ============================================================================
SURAHS = [
    {"key": "1", "name": "الفاتحة", "number": 1, "start_page": 1, "end_page": 1},
    {"key": "2", "name": "البقرة", "number": 2, "start_page": 2, "end_page": 49},
    {"key": "3", "name": "آل عمران", "number": 3, "start_page": 50, "end_page": 76},
    {"key": "4", "name": "النساء", "number": 4, "start_page": 77, "end_page": 106},
    {"key": "5", "name": "المائدة", "number": 5, "start_page": 106, "end_page": 127},
    {"key": "6", "name": "الأنعام", "number": 6, "start_page": 128, "end_page": 150},
    {"key": "7", "name": "الأعراف", "number": 7, "start_page": 151, "end_page": 176},
    {"key": "8", "name": "الأنفال", "number": 8, "start_page": 177, "end_page": 186},
    {"key": "9", "name": "التوبة", "number": 9, "start_page": 187, "end_page": 207},
    {"key": "10", "name": "يونس", "number": 10, "start_page": 208, "end_page": 221},
    {"key": "11", "name": "هود", "number": 11, "start_page": 221, "end_page": 235},
    {"key": "12", "name": "يوسف", "number": 12, "start_page": 235, "end_page": 248},
    {"key": "13", "name": "الرعد", "number": 13, "start_page": 249, "end_page": 255},
    {"key": "14", "name": "إبراهيم", "number": 14, "start_page": 255, "end_page": 261},
    {"key": "15", "name": "الحجر", "number": 15, "start_page": 262, "end_page": 267},
    {"key": "16", "name": "النحل", "number": 16, "start_page": 267, "end_page": 281},
    {"key": "17", "name": "الإسراء", "number": 17, "start_page": 282, "end_page": 293},
    {"key": "18", "name": "الكهف", "number": 18, "start_page": 293, "end_page": 304},
    {"key": "19", "name": "مريم", "number": 19, "start_page": 305, "end_page": 312},
    {"key": "20", "name": "طه", "number": 20, "start_page": 312, "end_page": 321},
    {"key": "21", "name": "الأنبياء", "number": 21, "start_page": 322, "end_page": 331},
    {"key": "22", "name": "الحج", "number": 22, "start_page": 332, "end_page": 341},
    {"key": "23", "name": "المؤمنون", "number": 23, "start_page": 342, "end_page": 349},
    {"key": "24", "name": "النور", "number": 24, "start_page": 350, "end_page": 359},
    {"key": "25", "name": "الفرقان", "number": 25, "start_page": 359, "end_page": 366},
    {"key": "26", "name": "الشعراء", "number": 26, "start_page": 367, "end_page": 376},
    {"key": "27", "name": "النمل", "number": 27, "start_page": 377, "end_page": 385},
    {"key": "28", "name": "القصص", "number": 28, "start_page": 385, "end_page": 396},
    {"key": "29", "name": "العنكبوت", "number": 29, "start_page": 396, "end_page": 404},
    {"key": "30", "name": "الروم", "number": 30, "start_page": 404, "end_page": 410},
    {"key": "31", "name": "لقمان", "number": 31, "start_page": 411, "end_page": 414},
    {"key": "32", "name": "السجدة", "number": 32, "start_page": 415, "end_page": 417},
    {"key": "33", "name": "الأحزاب", "number": 33, "start_page": 418, "end_page": 427},
    {"key": "34", "name": "سبأ", "number": 34, "start_page": 428, "end_page": 434},
    {"key": "35", "name": "فاطر", "number": 35, "start_page": 434, "end_page": 440},
    {"key": "36", "name": "يس", "number": 36, "start_page": 440, "end_page": 445},
    {"key": "37", "name": "الصافات", "number": 37, "start_page": 445, "end_page": 452},
    {"key": "38", "name": "ص", "number": 38, "start_page": 453, "end_page": 458},
    {"key": "39", "name": "الزمر", "number": 39, "start_page": 458, "end_page": 467},
    {"key": "40", "name": "غافر", "number": 40, "start_page": 467, "end_page": 476},
    {"key": "41", "name": "فصلت", "number": 41, "start_page": 477, "end_page": 482},
    {"key": "42", "name": "الشورى", "number": 42, "start_page": 483, "end_page": 489},
    {"key": "43", "name": "الزخرف", "number": 43, "start_page": 489, "end_page": 495},
    {"key": "44", "name": "الدخان", "number": 44, "start_page": 496, "end_page": 498},
    {"key": "45", "name": "الجاثية", "number": 45, "start_page": 499, "end_page": 502},
    {"key": "46", "name": "الأحقاف", "number": 46, "start_page": 502, "end_page": 506},
    {"key": "47", "name": "محمد", "number": 47, "start_page": 507, "end_page": 510},
    {"key": "48", "name": "الفتح", "number": 48, "start_page": 511, "end_page": 515},
    {"key": "49", "name": "الحجرات", "number": 49, "start_page": 515, "end_page": 517},
    {"key": "50", "name": "ق", "number": 50, "start_page": 518, "end_page": 520},
    {"key": "51", "name": "الذاريات", "number": 51, "start_page": 520, "end_page": 523},
    {"key": "52", "name": "الطور", "number": 52, "start_page": 523, "end_page": 525},
    {"key": "53", "name": "النجم", "number": 53, "start_page": 526, "end_page": 528},
    {"key": "54", "name": "القمر", "number": 54, "start_page": 528, "end_page": 531},
    {"key": "55", "name": "الرحمن", "number": 55, "start_page": 531, "end_page": 534},
    {"key": "56", "name": "الواقعة", "number": 56, "start_page": 534, "end_page": 537},
    {"key": "57", "name": "الحديد", "number": 57, "start_page": 537, "end_page": 541},
    {"key": "58", "name": "المجادلة", "number": 58, "start_page": 542, "end_page": 545},
    {"key": "59", "name": "الحشر", "number": 59, "start_page": 545, "end_page": 548},
    {"key": "60", "name": "الممتحنة", "number": 60, "start_page": 549, "end_page": 551},
    {"key": "61", "name": "الصف", "number": 61, "start_page": 551, "end_page": 553},
    {"key": "62", "name": "الجمعة", "number": 62, "start_page": 553, "end_page": 554},
    {"key": "63", "name": "المنافقون", "number": 63, "start_page": 554, "end_page": 555},
    {"key": "64", "name": "التغابن", "number": 64, "start_page": 556, "end_page": 557},
    {"key": "65", "name": "الطلاق", "number": 65, "start_page": 558, "end_page": 559},
    {"key": "66", "name": "التحريم", "number": 66, "start_page": 560, "end_page": 561},
    {"key": "67", "name": "الملك", "number": 67, "start_page": 562, "end_page": 564},
    {"key": "68", "name": "القلم", "number": 68, "start_page": 564, "end_page": 566},
    {"key": "69", "name": "الحاقة", "number": 69, "start_page": 566, "end_page": 568},
    {"key": "70", "name": "المعارج", "number": 70, "start_page": 568, "end_page": 570},
    {"key": "71", "name": "نوح", "number": 71, "start_page": 570, "end_page": 571},
    {"key": "72", "name": "الجن", "number": 72, "start_page": 572, "end_page": 573},
    {"key": "73", "name": "المزمل", "number": 73, "start_page": 574, "end_page": 575},
    {"key": "74", "name": "المدثر", "number": 74, "start_page": 575, "end_page": 577},
    {"key": "75", "name": "القيامة", "number": 75, "start_page": 577, "end_page": 578},
    {"key": "76", "name": "الإنسان", "number": 76, "start_page": 578, "end_page": 580},
    {"key": "77", "name": "المرسلات", "number": 77, "start_page": 580, "end_page": 581},
    {"key": "78", "name": "النبأ", "number": 78, "start_page": 582, "end_page": 582},
    {"key": "79", "name": "النازعات", "number": 79, "start_page": 583, "end_page": 584},
    {"key": "80", "name": "عبس", "number": 80, "start_page": 585, "end_page": 585},
    {"key": "81", "name": "التكوير", "number": 81, "start_page": 586, "end_page": 586},
    {"key": "82", "name": "الانفطار", "number": 82, "start_page": 587, "end_page": 587},
    {"key": "83", "name": "المطففين", "number": 83, "start_page": 587, "end_page": 589},
    {"key": "84", "name": "الانشقاق", "number": 84, "start_page": 589, "end_page": 590},
    {"key": "85", "name": "البروج", "number": 85, "start_page": 590, "end_page": 590},
    {"key": "86", "name": "الطارق", "number": 86, "start_page": 591, "end_page": 591},
    {"key": "87", "name": "الأعلى", "number": 87, "start_page": 591, "end_page": 592},
    {"key": "88", "name": "الغاشية", "number": 88, "start_page": 592, "end_page": 592},
    {"key": "89", "name": "الفجر", "number": 89, "start_page": 593, "end_page": 594},
    {"key": "90", "name": "البلد", "number": 90, "start_page": 594, "end_page": 594},
    {"key": "91", "name": "الشمس", "number": 91, "start_page": 595, "end_page": 595},
    {"key": "92", "name": "الليل", "number": 92, "start_page": 595, "end_page": 596},
    {"key": "93", "name": "الضحى", "number": 93, "start_page": 596, "end_page": 596},
    {"key": "94", "name": "الشرح", "number": 94, "start_page": 596, "end_page": 596},
    {"key": "95", "name": "التين", "number": 95, "start_page": 597, "end_page": 597},
    {"key": "96", "name": "العلق", "number": 96, "start_page": 597, "end_page": 597},
    {"key": "97", "name": "القدر", "number": 97, "start_page": 598, "end_page": 598},
    {"key": "98", "name": "البينة", "number": 98, "start_page": 598, "end_page": 599},
    {"key": "99", "name": "الزلزلة", "number": 99, "start_page": 599, "end_page": 599},
    {"key": "100", "name": "العاديات", "number": 100, "start_page": 599, "end_page": 600},
    {"key": "101", "name": "القارعة", "number": 101, "start_page": 600, "end_page": 600},
    {"key": "102", "name": "التكاثر", "number": 102, "start_page": 600, "end_page": 600},
    {"key": "103", "name": "العصر", "number": 103, "start_page": 601, "end_page": 601},
    {"key": "104", "name": "الهمزة", "number": 104, "start_page": 601, "end_page": 601},
    {"key": "105", "name": "الفيل", "number": 105, "start_page": 601, "end_page": 601},
    {"key": "106", "name": "قريش", "number": 106, "start_page": 602, "end_page": 602},
    {"key": "107", "name": "الماعون", "number": 107, "start_page": 602, "end_page": 602},
    {"key": "108", "name": "الكوثر", "number": 108, "start_page": 602, "end_page": 602},
    {"key": "109", "name": "الكافرون", "number": 109, "start_page": 603, "end_page": 603},
    {"key": "110", "name": "النصر", "number": 110, "start_page": 603, "end_page": 603},
    {"key": "111", "name": "المسد", "number": 111, "start_page": 603, "end_page": 603},
    {"key": "112", "name": "الإخلاص", "number": 112, "start_page": 604, "end_page": 604},
    {"key": "113", "name": "الفلق", "number": 113, "start_page": 604, "end_page": 604},
    {"key": "114", "name": "الناس", "number": 114, "start_page": 604, "end_page": 604},
]
SURAHS_DICT = {s["key"]: s for s in SURAHS}

class QuranStates(StatesGroup):
    waiting_for_range = State()
    waiting_for_city = State()

http_session: Optional[aiohttp.ClientSession] = None

class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user and not user.is_bot:
            now = datetime.now()
            today_key = now.strftime("%Y-%m-%d")

            record = BOT_USERS.get(user.id)
            if record is None:
                record = {"user_id": user.id, "first_seen": now, "message_count": 0}
                BOT_USERS[user.id] = record

            record["username"] = user.username
            record["first_name"] = user.first_name
            record["last_name"] = user.last_name
            record["last_seen"] = now
            record["message_count"] = record.get("message_count", 0) + 1

            day_bucket = DAILY_ACTIVITY.setdefault(today_key, {})
            user_log = day_bucket.setdefault(user.id, [])
            preview = (event.text or event.caption or "📎 وسائط").strip()
            user_log.append({"time": now, "text": preview})

        return await handler(event, data)

async def download_bytes(url: str, timeout_seconds: int = REQUEST_TIMEOUT_SECONDS) -> Optional[bytes]:
    assert http_session is not None
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with http_session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.read()
    except Exception as e:
        logger.warning("خطأ أثناء التحميل: %s", e)
    return None

async def download_bytes_with_retry(url: str, retries: int = 3) -> Optional[bytes]:
    for attempt in range(1, retries + 1):
        data = await download_bytes(url)
        if data is not None:
            return data
        await asyncio.sleep(0.4 * attempt)
    return None

async def fetch_page_jpg(page: int) -> Optional[bytes]:
    disk_path = PAGE_IMAGES_DIR / f"{page}.jpg"
    if disk_path.exists():
        try:
            return disk_path.read_bytes()
        except Exception:
            pass

    image_url = PAGE_IMAGE_URL_TEMPLATE.format(page=page)
    data = await download_bytes_with_retry(image_url, retries=5)
    if data:
        try:
            disk_path.write_bytes(data)
        except Exception:
            pass
    return data

async def fetch_pages_as_media_group(pages: list[int]) -> list[tuple[int, InputMediaPhoto]]:
    semaphore = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)

    async def process(page: int) -> Optional[tuple[int, InputMediaPhoto]]:
        caption_text = f"<b>صفحة {page}</b> {EMOJI_CAPTION_HTML}"
        if page in PAGE_CACHE:
            return page, InputMediaPhoto(media=PAGE_CACHE[page], caption=caption_text, parse_mode=ParseMode.HTML)

        async with semaphore:
            jpg = await fetch_page_jpg(page)
            if jpg is None:
                return None
            file = BufferedInputFile(jpg, filename=f"page_{page}.jpg")
            return page, InputMediaPhoto(media=file, caption=caption_text, parse_mode=ParseMode.HTML)

    results = await asyncio.gather(*(process(p) for p in pages))
    return [item for item in results if item]

def chunk_list(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]

async def get_page_ayahs(page: int) -> list[tuple[int, int]]:
    if page == 1:
        return [(1, a) for a in range(1, 8)]

    assert http_session is not None
    url = f"{QURAN_COM_PAGE_VERSES_API_URL.format(page=page)}?per_page=50"
    try:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        async with http_session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                return []
            payload = await resp.json()
    except Exception:
        return []

    result = []
    for verse in payload.get("verses", []):
        verse_key = verse.get("verse_key", "")
        if ":" in verse_key:
            s, a = verse_key.split(":")
            result.append((int(s), int(a)))
    return result

async def build_pages_audio(pages: list[int], reciter: dict) -> Optional[bytes]:
    pages_ayahs = await asyncio.gather(*(get_page_ayahs(p) for p in pages))
    all_ayahs = []
    for page_ayahs in pages_ayahs:
        all_ayahs.extend(page_ayahs)

    seen = set()
    unique_ayahs = []
    for surah_num, ayah_num in all_ayahs:
        if (surah_num, ayah_num) not in seen:
            seen.add((surah_num, ayah_num))
            unique_ayahs.append((surah_num, ayah_num))

    if not unique_ayahs:
        return None

    reciter_key = reciter["key"]
    reciter_audio_url = reciter["audio_url"]
    semaphore = asyncio.Semaphore(AUDIO_DOWNLOAD_CONCURRENCY)

    async def fetch_ayah(surah_num: int, ayah_num: int) -> Optional[bytes]:
        key = (reciter_key, surah_num, ayah_num)
        if key in AUDIO_CACHE:
            return AUDIO_CACHE[key]

        disk_path = AUDIO_FILES_DIR / reciter_key / f"{surah_num:03d}{ayah_num:03d}.mp3"
        if disk_path.exists():
            try:
                data = disk_path.read_bytes()
                AUDIO_CACHE[key] = data
                return data
            except Exception:
                pass

        async with semaphore:
            url = f"{reciter_audio_url}/{surah_num:03d}{ayah_num:03d}.mp3"
            data = await download_bytes_with_retry(url)
            if data:
                AUDIO_CACHE[key] = data
                try:
                    disk_path.parent.mkdir(parents=True, exist_ok=True)
                    disk_path.write_bytes(data)
                except Exception:
                    pass
            return data

    results = await asyncio.gather(*(fetch_ayah(s, a) for s, a in unique_ayahs))
    audio_chunks = [chunk for chunk in results if chunk]
    return b"".join(audio_chunks) if audio_chunks else None

async def deliver_audio_result(answer_target, surah: dict, combined_audio: Optional[bytes], title_suffix: str, reciter: dict, waiting_msg: Optional[Message] = None):
    if not combined_audio:
        if waiting_msg:
            try: await waiting_msg.delete()
            except Exception: pass
        await answer_target.answer("⚠️ تعذر تجميع المقطع الصوتي.")
        return

    try:
        audio_file = BufferedInputFile(combined_audio, filename=f"{surah['name']}_{title_suffix}.mp3")
        caption_text = f"القارئ : <b>{reciter['name']}</b> {EMOJI_RECITER_HTML}"
        await answer_target.answer_audio(audio=audio_file, caption=caption_text, parse_mode=ParseMode.HTML)
    except Exception:
        logger.exception("فشل إرسال ملف الصوت")
    finally:
        if waiting_msg:
            try: await waiting_msg.delete()
            except Exception: pass

def build_home_menu(user_id: Optional[int]) -> InlineKeyboardMarkup:
    theme = USER_THEME.get(user_id, "light")
    theme_btn_text = "🌙 الوضع الليلي" if theme == "light" else "☀️ الوضع النهاري"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="القرآن الكريم 📖", callback_data="open_quran_section"),
                InlineKeyboardButton(text="أختر القارئ 🎙", callback_data="open_reciter_section"),
            ],
            [
                InlineKeyboardButton(text="📿 الأذكار والتسبيح", callback_data="open_azkar_section"),
                InlineKeyboardButton(text="🕌 مواقيت الصلاة والقبلة", callback_data="open_prayer_section"),
            ],
            [
                InlineKeyboardButton(text=theme_btn_text, callback_data="toggle_theme"),
                InlineKeyboardButton(text="لوحة الأدمن 🛡️", callback_data="security_panel"),
            ],
            [
                InlineKeyboardButton(text="آقتراحات لـ تطوير البوت", url=f"https://t.me/{DEVELOPER_USERNAME}")
            ],
        ]
    )

def build_azkar_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="☀️ أذكار الصباح", callback_data="azkar:sabah:0")],
            [InlineKeyboardButton(text="🌙 أذكار المساء", callback_data="azkar:mosa:0")],
            [InlineKeyboardButton(text="😴 أذكار النوم", callback_data="azkar:sleep:0")],
            [InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_home")],
        ]
    )

def build_azkar_item_menu(type_key: str, index: int, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔢 باقي {count} مرة (اضغط للتكرار)", callback_data=f"azkar_click:{type_key}:{index}:{count}")],
            [InlineKeyboardButton(text="الذكر التالي ➡️", callback_data=f"azkar:{type_key}:{index + 1}")],
            [InlineKeyboardButton(text="رجوع للأذكار 📿", callback_data="open_azkar_section")]
        ]
    )

def build_reciter_menu(user_id: Optional[int]) -> InlineKeyboardMarkup:
    selected_key = USER_RECITER.get(user_id, DEFAULT_RECITER_KEY)
    rows = []
    for reciter in RECITERS:
        is_selected = reciter["key"] == selected_key
        rows.append([
            InlineKeyboardButton(
                text=f"{'✅ ' if is_selected else ''}{reciter['name']}",
                callback_data=f"select_reciter:{reciter['key']}"
            )
        ])
    rows.append([InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_surah_list_menu(page: int = 0) -> InlineKeyboardMarkup:
    start_idx = page * SURAHS_PER_PAGE
    end_idx = start_idx + SURAHS_PER_PAGE
    current_surahs = SURAHS[start_idx:end_idx]

    rows = []
    row = []
    for idx, surah in enumerate(current_surahs):
        btn = InlineKeyboardButton(text=f"سورة {surah['name']}", callback_data=f"surah:{surah['key']}")
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row: rows.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="السابق ◀️", callback_data=f"surah_page:{page - 1}"))
    if end_idx < len(SURAHS):
        nav_row.append(InlineKeyboardButton(text="التالي ▶️", callback_data=f"surah_page:{page + 1}"))
    if nav_row: rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_surah_mode_menu(surah_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="أختيار صفحة واحدة 📄", callback_data=f"grid:{surah_key}:0")],
            [InlineKeyboardButton(text="أختيار أكثر من صفحة 📚", callback_data=f"range:{surah_key}")],
            [InlineKeyboardButton(text="رجوع 🔙", callback_data="surah_page:0")],
        ]
    )

def build_page_grid(surah_key: str, offset: int) -> InlineKeyboardMarkup:
    surah = SURAHS_DICT[surah_key]
    all_pages = list(range(surah["start_page"], surah["end_page"] + 1))
    screen_pages = all_pages[offset : offset + PAGES_PER_GRID_SCREEN]

    rows = []
    row = []
    for page in screen_pages:
        row.append(InlineKeyboardButton(text=str(page), callback_data=f"pg:{surah_key}:{page}"))
        if len(row) == GRID_COLUMNS:
            rows.append(row)
            row = []
    if row: rows.append(row)

    nav_row = []
    if offset > 0:
        prev_offset = max(0, offset - PAGES_PER_GRID_SCREEN)
        nav_row.append(InlineKeyboardButton(text="السابق ◀️", callback_data=f"grid:{surah_key}:{prev_offset}"))
    if offset + PAGES_PER_GRID_SCREEN < len(all_pages):
        next_offset = offset + PAGES_PER_GRID_SCREEN
        nav_row.append(InlineKeyboardButton(text="التالي ▶️", callback_data=f"grid:{surah_key}:{next_offset}"))
    if nav_row: rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="رجوع 🔙", callback_data=f"surah:{surah_key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_security_panel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"👥 كل المشاركين ({len(BOT_USERS)})", callback_data="sec_all:0")],
            [InlineKeyboardButton(text="القائمة الرئيسية 🏠", callback_data="back_to_home")],
        ]
    )

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        get_home_text(message.from_user.id),
        reply_markup=build_home_menu(message.from_user.id),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "back_to_home")
async def on_back_to_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(
            get_home_text(callback.from_user.id),
            reply_markup=build_home_menu(callback.from_user.id),
            parse_mode=ParseMode.HTML
        )
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "toggle_theme")
async def on_toggle_theme(callback: CallbackQuery):
    current = USER_THEME.get(callback.from_user.id, "light")
    USER_THEME[callback.from_user.id] = "dark" if current == "light" else "light"
    await callback.answer("تم تغيير ثيم الواجهة!")
    try:
        await callback.message.edit_text(
            get_home_text(callback.from_user.id),
            reply_markup=build_home_menu(callback.from_user.id),
            parse_mode=ParseMode.HTML
        )
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "open_azkar_section")
async def on_open_azkar(callback: CallbackQuery):
    await callback.answer()
    text = "<b>قسم الأذكار والتسبيح اليومي</b> 📿\n\nأختر الأذكار المطلوبة:"
    await callback.message.edit_text(text, reply_markup=build_azkar_menu(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("azkar:"))
async def on_show_azkar_item(callback: CallbackQuery):
    _, type_key, index_str = callback.data.split(":")
    index = int(index_str)
    items = AZKAR_DATA.get(type_key, [])

    if index >= len(items):
        await callback.answer("✨ أتممت هذه الأذكار بنجاح، تقبل الله!", show_alert=True)
        await callback.message.edit_text("<b>قسم الأذكار والتسبيح اليومي</b> 📿", reply_markup=build_azkar_menu(), parse_mode=ParseMode.HTML)
        return

    await callback.answer()
    item = items[index]
    text = f"<b>الذكر ({index + 1}/{len(items)}):</b>\n\n« {item['text']} »"
    await callback.message.edit_text(text, reply_markup=build_azkar_item_menu(type_key, index, item["count"]), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("azkar_click:"))
async def on_azkar_click(callback: CallbackQuery):
    _, type_key, index_str, count_str = callback.data.split(":")
    index, count = int(index_str), int(count_str) - 1

    if count <= 0:
        await callback.answer("أحسنت! انتقل للذكر التالي.")
        items = AZKAR_DATA.get(type_key, [])
        next_index = index + 1
        if next_index >= len(items):
            await callback.message.edit_text("✨ أتممت هذه الأذكار بنجاح، تقبل الله!", reply_markup=build_azkar_menu(), parse_mode=ParseMode.HTML)
        else:
            item = items[next_index]
            text = f"<b>الذكر ({next_index + 1}/{len(items)}):</b>\n\n« {item['text']} »"
            await callback.message.edit_text(text, reply_markup=build_azkar_item_menu(type_key, next_index, item["count"]), parse_mode=ParseMode.HTML)
    else:
        await callback.answer(f"متبقي {count} مرة")
        items = AZKAR_DATA.get(type_key, [])
        item = items[index]
        text = f"<b>الذكر ({index + 1}/{len(items)}):</b>\n\n« {item['text']} »"
        await callback.message.edit_text(text, reply_markup=build_azkar_item_menu(type_key, index, count), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "open_prayer_section")
async def on_open_prayer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(QuranStates.waiting_for_city)
    text = "<b>🕌 مواقيت الصلاة والقبلة</b>\n\nأرسل اسم مدينتك الآن بالإنجليزية (مثال: <code>Baghdad</code> أو <code>Cairo</code>):"
    await callback.message.answer(text, parse_mode=ParseMode.HTML)

@router.message(QuranStates.waiting_for_city, F.text)
async def handle_city_input(message: Message, state: FSMContext):
    city = message.text.strip()
    await state.clear()
    
    url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=&method=4"
    data = await download_bytes(url)
    if not data:
        await message.answer("⚠️ تعذر جلب مواقيت الصلاة لهذه المدينة. تأكد من كتابة الاسم بالإنجليزية.")
        return

    try:
        json_data = json.loads(data.decode("utf-8"))
        timings = json_data["data"]["timings"]
        text = (
            f"<b>🕌 مواقيت الصلاة لمدينة ({city.capitalize()}):</b>\n\n"
            f"• الفجر: <code>{timings['Fajr']}</code>\n"
            f"• الشروق: <code>{timings['Sunrise']}</code>\n"
            f"• الظهر: <code>{timings['Dhuhr']}</code>\n"
            f"• العصر: <code>{timings['Asr']}</code>\n"
            f"• المغرب: <code>{timings['Maghrib']}</code>\n"
            f"• العشاء: <code>{timings['Isha']}</code>\n"
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception:
        await message.answer("⚠️ حدث خطأ أثناء معالجة البيانات.")

@router.callback_query(F.data == "open_quran_section")
async def on_open_quran_section(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text(QURAN_HEADER_TEXT, reply_markup=build_surah_list_menu(0), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data == "open_reciter_section")
async def on_open_reciter_section(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text(RECITER_HEADER_TEXT, reply_markup=build_reciter_menu(callback.from_user.id), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data.startswith("select_reciter:"))
async def on_select_reciter(callback: CallbackQuery):
    reciter_key = callback.data.split(":", 1)[1]
    reciter = RECITERS_DICT.get(reciter_key)
    if not reciter:
        await callback.answer()
        return

    USER_RECITER[callback.from_user.id] = reciter_key
    await callback.answer(f"تم اختيار القارئ: {reciter['name']}")
    try:
        await callback.message.edit_text(RECITER_HEADER_TEXT, reply_markup=build_reciter_menu(callback.from_user.id), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data.startswith("surah_page:"))
async def on_surah_page_change(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.answer()
    try:
        await callback.message.edit_text(QURAN_HEADER_TEXT, reply_markup=build_surah_list_menu(page), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data.startswith("surah:"))
async def on_surah_selected(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    surah = SURAHS_DICT.get(key)
    if not surah:
        return
    await callback.answer()
    await state.clear()

    text = f"أخترت سورة <b>{surah['name']}</b> {EMOJI_SURAH_CHOSEN}\nأختر الطريقة المناسبة <b>للعرض</b> {EMOJI_SELECT_MODE}"
    try:
        await callback.message.edit_text(text, reply_markup=build_surah_mode_menu(key), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data.startswith("grid:"))
async def on_grid_requested(callback: CallbackQuery):
    _, surah_key, offset_str = callback.data.split(":")
    offset = int(offset_str)
    surah = SURAHS_DICT.get(surah_key)
    if not surah:
        return
    await callback.answer()

    text = f"<b>{surah['name']}</b> - أختر صفحة {EMOJI_GRID_TITLE}"
    try:
        await callback.message.edit_text(text, reply_markup=build_page_grid(surah_key, offset), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

@router.callback_query(F.data.startswith("pg:"))
async def on_single_page_selected(callback: CallbackQuery):
    _, surah_key, page_str = callback.data.split(":")
    page = int(page_str)
    surah = SURAHS_DICT.get(surah_key)
    reciter = get_user_reciter(callback.from_user.id)

    audio_task = asyncio.create_task(build_pages_audio([page], reciter))
    caption_text = f"<b>صفحة {page}</b> {EMOJI_CAPTION_HTML}"

    img_waiting_msg = await callback.message.answer(f"<b>جارِ</b> تحميل <b>صورة الصفحة</b> {EMOJI_WAITING_HTML}", parse_mode=ParseMode.HTML)

    if page in PAGE_CACHE:
        await callback.message.answer_photo(photo=PAGE_CACHE[page], caption=caption_text, parse_mode=ParseMode.HTML)
    else:
        jpg = await fetch_page_jpg(page)
        if jpg:
            photo = BufferedInputFile(jpg, filename=f"page_{page}.jpg")
            sent = await callback.message.answer_photo(photo=photo, caption=caption_text, parse_mode=ParseMode.HTML)
            if sent.photo:
                PAGE_CACHE[page] = sent.photo[-1].file_id
                save_page_file_id_cache()

    try: await img_waiting_msg.delete()
    except Exception: pass

    audio_waiting_msg = await callback.message.answer(f"<b>جارِ</b> تجهيز <b>المقطع الصوتي</b> {EMOJI_WAITING_HTML}", parse_mode=ParseMode.HTML)
    combined_audio = await audio_task
    await deliver_audio_result(callback.message, surah, combined_audio, f"صفحة_{page}", reciter, waiting_msg=audio_waiting_msg)

@router.callback_query(F.data.startswith("range:"))
async def on_range_requested(callback: CallbackQuery, state: FSMContext):
    surah_key = callback.data.split(":", 1)[1]
    surah = SURAHS_DICT.get(surah_key)
    if not surah:
        return
    await callback.answer()
    await state.update_data(surah_key=surah_key)
    await state.set_state(QuranStates.waiting_for_range)

    prompt_text = (
        f"<b>أختر</b> عدد من الصفحات من ( <b>{surah['start_page']}</b> - <b>{surah['end_page']}</b> ) {EMOJI_RANGE_TITLE}\n\n"
        f"{EMOJI_ALERT} <b>تنبيه</b> الحد المسموح <b><u>20</u></b> صفحة وأقل.\n"
        f"{EMOJI_ALERT} <b>أرسل</b> <u>النطاق المطلوب</u> هكذا (مثال: <code>5-8</code>):"
    )
    await callback.message.answer(prompt_text, parse_mode=ParseMode.HTML)

@router.message(QuranStates.waiting_for_range, F.text)
async def handle_page_range(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    match = re.match(r"^(\d{1,3})\s*-\s*(\d{1,3})$", text)
    if not match:
        await message.answer("⚠️ صيغة غير صحيحة. أرسل النطاق هكذا: <code>5-8</code>")
        return

    start_page, end_page = int(match.group(1)), int(match.group(2))
    data = await state.get_data()
    surah = SURAHS_DICT.get(data.get("surah_key"))

    if not surah or start_page > end_page or start_page < surah["start_page"] or end_page > surah["end_page"]:
        await message.answer("⚠️ النطاق مدخل بشكل غير صحيح أو خارج صفحات السورة.")
        return

    if (end_page - start_page + 1) > MAX_RANGE_PAGES:
        await message.answer(f"{EMOJI_ALERT} عذراً، لا يمكن اختيار أكثر من 20 صفحة في المرة الواحدة.")
        return

    pages = list(range(start_page, end_page + 1))
    reciter = get_user_reciter(message.from_user.id)
    audio_task = asyncio.create_task(build_pages_audio(pages, reciter))

    img_waiting_msg = await message.answer(f"<b>جارِ</b> تحميل <b>صور الصفحات</b> {EMOJI_WAITING_HTML}", parse_mode=ParseMode.HTML)
    media_data = await fetch_pages_as_media_group(pages)
    newly_cached = False

    for chunk in chunk_list(media_data, MEDIA_GROUP_CHUNK_SIZE):
        chunk_pages = [item[0] for item in chunk]
        chunk_media = [item[1] for item in chunk]
        sent_messages = await message.answer_media_group(media=chunk_media)
        for p_num, msg in zip(chunk_pages, sent_messages):
            if p_num not in PAGE_CACHE and msg.photo:
                PAGE_CACHE[p_num] = msg.photo[-1].file_id
                newly_cached = True

    if newly_cached: save_page_file_id_cache()

    try: await img_waiting_msg.delete()
    except Exception: pass

    audio_waiting_msg = await message.answer(f"<b>جارِ</b> تجهيز <b>المقطع الصوتي</b> {EMOJI_WAITING_HTML}", parse_mode=ParseMode.HTML)
    combined_audio = await audio_task
    await deliver_audio_result(message, surah, combined_audio, f"صفحات_{start_page}-{end_page}", reciter, waiting_msg=audio_waiting_msg)
    await state.clear()

@router.callback_query(F.data == "security_panel")
async def on_security_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("⚠️ هذه اللوحة مخصصة لمالك البوت فقط.", show_alert=True)
        return
    await callback.answer()
    text = (
        f"<b>لوحة الأدمن</b> {EMOJI_SECURITY_PANEL}\n\n"
        f"إجمالي من تعامل مع البوت: <b>{len(BOT_USERS)}</b>\n"
        "أختر أحد الخيارات:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=build_security_panel_menu(), parse_mode=ParseMode.HTML)
    except TelegramAPIError:
        pass

def get_user_reciter(user_id: Optional[int]) -> dict:
    reciter_key = USER_RECITER.get(user_id, DEFAULT_RECITER_KEY)
    return RECITERS_DICT.get(reciter_key, RECITERS[0])

async def main():
    await start_dummy_server()
    global http_session
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(UserTrackingMiddleware())
    dp.include_router(router)

    http_session = aiohttp.ClientSession()
    logger.info("🚀 تم تشغيل البوت بنجاح مع كافة السور الـ 114...")
    try:
        await dp.start_polling(bot)
    finally:
        if http_session:
            await http_session.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
