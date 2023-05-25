import asyncio, aiohttp
import requests
from src.config import IFTTT_TOKEN

def call_webhook_async(event, payload):
    # 如果没有配置IFTTT的webhook token则什么也不做
    if IFTTT_TOKEN == "":
        return
    webhook_url = f"https://maker.ifttt.com/trigger/{event}/json/with/key/{IFTTT_TOKEN}"

    print("hook: ", webhook_url)

    async def req():
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, data=payload) as response:
                print("pong: " + str(response.status))
    asyncio.create_task(req())


def call_webhook(event, payload):
    # 如果没有配置IFTTT的webhook token则什么也不做
    if IFTTT_TOKEN == "":
        return
    webhook_url = f"https://maker.ifttt.com/trigger/{event}/json/with/key/{IFTTT_TOKEN}"
    requests.post(webhook_url, json=payload)