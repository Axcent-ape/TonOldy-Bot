import random
import time
import datetime
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName
import asyncio
from urllib.parse import unquote, quote
from data import config
import aiohttp
from fake_useragent import UserAgent
from aiohttp_socks import ProxyConnector


class TonOldy:
    def __init__(self, thread: int, session_name: str, phone_number: str, proxy: [str, None]):
        self.account = session_name + '.session'
        self.thread = thread

        self.proxy = f"{config.PROXY['TYPE']['REQUESTS']}://{proxy}" if proxy is not None else None
        connector = ProxyConnector.from_url(self.proxy) if proxy else aiohttp.TCPConnector(verify_ssl=False)

        if proxy:
            proxy = {
                "scheme": config.PROXY['TYPE']['TG'],
                "hostname": proxy.split(":")[1].split("@")[1],
                "port": int(proxy.split(":")[2]),
                "username": proxy.split(":")[0],
                "password": proxy.split(":")[1].split("@")[0]
            }

        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=proxy,
            lang_code='ru'
        )

        headers = {
            'User-Agent': UserAgent(os='android', browsers='chrome').random,
        }
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=connector)

    async def stats(self):
        await self.login()

        challenge = await self.get_challenge()

        r = await (await self.session.get(f'https://backend.tonoldy.com/api/user')).json()
        balance = r.get('tokenAmount')

        r = await (await self.session.get(f'https://backend.tonoldy.com/api/referrals')).json()
        referrals = r.get('invited')

        r = await (await self.session.get(f'https://backend.tonoldy.com/api/leaderboard')).json()
        leaderboard = r.get('position')

        await self.logout()

        await self.client.connect()
        me = await self.client.get_me()
        phone_number, name = "'" + me.phone_number, f"{me.first_name} {me.last_name if me.last_name is not None else ''}"
        await self.client.disconnect()

        proxy = self.proxy.replace('http://', "") if self.proxy is not None else '-'

        return [phone_number, name, str(balance), str(leaderboard), str(referrals), proxy]

    async def submit_daily_hunts(self):
        resp_txt = await (await self.session.post('https://backend.tonoldy.com/api/challenge/daily_hunt')).text()
        return resp_txt == ''

    async def get_challenge(self):
        r = await (await self.session.get('https://backend.tonoldy.com/api/challenge')).json()
        return r

    async def register(self, query: str):
        resp = await self.session.post(f'https://backend.tonoldy.com/api/auth?queryString={query}')
        return (await resp.json()).get('status') == 'Success'

    async def logout(self):
        await self.session.close()

    async def login(self):
        attempts = 3
        while attempts:
            try:
                await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
                query = await self.get_tg_web_data()

                if query is None:
                    logger.error(f"Thread {self.thread} | {self.account} | Session {self.account} invalid")
                    await self.logout()
                    return None, None

                r = await (await self.session.get(f'https://backend.tonoldy.com/api/start?queryString={query}')).json()

                self.session.headers['Authorization'] = 'Bearer ' + r.get('jwtToken')

                if r.get('result') == 'NeedsRegistration':
                    if await self.register(query):
                        logger.success(f"Thread {self.thread} | {self.account} | Register")

                logger.success(f"Thread {self.thread} | {self.account} | Login")
                break
            except Exception as e:
                logger.error(f"Thread {self.thread} | {self.account} | Left login attempts: {attempts}, error: {e}")
                await asyncio.sleep(random.uniform(*config.DELAYS['RELOGIN']))
                attempts -= 1
        else:
            logger.error(f"Thread {self.thread} | {self.account} | Couldn't login")
            await self.logout()
            return
    async def get_tg_web_data(self):
        try:
            await self.client.connect()

            web_view = await self.client.invoke(RequestAppWebView(
                peer=await self.client.resolve_peer('TonOldy_bot'),
                app=InputBotAppShortName(bot_id=await self.client.resolve_peer('TonOldy_bot'), short_name="app"),
                platform='android',
                write_allowed=True,
                start_param='NjAwODIzOTE4Mg==' if random.random() <= 0.4 else config.REF_LINK.split('startapp=')[1]
            ))
            await self.client.disconnect()

            auth_url = web_view.url
            query = auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
            return query

        except:
            return None

    @staticmethod
    def get_sleep_time():
        now = datetime.datetime.utcnow()
        target_time = now.replace(hour=12, minute=0, second=0, microsecond=0)

        if now >= target_time:
            target_time += datetime.timedelta(days=1)

        seconds_until_noon = (target_time - now).total_seconds()
        return seconds_until_noon
