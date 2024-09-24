import random
from utils.ton_oldy import TonOldy
from data import config
from utils.core import logger
import datetime
import pandas as pd
from utils.core.telegram import Accounts
import asyncio
import os


async def start(thread: int, session_name: str, phone_number: str, proxy: [str, None]):
    oldy = TonOldy(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy)
    account = session_name + '.session'

    while True:
        await oldy.login()

        info = await oldy.get_challenge()
        if not info.get('dailyHuntIsCompleted'):
            if await oldy.submit_daily_hunts():
                info = await oldy.get_challenge()
                logger.success(f"Thread {thread} | {account} | Submitted daily hunt word «{info.get('dailyHuntWord')}» and got {info.get('dailyHuntCurrentReward')} STONE")

        await oldy.logout()

        sleep = oldy.get_sleep_time() + random.uniform(*config.DELAYS['ADDITION_SLEEP'])
        logger.info(f"Thread {thread} | {account} | Sleep {int(sleep)}")
        await asyncio.sleep(sleep)


async def stats():
    accounts = await Accounts().get_accounts()

    tasks = []
    for thread, account in enumerate(accounts):
        session_name, phone_number, proxy = account.values()
        tasks.append(asyncio.create_task(TonOldy(session_name=session_name, phone_number=phone_number, thread=thread, proxy=proxy).stats()))

    data = await asyncio.gather(*tasks)
    path = f"statistics/statistics_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
    columns = ['Phone number', 'Name', 'balance', 'leaderboard', 'referrals', 'Proxy (login:password@ip:port)']

    if not os.path.exists('statistics'): os.mkdir('statistics')
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(path, index=False, encoding='utf-8-sig')

    logger.success(f"Saved statistics to {path}")
