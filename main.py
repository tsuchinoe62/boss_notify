import os
import datetime
from discord import Intents, Client, Embed
from discord.ext import tasks
from dotenv import load_dotenv
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pytz
from table2ascii import table2ascii

load_dotenv(verbose=True)
CHANNEL_IDS = list(map(int, os.environ.get("CHANNEL_IDS").split(",")))
TOKEN = os.environ.get("TOKEN")

def get_upcoming_bosses() -> pd.DataFrame:
    auth = "./credentials.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = auth

    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(auth, scope)
    oauth2_client = gspread.authorize(credentials)

    sheet = oauth2_client.open_by_key("1osMHLFRGKJBNyCp8E3YcRNJFqCZycksXJ9XPyXNWW8Q")
    raw_data = sheet.worksheet("シート1")
    df = pd.DataFrame(raw_data.get_all_values())

    return df.iloc[2:, 1:4]

def display_upcoming_bosses(df: pd.DataFrame) -> Embed:
    upcoming_bosses = table2ascii(
        header=["場所", "名前", "時刻"],
        body = df.values.tolist(),
        footer=[
            "最終更新:",
            datetime.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M'),
            "",
        ]
    )

    embed = Embed(title="フィールドボス出現予定一覧", description=upcoming_bosses)

    return embed

class MyClient(Client):
    def __init__(self) -> None:
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.messages = {}

    async def init_bosses_list(self) -> None:
        df = get_upcoming_bosses()
        embed = display_upcoming_bosses(df)

        for channel_id in CHANNEL_IDS:
            channel = self.get_channel(channel_id)
            self.messages[channel_id] = await channel.send(embed=embed)

    @tasks.loop(seconds=60)
    async def update_bosses_list(self) -> None:
        df = get_upcoming_bosses()
        embed = display_upcoming_bosses(df)

        for channel_id in CHANNEL_IDS:
            try:
                await self.messages[channel_id].edit(embed=embed)
            except Exception as e:
                print(e)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")

        await self.init_bosses_list()
        self.update_bosses_list.start()

client = MyClient()
client.run(TOKEN)
