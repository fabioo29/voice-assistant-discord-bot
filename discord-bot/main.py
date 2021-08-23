import os
import re
import json
import time
import discord
import youtube_dl

import yfinance as yf
import speech_recognition as sr

from currency_converter import CurrencyConverter
from translate import Translator

from pydub import AudioSegment
from pydub.silence import split_on_silence
from youtubesearchpython import VideosSearch
from discord.ext.commands import AutoShardedBot
from discord.utils import get
from discord.ext import tasks

from youtubesearchpython import VideosSearch
from argparse import ArgumentParser
from decouple import config
from assist import Assistant
from gtts import gTTS

from constants import * 
from keep_alive import keep_alive


def combined_sounds(path1:str, path2:str):
    """combine two wav files into one var"""
    sound1 = AudioSegment.from_wav(path1)
    sound2 = AudioSegment.from_wav(path2)

    return sound1 + sound2

def remove_accents(raw_text:str) -> str :
    """Strip accents from input string"""
    raw_text = re.sub(u"[àáâãäå]", 'a', raw_text)
    raw_text = re.sub(u"[èéêë]", 'e', raw_text)
    raw_text = re.sub(u"[ìíîï]", 'i', raw_text)
    raw_text = re.sub(u"[òóôõö]", 'o', raw_text)
    raw_text = re.sub(u"[ùúûü]", 'u', raw_text)
    raw_text = re.sub(u"[ýÿ]", 'y', raw_text)
    raw_text = re.sub(u"[ß]", 'ss', raw_text)
    raw_text = re.sub(u"[ñ]", 'n', raw_text)
    return raw_text 

def speech_to_tex(path:str):
    """"
    convert audio from .wav file to text using
     google speech recognition API.
    """
    sound = AudioSegment.from_wav(path)  
    chunks = split_on_silence(sound,
        min_silence_len = 500,
        silence_thresh = sound.dBFS-14,
        keep_silence=500,
    )
    folder_name = "audio-chunks"
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)

    # whole_text = ""
    whole_text = []
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        
        with sr.AudioFile(chunk_filename) as source:
            try:
                audio_listened = r.record(source)
                try:
                    text = r.recognize_google(audio_listened, language = 'en-US', show_all=True)
                    if text['alternative'][0]['confidence'] < 0.7:
                        text['alternative'][0]['transcript'] = "*inaudible*"
                    text = text['alternative'][0]['transcript']
                except sr.UnknownValueError as e:
                    text = "*inaudible*"
                else:                
                    # whole_text += text
                    whole_text.append(text)
            except:
                whole_text.append('')
                continue

    return whole_text

