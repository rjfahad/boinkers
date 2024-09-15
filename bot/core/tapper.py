import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import time
from urllib.parse import unquote, quote
import brotli

import aiohttp
import json
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types
from .agents import generate_random_user_agent
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from .helper import format_duration


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.fullname = None
        self.start_param = None
        self.peer = None
        self.first_run = None

        self.session_ug_dict = self.load_user_agents() or []

        headers['User-Agent'] = self.check_user_agent()

    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def info(self, message):
        from bot.utils import info
        info(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def debug(self, message):
        from bot.utils import debug
        debug(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def warning(self, message):
        from bot.utils import warning
        warning(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def error(self, message):
        from bot.utils import error
        error(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def critical(self, message):
        from bot.utils import critical
        critical(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def success(self, message):
        from bot.utils import success
        success(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            logger.success(f"<light-yellow>{self.session_name}</light-yellow> | User agent saved successfully")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            self.start_param = random.choices([settings.REF_ID, "boink355876562"], weights=[75, 25], k=1)[0]
            peer = await self.tg_client.resolve_peer('boinker_bot')
            InputBotApp = types.InputBotAppShortName(bot_id=peer, short_name="boinkapp")

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotApp,
                platform='android',
                write_allowed=True,
                start_param='boink355876562'
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            try:
                if self.user_id == 0:
                    information = await self.tg_client.get_me()
                    self.user_id = information.id
                    self.first_name = information.first_name or ''
                    self.last_name = information.last_name or ''
                    self.username = information.username or ''
            except Exception as e:
                print(e)

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(
                f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, initdata):
        try:
            json_data = { "initDataString": initdata }
            resp = await http_client.post(
                "https://boink.astronomica.io/public/users/loginByTelegram?p=android",
                json=json_data,
                ssl=False
            )
            if resp.status == 520:
                self.warning('Relogin')
                await asyncio.sleep(delay=5)

            resp_json = await resp.json()

            login_need = False

            return resp_json.get("token"), resp_json.get("token")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Login error {error}")
            return None, None

    async def upgrade_boinker(self, http_client: aiohttp.ClientSession):
         try:
             resp = await http_client.post(f"https://boink.astronomica.io/api/boinkers/upgradeBoinker?p=android",
                                           ssl=False)
             data = await resp.json()

             if resp.status == 200 and data:
                 logger.info(f"<light-yellow>{self.session_name}</light-yellow> Upgrade Boinker | Coin: <light-yellow>{'{:,}'.format(data['newSoftCurrencyAmount'])}</light-yellow> | Spin: <light-blue>{data['newSlotMachineEnergy']}</light-blue> | Rank: <magenta>{data['rank']}</magenta>")
                 return True
             else:
                 logger.info(f"<light-yellow>{self.session_name}</light-yellow> Upgrade Boinker | Not enough coins | Status: <magenta>{resp.status}</magenta>")
                 return False

             return False1
         except Exception as e:
             self.error(f"Error occurred during upgrade boinker: {e}")
             return False

    async def claim_booster(self, http_client: aiohttp.ClientSession, spin: int):
        json_data = {
            'multiplier': 2,
            'optionNumber': 1
        }

        if spin > 30:
            json_data = {
                'multiplier': 2,
                'optionNumber': 3
            }

        try:
            resp = await http_client.post(
                f"https://boink.astronomica.io/api/boinkers/addShitBooster?p=android",
                json=json_data,
                ssl=False
            )

            data = await resp.json()

            if resp.status == 200:
                return True
            else:
                return False

            return True
        except Exception as e:
            self.error(f"Error occurred during claim booster: {e}")
            return False

    async def spin_wheel_fortune(self, http_client: aiohttp.ClientSession):
        try:
            resp = await http_client.post(
                f"https://boink.astronomica.io/api/play/spinWheelOfFortune?p=android",
                ssl=False
            )

            data = await resp.json()

            if resp.status == 200:
                logger.info(f"<light-yellow>{self.session_name}</light-yellow> Wheel of Fortune | Prize: <magenta>{data['prize']['prizeName']}</magenta> - <light-green>{data['prize']['prizeValue']}</light-green>")
                return True
            else:
                return False

            return True
        except Exception as e:
            self.error(f"Error occurred during spin wheel of fortune: {e}")
            return False

    async def spin_slot_machine(self, http_client: aiohttp.ClientSession, spins: int):
        spin_amounts = [150, 50, 25, 10, 5, 1]
        remaining_spins = spins

        try:
            while remaining_spins > 0:
                spin_amount = next((amount for amount in spin_amounts if amount <= remaining_spins), 1)

                resp = await http_client.post(
                    f"https://boink.astronomica.io/api/play/spinSlotMachine/${spin_amount}?p=android",
                    ssl=False
                )

                if resp.status == 200:
                    data = await resp.json()
                    logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Spin prize: <light-blue>{data['prize']['prizeTypeName']}</light-blue> - <light-green>{data['prize']['prizeValue']}</light-green>")
                    remaining_spins -= spin_amount
                else:
                    await asyncio.sleep(delay=2)
                    return False

            return True
        except Exception as e:
            self.error(f"Error occurred during spin slot machine: {e}")
            return False

    async def get_user_info(self, http_client: aiohttp.ClientSession):
        try:
            resp = await http_client.get(
                 f"https://boink.astronomica.io/api/users/me?p=android",
                 ssl=False
            )
            json = await resp.json()
            return json
        except Exception as e:
            self.error(f"Error occurred during getting user info: {e}")
            return None
    async def perform_rewarded_actions(self, http_client: aiohttp.ClientSession):
        get_rewarded_action_list_url = "https://boink.astronomica.io/api/rewardedActions/getRewardedActionList?p=android"

        skipped_tasks = [
            'twitterQuotePost20',
            'telegramShareStory5',
            'emojiOnPostTelegramNewsChannel',
            'NotGoldReward',
            'NotPlatinumReward',
            'connectTonWallet',
            'telegramJoinBoinkersNewsChannel',
            'telegramJoinAcidGames',
            'inviteAFriend'
        ]

        try:
            # Fetch user info
            user_info = await self.get_user_info(http_client=http_client)

            async with http_client.get(get_rewarded_action_list_url, ssl=False) as response:
                if response.status != 200:
                    return
                rewarded_actions = await response.json()

            # Process each action
            if rewarded_actions is None:
                return False

            for action in rewarded_actions:
                name_id = action['nameId']


                if name_id in skipped_tasks:
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Skipping task: {name_id}")
                    continue

                current_time = datetime.now(timezone.utc)
                can_perform_task = True
                wait_time = None

                if user_info.get('rewardedActions', {}).get(name_id):
                    last_claim_time = current_time
                    if 'claimDateTime' in user_info['rewardedActions'][name_id]:
                        last_claim_time = parser.isoparse(user_info['rewardedActions'][name_id]['claimDateTime'])

                    if name_id == 'SeveralHourlsReward':
                        next_available_time = last_claim_time + timedelta(hours=6)
                        if current_time < next_available_time:
                            can_perform_task = False
                            wait_time = next_available_time
                    elif name_id in ['SeveralHourlsRewardedAdTask', 'SeveralHourlsRewardedAdTask2']:
                        next_available_time = last_claim_time + timedelta(minutes=6)
                        if current_time < next_available_time:
                            can_perform_task = False
                            wait_time = next_available_time
                    else:
                        can_perform_task = False

                if not can_perform_task:
                    if wait_time:
                        wait_minutes = (wait_time - current_time).seconds
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Need to wait {wait_minutes} seconds to perform task {name_id}")
                    continue

                if name_id in ['SeveralHourlsRewardedAdTask', 'SeveralHourlsRewardedAdTask2']:
                    provider_id = 'adsgram' if name_id == 'SeveralHourlsRewardedAdTask' else 'onclicka'
                    await self.handle_ad_task(http_client=http_client, name_id=name_id, provider_id=provider_id)  # Assuming you have a function to handle this
                else:
                    click_url = f"https://boink.astronomica.io/api/rewardedActions/rewardedActionClicked/{name_id}?p=android"
                    try:
                        async with http_client.post(click_url, ssl=False) as click_response:
                            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Performed task {name_id}. Status: pending")

                    except Exception as click_error:
                        logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Error performing task {name_id}: {click_error}")
                        continue

                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Waiting 2 seconds before claiming reward...")

                    await asyncio.sleep(10)

                    claim_url = f"https://boink.astronomica.io/api/rewardedActions/claimRewardedAction/{name_id}?p=android"
                    try:
                        async with http_client.post(claim_url, ssl=False) as claim_response:
                            if claim_response.status == 200:
                                result = await claim_response.json()
                                reward = result['prizeGotten']
                                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Successfully completed task {name_id} | Reward: <light-green>{reward}</light-green>")
                            else:
                                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Failed to claim reward for {name_id}. Status code: <light-red>{claim_response.status}</light-red>")
                    except Exception as claim_error:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Error claiming reward for {name_id}: {claim_error}")


                await asyncio.sleep(1)

        except Exception as error:
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Error performing tasks: {error}")

    async def handle_ad_task(self, http_client: aiohttp.ClientSession, name_id, provider_id):
        try:
            # Click the ad task
            click_url = f"https://boink.astronomica.io/api/rewardedActions/rewardedActionClicked/{name_id}?p=android"
            await http_client.post(click_url, ssl=False)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Ad task {name_id} clicked successfully")

            await asyncio.sleep(15)

            # Confirm ad watched
            ad_watched_url = "https://boink.astronomica.io/api/rewardedActions/ad-watched?p=android"
            await http_client.post(ad_watched_url, json={"providerId": provider_id}, ssl=False)
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Ad watched for {name_id} confirmed")

            await asyncio.sleep(20)

            # Claim the reward
            claim_url = f"https://boink.astronomica.io/api/rewardedActions/claimRewardedAction/{name_id}?p=android"
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sending reward claim request for ad task {name_id}...")
            async with http_client.post(claim_url, headers=headers) as claim_response:
                if claim_response.status == 200:
                    result = await claim_response.json()
                    reward = result.get('prizeGotten')
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Successfully completed ad task {name_id} | Reward: {reward}")
                else:
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Failed to claim reward for ad task {name_id}. Status code: {claim_response.status}")

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Error handling ad task {name_id}: {error}")

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:
        access_token = None
        refresh_token = None
        login_need = True
        spin_wheel_fortune = True

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        while True:
            try:
                if login_need:
                    if "Authorization" in http_client.headers:
                        del http_client.headers["Authorization"]

                    init_data = await self.get_tg_web_data(proxy=proxy)

                    access_token, refresh_token = await self.login(http_client=http_client, initdata=init_data)

                    http_client.headers["Authorization"] = f"{access_token}"

                    if self.first_run is not True:
                        self.success("Logged in successfully")
                        self.first_run = True

                    login_need = False

                await asyncio.sleep(delay=3)

            except Exception as error:
                logger.error(
                    f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during login: {error}")
                await asyncio.sleep(delay=3)

            try:
                user_info = await self.get_user_info(http_client=http_client)
                await asyncio.sleep(delay=2)
                if user_info is not None:
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Level: <light-blue>{'{:,}'.format(user_info['boinkers']['currentBoinkerProgression']['level'])}</light-blue>")
                    if 'currencySoft' in user_info:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Coin Balance: <light-green>{'{:,}'.format(user_info['currencySoft'])}</light-green>")

                    if 'currencyCrypto' in user_info:
                        logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Shit Balance: <cyan>{'{:,.3f}'.format(user_info['currencyCrypto'])}</cyan>")

                    current_time = datetime.now(timezone.utc)

                    last_claimed_time_str = user_info.get('boinkers', {}).get('booster', {}).get('x2', {}).get('lastTimeFreeOptionClaimed')
                    last_claimed_time = parser.isoparse(last_claimed_time_str) if last_claimed_time_str else None

                    # Check for booster claim
                    if not last_claimed_time or current_time > last_claimed_time + timedelta(hours=2, minutes=5):
                        success = await self.claim_booster(http_client=http_client, spin=user_info['gamesEnergy']['slotMachine']['energy'])
                        logger.success(f"<light-yellow>{self.session_name}</light-yellow> | Claimed boost successfully")
                        await asyncio.sleep(delay=4)
#                     else:
#                         next_booster_time = last_claimed_time + timedelta(hours=2, minutes=5)
#                         logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Next claim boost will be available at: {next_booster_time.strftime('%Y-%m-%d %H:%M:%S')}")

                    spin_user = await self.get_user_info(http_client=http_client)
                    spins = spin_user['gamesEnergy']['slotMachine']['energy']
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Spins: <light-blue>{spins}</light-blue>")
                    if spins > 0:
                        await self.spin_slot_machine(http_client=http_client, spins=spins)
                        await asyncio.sleep(delay=4)


                    if spin_wheel_fortune == True:
                        await self.spin_wheel_fortune(http_client=http_client)
                        spin_wheel_fortune = False

                    await self.perform_rewarded_actions(http_client=http_client)
                    await asyncio.sleep(delay=4)

                    upgrade_success = True
                    while upgrade_success:
                        upgrade_success = await self.upgrade_boinker(http_client=http_client)
                        await asyncio.sleep(delay=3)

                logger.info(f"<light-yellow>{self.session_name}</light-yellow> | sleep 600 seconds")
                await asyncio.sleep(delay=600)

            except Exception as error:
                logger.error(
                    f"<light-yellow>{self.session_name}</light-yellow> | Unknown error: {error}")

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")