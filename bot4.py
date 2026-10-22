import ssl, certifi, asyncio, discord, yt_dlp, os, json, random, io, time, aiohttp
from discord.ui import Button, View
current_volume = 1.0
# Keep normal TLS certificate verification enabled.

try:
    discord.opus.load_opus('/opt/homebrew/lib/libopus.dylib')
except:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

client = discord.Client(intents=intents)

DEFAULT_VOICE_CHANNEL_ID = 1517775963784744970

AUTHORIZED_USERS = {
    967675648522989578: "وليد",
    851952174590066728: "أحمد",
    1434636048817721424: "عبادي",
    1558412634653462632: "waleed"
}


queue = []
last_played_song = None
autoplay_mode = False
active_control_message = None
played_history = set()


YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'skip_download': True,
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -probesize 32768 -analyzeduration 0',
    'options': '-vn -loglevel quiet',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class MusicControlView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for child in self.children:
            if child.custom_id == "btn_autoplay_1":
                child.style = discord.ButtonStyle.success if autoplay_mode else discord.ButtonStyle.danger

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="btn_prev_1")
    async def prev_song(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏮️ استخدم أمر `-عيد` لإعادة الأغنية السابقة.", ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="btn_pause_resume_1")
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if not vc: return await interaction.response.send_message("❌ البوت غير متصل!", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
            try: await interaction.message.edit(view=self)
            except: pass
            await interaction.response.send_message("⏸️ **تم الإيقاف المؤقت.**", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.primary
            try: await interaction.message.edit(view=self)
            except: pass
            await interaction.response.send_message("▶️ **تم الاستئناف!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا يوجد شي قيد التشغيل.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="btn_skip_1")
    async def skip_song(self, interaction: discord.Interaction, button: Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ **تم التخطي بنجاح!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد أغنية لتخطيها.", ephemeral=True)

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary, custom_id="btn_replay_1")
    async def replay_song(self, interaction: discord.Interaction, button: Button):
        global last_played_song
        vc = interaction.guild.voice_client
        if not vc or not last_played_song: return await interaction.response.send_message("⚠️ لا توجد أغنية سابقة!", ephemeral=True)
        queue.insert(0, last_played_song)
        vc.stop()
        await interaction.response.send_message(f"🔄 **إعادة تشغيل:** `{last_played_song['title']}`", ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="btn_vol_down_1")
    async def volume_down(self, interaction: discord.Interaction, button: Button):
        global current_volume
        current_volume = max(0.1, round(current_volume - 0.25, 2))
        vc = interaction.guild.voice_client
        if vc and vc.is_playing() and hasattr(vc.source, 'volume'):
            vc.source.volume = current_volume
        await interaction.response.send_message(f"🔉 **تم خفض الصوت.** ({int(current_volume*100)}%)", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="btn_vol_up_1")
    async def volume_up(self, interaction: discord.Interaction, button: Button):
        global current_volume
        current_volume = min(2.0, round(current_volume + 0.25, 2))
        vc = interaction.guild.voice_client
        if vc and vc.is_playing() and hasattr(vc.source, 'volume'):
            vc.source.volume = current_volume
        await interaction.response.send_message(f"🔊 **تم رفع الصوت.** ({int(current_volume*100)}%)", ephemeral=True)

    @discord.ui.button(emoji="♾️", style=discord.ButtonStyle.danger, custom_id="btn_autoplay_1")
    async def toggle_autoplay(self, interaction: discord.Interaction, button: Button):
        global autoplay_mode
        autoplay_mode = not autoplay_mode
        if autoplay_mode:
            button.style = discord.ButtonStyle.success
            await interaction.response.send_message("♾️ **تم تفعيل التشغيل التلقائي (Autoplay: On)**", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.danger
            await interaction.response.send_message("♾️ **تم إيقاف التشغيل التلقائي (Autoplay: Off)**", ephemeral=True)
        try: await interaction.message.edit(view=MusicControlView())
        except: pass

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="btn_stop_1")
    async def stop_bot(self, interaction: discord.Interaction, button: Button):
        global active_control_message
        vc = interaction.guild.voice_client
        queue.clear()
        if vc: vc.stop(); await vc.disconnect()
        if active_control_message:
            try: await active_control_message.delete()
            except: pass
            active_control_message = None
        await interaction.response.send_message("⏹️ **تم إيقاف البوت ومسح القائمة.**", ephemeral=True)

async def send_or_update_control_message(channel, embed):
    global active_control_message
    try:
        if active_control_message:
            try: await active_control_message.delete()
            except: pass
            active_control_message = None
        active_control_message = await channel.send(embed=embed, view=MusicControlView())
    except Exception as e:
        print(f"⚠️ خطأ في إرسال رسالة التحكم: {e}")

def play_next(client_instance, channel):
    global last_played_song, autoplay_mode, current_volume
    if len(queue) > 0:
        song = queue.pop(0)
        last_played_song = song
        played_history.add(song['title'])
        vc = channel.guild.voice_client
        if vc and vc.is_connected():
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS),
                volume=current_volume
            )
            vc.play(audio_source, after=lambda e: play_next(client_instance, channel))
            embed = discord.Embed(
                title="🎵 جاري التشغيل حالياً",
                description=f"🎵 **العنوان:** `{song['title']}`",
                color=discord.Color.blue()
            )
            asyncio.run_coroutine_threadsafe(send_or_update_control_message(channel, embed), client_instance.loop)
    elif autoplay_mode and last_played_song:
        asyncio.run_coroutine_threadsafe(fetch_smart_autoplay(client_instance, channel, last_played_song['title']), client_instance.loop)
    else:
        last_played_song = None

async def fetch_smart_autoplay(client_instance, channel, previous_title):
    global last_played_song, current_volume
    try:
        clean_title = previous_title.replace("official", "").replace("video", "").replace("audio", "").strip()
        words = [w for w in clean_title.split() if len(w) > 2]
        base_keyword = words[0] if words else clean_title
        
        query = f"ytsearch20:{base_keyword} جلسات عود طرب مشابهة"
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        entries = data.get('entries', [])
        
        valid_entries = [e for e in entries if e and e.get('title', '') not in played_history and e.get('title', '') != previous_title]
        
        chosen = None
        if valid_entries:
            chosen = random.choice(valid_entries)
        elif entries:
            chosen = random.choice(entries)
            
        if chosen:
            stream_url = chosen['url']
            title = chosen.get('title', 'مقطع مقترح')
            song_data = {'url': stream_url, 'title': title}
            last_played_song = song_data
            played_history.add(title)
            vc = channel.guild.voice_client
            if vc and vc.is_connected():
                audio_source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS),
                    volume=current_volume
                )
                vc.play(audio_source, after=lambda e: play_next(client_instance, channel))
                embed = discord.Embed(
                    title="♾️ تشغيل تلقائي مستمر (Autoplay)",
                    description=f"🎵 **العنوان:** `{title}`",
                    color=discord.Color.green()
                )
                await send_or_update_control_message(channel, embed)
    except Exception as e:
        print(f"⚠️ خطأ في التشغيل التلقائي: {e}")