def deEmojify(text:str) -> str:
    """Remove special chars and emojis from string"""
    regrex_pattern = re.compile(pattern = "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags = re.UNICODE)
    return regrex_pattern.sub(r'',text)

class AssistantDiscordBot(AutoShardedBot):
    """Responds to Discord User Queries"""

    def __init__(
            self,
            device_model_id=None,
            device_id=None,
            credentials=None,
            token=None):
        super(AssistantDiscordBot, self).__init__(
            command_prefix=INVOCATION_PREFIXES,
            fetch_offline_members=False,
            case_insensitive=True,
            help_command=None
        )
        self.assistant = Assistant(
            device_model_id=device_model_id,
            device_id=device_id,
            credentials=credentials,
            token=token
        )
        self.waiting = False
        self.timer = 0
        self.youtubePlaying = False
        self.ytQueue = {}
        self.ytvidTimer = 0
        self.MusicStatus = False


if __name__ == '__main__':
    
    parser = ArgumentParser()
    parser.add_argument('-sp','--speechdetection', action="store_true", 
        help='show speech detection print in console')
    parser.add_argument('-cd','--channeldialog', action="store_true", 
        help='hide dialog User/BOT in channel chat')
    parser.add_argument('-rt','--responsetime', default="5", required=False, 
        help='time for user to ask something to BOT in voice channel')
    
    parser = parser.parse_args()

    device_model_id = config("DEVICE_MODEL_ID")
    device_id = config("DEVICE_ID")
    assistant_token = config("ASSISTANT_TOKEN")
    credentials = config("CREDENTIALS")

    discord_token = config("DISCORD_TOKEN")

    credentials = json.loads(credentials)
    credentials.pop('token', None)

    client = AssistantDiscordBot(
        device_model_id=device_model_id,
        device_id=device_id,
        credentials=credentials,
        token=assistant_token,
    )

    r = sr.Recognizer()
    c = CurrencyConverter()
    
    @tasks.loop(seconds = 1)
    async def check_voice(ctx):
        """
        Check if Bot detected user voice and give user 
         x more seconds to talk and then cancels it to 
         run the callback function "voiceReceiver_callback"
        """

        vc = get(ctx.bot.voice_clients, guild=ctx.guild)
        if [f for f in os.listdir() if f.endswith('.pcm')] and not client.waiting:
            client.waiting = True
            client.timer = time.time()

        if client.waiting and (time.time()-client.timer >= int(parser.responsetime)):
            vc.stop_recording()
            client.waiting = False        
        elif not client.waiting and not vc.recording: 
            vc.start_recording(discord.Sink(encoding='wav', filters={'time': 0}), voiceReceiver_callback, ctx)

    async def playAfterGoogle(ctx):
        ''' Resume music after Google speaks '''
        voice = get(ctx.bot.voice_clients, guild=ctx.guild)
        while voice.is_playing():
            pass
                
        await play(ctx, client.ytQueue[ctx.guild.id][0], client.ytvidTimer)

    async def voiceReceiver_callback(sink, channel, *args):
        """auto-execute after Discord.Sink(record_voice) gets cancelled"""
        
        user_texts = []
        wavFiles = [f for f in os.listdir() if f.endswith('.wav')]

        if not len(wavFiles): return
        
        for file in wavFiles:
            currText = speech_to_tex(file)
            user_texts.append(currText[0])

        [os.remove(f) for f in wavFiles]

        if parser.speechdetection: print(user_texts)

        newUser_texts = []
        for text in user_texts:
            if list(filter(text.lower().startswith, INVOCATION_PREFIXES)) != []:
                newText = text.lower().replace(list(filter(text.lower().startswith, INVOCATION_PREFIXES))[0], '')
                if newText != '': newUser_texts.append(newText)

        if not len(newUser_texts): return

        for text in newUser_texts:
            assistant_response = deEmojify(client.assistant.text_assist(remove_accents(text)))

            if not parser.channeldialog:
                await channel.send(f'```\nUser:{text}\n\nAssistant: {assistant_response}\n```')
                
            gTTS(text=assistant_response, lang='en', slow=False).save('botPlay.mp3')
            
            client.ytvidTimer = time.time() - client.ytvidTimer
            
            try:
                voice = get(channel.bot.voice_clients, guild=channel.guild)
                voice.pause()

                voice.play(discord.FFmpegPCMAudio('botPlay.mp3', options = "-loglevel panic"))
                voice.source.volume = 0.8
                
                await playAfterGoogle(channel)
            except:
                pass

    @client.event
    async def on_ready():
        """Bot-ready message"""
        [os.remove(f) for f in os.listdir() if f.endswith(('.wav', '.pcm'))]
        print(client.user.name, 'ready!')

    @client.command(pass_context=True)
    async def help(ctx):
        """-help to show helpfull Bot commands"""
        await ctx.send(HELP_MESSAGE)
        return
        
    @client.command(pass_context=True)
    async def join(ctx):
        """Bot to join voice room on "join" command"""        
        if ctx.author.voice:
            channel = ctx.message.author.voice.channel
            await channel.connect()
            check_voice.start(ctx)
            try: client.ytQueue[ctx.guild.id];
            except: client.ytQueue[ctx.guild.id] = [];
        else:
            await ctx.send("You're not in a voice room.")
        return
    
    @client.command(pass_context=True)
    async def leave(ctx):
        """Bot to leave voice room on "leave" command"""
        if ctx.voice_client:
            await ctx.guild.voice_client.disconnect()
            check_voice.stop()
            check_music.stop()
            try: del client.ytQueue[ctx.guild.id];
            except: pass;
        else:
            await ctx.send("I'm not in a voice room.")
        return

    @tasks.loop(seconds = 2)
    async def check_music(ctx):
        """Play music in the queue if current music stops"""
        voice = get(client.voice_clients, guild=ctx.guild)

        if not client.ytQueue[ctx.guild.id] or not client.MusicStatus:
            return 

        if not voice.is_playing():
            if client.youtubePlaying:  
                del client.ytQueue[ctx.guild.id][0]
                if (client.ytQueue[ctx.guild.id]): 
                    await play(ctx, client.ytQueue[ctx.guild.id][0])

    @client.command(aliases=['p'], pass_context=True)
    async def play(ctx, url: str, timestamp: int = 0):
        """Bot to play youtube url on "play {url}" command"""
        voice = get(client.voice_clients, guild=ctx.guild)
        
        if voice.is_playing():
            if not url in client.ytQueue[ctx.guild.id]: 
                client.ytQueue[ctx.guild.id].append(url)
                with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(url, download=False)     
                    await ctx.send(info.get('title', None)[:30] + " added to the queue.")
            return

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            if not url in client.ytQueue[ctx.guild.id]: client.ytQueue[ctx.guild.id].append(url)
            client.ytvidTimer = time.time() - timestamp
            client.youtubePlaying = True

            info = ydl.extract_info(url, download=False)
            I_URL = info['formats'][0]['url']
            FFMPEG_OPTIONS['options'] = '-vn -ss ' + str(timestamp)
            source = await discord.FFmpegOpusAudio.from_probe(I_URL, **FFMPEG_OPTIONS)
            voice.play(source)
            voice.source.volume = 0.8

            await ctx.send(info.get('title', None)[:22] + " is now playing.")

        if not check_music.is_running():
            check_music.start(ctx)

    @client.command(pass_context=True)
    async def pause(ctx):
        """pause current music"""
        client.MusicStatus = False
        voice = get(client.voice_clients, guild=ctx.guild)
        client.ytvidTimer = time.time() - client.ytvidTimer
        voice.pause()
        check_music.stop()
    
    @client.command(pass_context=True)
    async def unpause(ctx):
        """unpause current music"""
        client.MusicStatus = True
        await play(ctx, client.ytQueue[ctx.guild.id][0], client.ytvidTimer)

    @client.command(pass_context=True)
    async def skip(ctx):
        """skip current music"""
        voice = get(client.voice_clients, guild=ctx.guild)
        voice.pause()
        if len(client.ytQueue[ctx.guild.id]) >= 1:
            del client.ytQueue[ctx.guild.id][0]
        if (client.ytQueue[ctx.guild.id]):
            await play(ctx, client.ytQueue[ctx.guild.id][0])
    
    @client.command(aliases=['queue', 'q'], pass_context=True)
    async def playlist(ctx):
        """list all queued music"""
        voice = get(client.voice_clients, guild=ctx.guild)
        if (client.ytQueue[ctx.guild.id]):
            outStr = "Music Playlist```"
            with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                for i, url in enumerate(client.ytQueue[ctx.guild.id]):
                    info = ydl.extract_info(url, download=False)
                    outStr += f'\n{i+1}. ' + info.get('title', None)[:35]
                    if not i and voice.is_playing(): outStr += " [Playing]"
            await ctx.send(outStr + "```")
        else: await ctx.send("The music queue is empty.")     

    @client.command(pass_context=True)
    async def quote(ctx, ticker: str):
        """quote {AAPL, TSLA} to get company stock price"""
        try:
            await ctx.send(str(yf.Ticker(ticker).info['currentPrice'])+'$')
            return
        except:
            await ctx.send("I can't get any data from this stock ticker.")
            return
    
    @client.command(pass_context=True)
    async def convert(ctx, value: float, orig: str, dest: str):
        """convert {value} {USD} {EUR} to convert currencies"""
        if orig.upper() in CURRENCIES and \
            dest.upper() in CURRENCIES:
            await ctx.send('{:.2f} {}'.format(c.convert(value,orig,dest), dest.upper()))
            return
        else:
            await ctx.send(f'''\nAvailable currencies\n```\n{CURRENCIES}\n```''')
            return

    @client.event
    async def on_message(message):
        """Google assistant on messages starting with {INVOCATION_PREFIXES}"""
        
        if message.author.bot:
            return
        
        lower_content = message.content.lower()

        # If message don't start with {INVOCATION_PREFIXES} then ignore it
        if list(filter(lower_content.startswith, INVOCATION_PREFIXES)) == []:
            return

        lower_content = lower_content.replace(list(filter(lower_content.startswith, INVOCATION_PREFIXES))[0], '')

        # If it is a known command without the prefix, BOT execute it
        if list(filter(lower_content.startswith, list(client.all_commands.keys()))) != []:
            if lower_content.startswith('play'):
                if not 'www' in lower_content.split()[1:] and not 'http' in lower_content.split()[1:]:
                    ctx = await client.get_context(message)
                    await play(ctx, VideosSearch(' '.join(lower_content.split()[1:]), limit = 1).resultComponents[0]['link'])
                    return
            await client.process_commands(message)
            return

        # -translate {text} {en} {pt} to translate text
        if 'translate' in lower_content.split()[0][1:]:
            origLan, destLan = lower_content.split()[-2], lower_content.split()[-1]
            if origLan in list(LANGUAGES.values())+list(LANGUAGES.keys()) and \
                destLan in list(LANGUAGES.values())+list(LANGUAGES.keys()):
                if not destLan in list(LANGUAGES.keys()):
                    destLan = list(LANGUAGES.keys())[list(LANGUAGES.values()).index(destLan)]
                if not origLan in list(LANGUAGES.keys()):
                    origLan = list(LANGUAGES.keys())[list(LANGUAGES.values()).index(origLan)]
                await message.channel.send(
                    Translator(
                        from_lang=origLan, 
                        to_lang=destLan
                    ).translate(lower_content[10:].replace(
                        lower_content[lower_content.index(lower_content.split()[-2]):],''))
                )
                return
            else:
                await message.channel.send(f'''\nAvailable languages\n```\n{list(LANGUAGES.values())}\n```''')
                return

        assistant_response = client.assistant.text_assist(lower_content[1:])

        if assistant_response:
            await message.channel.send(assistant_response)
    
    keep_alive()
    client.run(discord_token)