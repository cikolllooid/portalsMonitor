import time
import random
import logging
import requests
import threading
from utils.collections_ids import collections_ids
from services.solveprice import robust_price_estimate, to_amounts
from queue import Queue
import os
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

message_queue = Queue()

AUTH_TOKEN = os.getenv("AUTH_TOKEN")
PORTAL_COOKIE = os.getenv("PORTAL_COOKIE")

# ---------------- CONTROL ----------------
stop_event = threading.Event()

# ---------------- CONFIG ----------------
URL_SEARCH = "https://portal-market.com/api/nfts/search"
URL_ACTIONS = "https://portal-market.com/api/market/actions/"
TIMEOUT = 15
PRICE_DIFF_MIN = 1

HEADERS_COMMON = {
    "Host": "portal-market.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Accept": "application/json, text/plain, */*",
    "Authorization": AUTH_TOKEN,
    "Cookie": PORTAL_COOKIE
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ---------------- SESSIONS ----------------
session_search = requests.Session()
session_search.headers.update(HEADERS_COMMON | {"Referer": "https://portal-market.com/"})

session_actions = requests.Session()
session_actions.headers.update(HEADERS_COMMON | {"Referer": "https://portal-market.com/market-activity"})

price_cache = {}

# ---------------- FUNCTIONS ----------------
def get_price_cached(model_back, collection_id, model_value):
    key = (model_back, collection_id, model_value)
    if key in price_cache:
        return price_cache[key]

    params = {
        "offset": 0,
        "limit": 50,
        "filter_by_backdrops": model_back,
        "collection_ids": collection_id,
        "filter_by_models": model_value
    }

    try:
        r = session_actions.get(URL_ACTIONS, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            logging.warning(f"market/actions error {r.status_code}")
            return None


        data = r.json()
        if len(price_cache) > 1000:
            price_cache.clear()

        price_cache[key] = data
        time.sleep(random.uniform(0.6, 1.2))
        return data

    except requests.RequestException as e:
        logging.error(f"Ошибка запроса market/actions: {e}")
        return None


def get_user_floor_price(collection_id: str, model_value: str | None = None, limit: int = 10):
    params = {
        "offset": 0,
        "limit": limit,
        "collection_ids": collection_id,
        "sort_by": "price asc",
        "status": "listed",
        "exclude_bundled": "true",
        "premarket_status": "all"
    }

    if model_value:
        params["filter_by_models"] = model_value

    try:
        r = session_search.get(URL_SEARCH, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return None

        results = r.json().get("results", [])
        return float(results[0]["price"]) if results else None

    except requests.RequestException:
        return None

# ---------------- CORE ----------------
def process_collection(params: dict):
    try:
        r = session_search.get(URL_SEARCH, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return

        results = r.json().get("results", [])

        for item in results:
            if stop_event.is_set():
                return

            model_value = next((a["value"] for a in item.get("attributes", []) if a["type"] == "model"), None)
            model_back = next((a["value"] for a in item.get("attributes", []) if a["type"] == "backdrop"), None)
            if not model_value or not model_back:
                continue

            key = f"monitor:{item['id']}"

            if redis_client.get(key) is not None:
                continue

            redis_client.set(key, 1, ex=172800)

            price_data = get_price_cached(model_back, item["collection_id"], model_value)
            if not price_data:
                continue

            actions = price_data.get("actions", [])
            amounts = to_amounts(actions)
            if not amounts:
                continue

            price_est = robust_price_estimate(amounts, n_recent=5, method="iqr_trimmed")
            if price_est is None:
                continue

            price_diff = price_est - float(item["price"])
            if price_diff < PRICE_DIFF_MIN:
                continue

            user_floor = get_user_floor_price(item["collection_id"], model_value)
            link = f"https://t.me/portals_market_bot/market?startapp=gift_{item['id']}_s8e0v0"

            message_text = (
                f"🎁 <b>{item['name']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🖼 <b>Модель:</b> {model_value}\n"
                f"🌅 <b>Фон:</b> {model_back}\n\n"

                f"💸 <b>Финансы</b>\n"
                f"• Цена лота: <b>{item['price']}</b>\n"
                f"• В среднем продают по: {round(price_est, 1)}\n"
                f"• Последняя продажа: <b>{amounts[0] if amounts else 'нет данных'}</b>\n"
                f"• Минимум на рынке: <b>{user_floor}</b>\n\n"

                f"🔥 <b>Потенциальная прибыль:</b> "
                f"<b>+{round(price_diff, 2)}</b>"
            )

            logging.info(f"Найден профит: {item['name']} +{round(price_diff,2)}")
            message_queue.put({
                "text": message_text,
                "link": link
            })

    except requests.RequestException as e:
        logging.error(f"Ошибка обработки коллекции: {e}")


# ---------------- RUNNER ----------------
def start_scanner(all: bool = True, data: dict = None):
    logging.info("Сканер запущен")

    stop_event.clear()
    params = {
        "offset": 0,
        "limit": 50,
        "collection_ids": "5f6892b6-8fd6-4e90-b666-9ebfa5414ae5",
        "sort_by": "listed_at desc",
        "status": "listed",
        "premarket_status": "all",
        "exclude_bundled": "true"
    }
    if data:
        model = data.get("model")
        backdrop = data.get("backdrop")
        if model:
            params["filter_by_models"] = model
        elif backdrop:
            params["filter_by_backdrops"] = backdrop
        params["collection_ids"] = data["gift_id"]
    while not stop_event.is_set():
        if all and data == None:
            for collection_id in collections_ids.values():
                if stop_event.is_set():
                    break
                logging.info(f"Коллекция {collection_id}")
                params["collection_id"] = collection_id
                process_collection(params)
                time.sleep(0.2)
        elif not all and data == None:
            try:
                params.pop("collection_ids")
            except KeyError:
                print("Нету ключа")
            logging.info(f"Мониторим последние подарки")
            process_collection(params)
            time.sleep(0.2)
        else:
            process_collection(params)
            time.sleep(0.2)

    logging.info("Сканер остановлен")


def stop_scanner():
    stop_event.set()
