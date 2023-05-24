import asyncio, aiohttp

def call_webhook(event, payload):
    webhook_url = f"https://maker.ifttt.com/trigger/{event}/json/with/key/dsJWkJ5szEedFwmDcLd8ne"

    print("hook: ", webhook_url)

    async def req():
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, data=payload) as response:
                print("pong: " + str(response.status))
    asyncio.create_task(req())