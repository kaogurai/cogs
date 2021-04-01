from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate
import discord
import aiohttp 
import lavalink
import time
import re
import asyncio
import hashlib
import xmltodict

class Scrobbler(commands.Cog):
    """Scrobbles music from VC to your https://last.fm account."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=5959595935467387654783)
        default_user = {
            "failed_scrobbles": 0,
            "username": None,
            "session_key": None
        }
        self.config.register_global(**default_user)

    async def red_delete_data_for_user(self, *, requester, user_id):
        await self.config.user_from_id(user_id).clear()

    @commands.command()
    async def fmlogin(self, ctx):
        """Authenticates your https://last.fm account to scrobble music in VC."""
        fm_tokens = await self.bot.get_shared_api_tokens("lastfm")
        lastfm_api_key = fm_tokens.get("appid")
        lastfm_api_secret = fm_tokens.get("secret")
        base_url = "https://ws.audioscrobbler.com/2.0/"
        try:
            if ctx.guild:
                await ctx.tick()
            await ctx.author.send(f"**Hello!**\n\nI assume you already have made a Last.FM account, but if you haven't, please make one at <https://last.fm> now.\n\nOnce you've done that, please go to this url:\n<https://www.last.fm/api/auth/?api_key={lastfm_api_key}&cb=https://trustyjaid.com/spotify>\n\nAfter you have authenticated, there will be a url that appears on screen.\n\nFor me to know you've done that, you'll need to copy that url that appeared on screen send it to me!\n\nI'll wait for two minutes for that url, but if you need longer, you can run the command again.")
            try:
                msg = await self.bot.wait_for("message", check=MessagePredicate.same_context(channel=ctx.author.dm_channel), timeout=120)
                if msg.content.startswith('https://trustyjaid.com/spotify/?token='):
                    token = msg.content.replace('https://trustyjaid.com/spotify/?token=', '')
                    params = {
                        'api_key': lastfm_api_key,
                        'method': 'auth.getSession',
                        'token': token
                    }
                    hashed = hashRequest(params, lastfm_api_secret)
                    params['api_sig'] = hashed
                    async with aiohttp.ClientSession() as session:
                        async with session.get(base_url, params=params) as request:
                            if request.status == 200:
                                response = await request.text()
                                dict = xmltodict.parse(response, process_namespaces=True)
                                username = dict['lfm']['session']['name']
                                session_key = dict['lfm']['session']['key']
                                await self.config.user(ctx.author).username.set(username)
                                await self.config.user(ctx.author).session_key.set(session_key)
                                await ctx.author.send(f"**Thanks!**\n\nYou've been successfully authenticated as `{username}` and I will now scrobble for you.\n\nIf you want me to stop scrobbling, use the `{ctx.clean_prefix}fmlogout` command!")
                            else:
                                await ctx.author.send("An error has occured. Please try again later!")
                    await session.close()
                else:
                    await ctx.author.send("That doesn't look like the correct link, can you do the command and reread the message again?")
            except asyncio.TimeoutError:
                await ctx.author.send("**You took too long!** Use the command again if you still want to try.")
        except discord.Forbidden:
                await ctx.send("I can't DM you.")

    @commands.command()
    async def fmlogout(self, ctx):
        """Deauthenticates your https://last.fm account to scrobble music in VC."""
        await self.config.user(ctx.author).clear()
        await ctx.tick()

    async def scrobble_song(self, track, artist, duration, user, requester):
        fm_tokens = await self.bot.get_shared_api_tokens("lastfm")
        api_key = fm_tokens.get('appid')
        api_secret = fm_tokens.get('secret')
        base_url = "https://ws.audioscrobbler.com/2.0/"
        timestamp = time.time()
        sk = await self.config.user(user).session_key()
        if user == requester:
            chosen = 1
        else:
            chosen = 0
        params = {
            'api_key': api_key,
            'artist': artist,
            'chosenByUser': chosen,
            'duration': str(duration/1000),
            'method': 'track.scrobble',
            'sk': sk,
            'timestamp': str(timestamp),
            'track': track
        }
        hashed = hashRequest(params, api_secret)
        params['api_sig'] = hashed
        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, params=params) as request:
                response = await request.text()
                dict = xmltodict.parse(response, process_namespaces=True)
                # do something to handle it not working LMFAO
                lol = self.bot.get_channel(800600678841319444)
                await lol.send(dict)

        await session.close()

    async def set_nowplaying(self, track, artist, duration, user, requester):
        fm_tokens = await self.bot.get_shared_api_tokens("lastfm")
        api_key = fm_tokens.get('appid')
        api_secret = fm_tokens.get('secret')
        base_url = "https://ws.audioscrobbler.com/2.0/"
        timestamp = time.time()
        sk = await self.config.user(user).session_key()
        params = {
            'api_key': api_key,
            'artist': artist,
            'duration': str(duration/1000),
            'method': 'track.updateNowPlaying',
            'sk': sk,
            'timestamp': str(timestamp),
            'track': track
        }
        hashed = hashRequest(params, api_secret)
        params['api_sig'] = hashed
        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, params=params) as request:
                response = await request.text()
                dict = xmltodict.parse(response, process_namespaces=True)
                # do something to handle it not working LMFAO
        await session.close()

    @commands.Cog.listener()
    async def on_red_audio_track_start(self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member):
        if not (guild and track):
            return
        if track.length <= 30000:
            return
        regex = re.compile((r"((\[)|(\()).*(of?ficial|feat\.?|"
                          r"ft\.?|audio|video|lyrics?|remix|HD).*(?(2)]|\))"), flags=re.I)
        # thanks wyn - https://github.com/TheWyn/Wyn-RedV3Cogs/blob/master/lyrics/lyrics.py#L12-13
        renamed_track = regex.sub('', track.title).strip()
        track_array = renamed_track.split('-', 2)
        if len(track_array) != 2:
            return
        track_artist = track_array[0]
        track_title = track_array[1]
        voice_members = guild.me.voice.channel.members
        for member in voice_members:
            if member == guild.me:
                continue
            elif member.bot is True:
                continue
            else:
                if await self.config.user(member).session_key():
                    await self.scrobble_song(track_title, track_artist, track.length, member, requester)
                    await self.set_nowplaying(track_title, track_artist, track.length, member, requester)

def hashRequest(obj, secretKey): # https://github.com/huberf/lastfm-scrobbler/blob/master/lastpy/__init__.py#L50
    string = ''
    items = obj.keys()
    sorted(items)
    for i in items:
        string += i
        string += obj[i]
    string += secretKey
    stringToHash = string.encode('utf8')
    requestHash = hashlib.md5(stringToHash).hexdigest()
    return requestHash