@client.event
async def on_ready():
    print(f'--> Logged in as {client.user}')
    
    ch = client.get_channel(DEFAULT_VOICE_CHANNEL_ID)
    if ch:
        vc = discord.utils.get(client.voice_clients, guild=ch.guild)
        if not vc:
            await ch.connect(reconnect=True, self_deaf=True)
            print("🔒 تم تثبيت البوت الرابع في الروم للأبد.")

    try:
        channel = client.get_channel(1536716345620824144)
        if channel:
            await channel.send("✅ **تم إعادة تشغيل البوت بنجاح!**")
            print(f'--> Success: Sent message to channel {channel.name}')
        else:
            print(f'--> Warning: Channel ID 1536716345620824144 not found or no access!')
    except Exception as e:
        print(f'--> Error sending message: {e}')

@client.event
async def on_message(message):
    global queue, last_played_song, current_volume
    if message.author == client.user:
        return

    vc = discord.utils.get(client.voice_clients, guild=message.guild)
    current_bot_channel = vc.channel if vc and vc.is_connected() else client.get_channel(DEFAULT_VOICE_CHANNEL_ID)

    if message.content in ['-تعال', '-ارجع']:
        if message.author.id not in AUTHORIZED_USERS:
            await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
            return

        if message.content == '-تعال':
            if message.author.voice and message.author.voice.channel:
                target_ch = message.author.voice.channel
                if vc and vc.is_connected():
                    await vc.move_to(target_ch)
                else:
                    vc = await target_ch.connect(reconnect=True, self_deaf=True)
                await message.channel.send('**حاضر سيدي 🫡**')
            else:
                await message.channel.send('⚠️ يرجى الدخول إلى روم صوتي أولاً لاستدعاء البوت!')

        elif message.content == '-ارجع':
            default_ch = client.get_channel(DEFAULT_VOICE_CHANNEL_ID)
            if default_ch:
                if vc and vc.is_connected():
                    await vc.move_to(default_ch)
                else:
                    vc = await default_ch.connect(reconnect=True, self_deaf=True)
                await message.channel.send('**سم طال عمرك 🫡**')
            else:
                await message.channel.send('⚠️ تعذر العثور على الروم الافتراضي المحدد.')
        return

    if not message.author.voice or not current_bot_channel or message.author.voice.channel.id != current_bot_channel.id:
        return

    if message.content.startswith('-ش '):
        query = message.content[3:].strip()
        
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            search_query = query if query.startswith('http') else f"ytsearch1:{query}"
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))
            if 'entries' in data: data = data['entries'][0]
            
            stream_url = data['url']
            title = data.get('title', 'مقطع صوتي')
            song_data = {'url': stream_url, 'title': title}

            if vc and (vc.is_playing() or vc.is_paused()):
                queue.append(song_data)
                await message.channel.send(f"➕ **أضيفت للانتظار:** `{title}`")
            else:
                if not vc: vc = await message.author.voice.channel.connect(reconnect=True, self_deaf=True)
                last_played_song = song_data
                audio_source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS),
                    volume=current_volume
                )
                vc.play(audio_source, after=lambda e: play_next(client, message.channel))
                embed = discord.Embed(
                    title="🎶 جاري التشغيل الآن",
                    description=f"🎵 **العنوان:** `{title}`\n👥 **المستدعي:** `{message.author.mention}`",
                    color=discord.Color.blurple()
                )
                await send_or_update_control_message(message.channel, embed)

    elif message.content == '-وقف':
        if vc and vc.is_playing(): 
            vc.pause()
            await message.channel.send('⏸️ **تم الإيقاف مؤقتاً.**')

    elif message.content == '-كمل':
        if vc and vc.is_paused(): 
            vc.resume()
            await message.channel.send('▶️ **تم الاستئناف!**')

    elif message.content in ['-سكب', '-تخطي']:
        if vc and (vc.is_playing() or vc.is_paused()): 
            vc.stop()
            await message.channel.send('⏭️ **تم التخطي!**')

    elif message.content == '-عيد':
        if not vc: return

        if not last_played_song:
            await message.channel.send("⚠️ لا توجد أغنية سابقة لإعادتها!")
            return

        if vc.is_playing() or vc.is_paused():
            queue.insert(0, last_played_song)
            vc.stop()
            await message.channel.send(f"🔄 **تمت إعادة تشغيل:** `{last_played_song['title']}`")
        else:
            song = last_played_song
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS),
                volume=current_volume
            )
            vc.play(audio_source, after=lambda e: play_next(client, message.channel))
            await message.channel.send(f"🔄 **إعادة تشغيل:** `{song['title']}`")

    elif message.content == '-ريستارت4':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        await message.channel.send('🔄 **جاري إعادة تشغيل البوت الرابع...**')
        await client.close()
        return

client.run(os.getenv('BOT4_TOKEN'))