import ssl, certifi, asyncio, discord, yt_dlp, os, json, random, io, time, aiohttp
from discord.ui import Button, View

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
intents.voice_states = True  # <--- تأكد من وجود هذا السطر وتفعيله
intents.guilds = True

client = discord.Client(intents=intents)
TARGET_ROOM_ID = 1510342490723451023

AUTHORIZED_USERS = {
    967675648522989578: "وليد",
    851952174590066728: "أحمد",
    1434636048817721424: "عبادي",
    1558412634653462632: "waleed"
}




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
queue = []
last_played_song = None
autoplay_mode = False
current_volume = 1.0  
active_control_message = None  

class MusicControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="btn_prev_3")
    async def prev_song(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏮️ يمكنك استخدام أمر `-عيد` لإعادة الأغنية السابقة.", ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="btn_pause_resume_3")
    async def pause_resume(self, interaction: discord.Interaction, button: Button):
        vc = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if not vc:
            await interaction.response.send_message("❌ البوت غير متصل بالصوت!", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
            try: await interaction.message.edit(view=self)
            except: pass
            await interaction.response.send_message("⏸️ **تم إيقاف الموسيقى مؤقتاً.**", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.primary
            try: await interaction.message.edit(view=self)
            except: pass
            await interaction.response.send_message("▶️ **تم استئناف الموسيقى!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا يوجد شيء قيد التشغيل حالياً.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="btn_skip_3")
    async def skip_song(self, interaction: discord.Interaction, button: Button):
        vc = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ **تم تخطي الأغنية!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لا توجد أغنية لتخطيها.", ephemeral=True)

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary, custom_id="btn_replay_3")
    async def replay_song(self, interaction: discord.Interaction, button: Button):
        global last_played_song
        vc = discord.utils.get(client.voice_clients, guild=interaction.guild)
        if not vc or not last_played_song:
            await interaction.response.send_message("⚠️ لا توجد أغنية سابقة لإعادتها!", ephemeral=True)
            return
        queue.insert(0, last_played_song)
        vc.stop()
        await interaction.response.send_message(f"🔄 **تمت إعادة تشغيل:** `{last_played_song['title']}`", ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="btn_vol_down_3")
    async def volume_down(self, interaction: discord.Interaction, button: Button):
        global current_volume
        current_volume = max(0.1, round(current_volume - 0.25, 2))
        vc = interaction.guild.voice_client
        if vc and vc.is_playing() and hasattr(vc.source, 'volume'):
            vc.source.volume = current_volume
        await interaction.response.send_message(f"🔉 **تم خفض الصوت.** ({int(current_volume*100)}%)", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="btn_vol_up_3")
    async def volume_up(self, interaction: discord.Interaction, button: Button):
        global current_volume
        current_volume = min(2.0, round(current_volume + 0.25, 2))
        vc = interaction.guild.voice_client
        if vc and vc.is_playing() and hasattr(vc.source, 'volume'):
            vc.source.volume = current_volume
        await interaction.response.send_message(f"🔊 **تم رفع الصوت.** ({int(current_volume*100)}%)", ephemeral=True)

    @discord.ui.button(emoji="♾️", style=discord.ButtonStyle.danger, custom_id="btn_autoplay_3")
    async def toggle_autoplay(self, interaction: discord.Interaction, button: Button):
        global autoplay_mode
        autoplay_mode = not autoplay_mode
        if autoplay_mode:
            button.style = discord.ButtonStyle.success
            await interaction.response.send_message("♾️ **تم تفعيل التشغيل التلقائي (Autoplay: On)**", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.danger
            await interaction.response.send_message("♾️ **تم إيقاف التشغيل التلقائي (Autoplay: Off)**", ephemeral=True)
        try: await interaction.message.edit(view=self)
        except: pass

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="btn_stop_3")
    async def stop_bot(self, interaction: discord.Interaction, button: Button):
        global active_control_message
        vc = discord.utils.get(client.voice_clients, guild=interaction.guild)
        queue.clear()
        if vc:
            vc.stop()
            await vc.disconnect()
        if active_control_message:
            try: await active_control_message.delete()
            except: pass
            active_control_message = None
        await interaction.response.send_message("⏹️ **تم إيقاف البوت ومسح قائمة الانتظار.**", ephemeral=True)

async def send_or_update_control_message(channel, embed):
    global active_control_message
    try:
        if active_control_message:
            try: await active_control_message.delete()
            except: pass
        active_control_message = await channel.send(embed=embed, view=MusicControlView())
    except Exception as e:
        print(f"⚠️ خطأ في تحديث رسالة التحكم: {e}")


def play_next(client_instance, channel):
    global last_played_song, autoplay_mode
    if len(queue) > 0:
        song = queue.pop(0)
        last_played_song = song
        vc = discord.utils.get(client_instance.voice_clients, guild=channel.guild)
        if vc and vc.is_connected():
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS),
                volume=current_volume
            )
            vc.play(audio_source, after=lambda e: play_next(client_instance, channel))
            embed = discord.Embed(
                title="🎶 جاري التشغيل الآن",
                description=f"🎵 **العنوان:** `{song['title']}`",
                color=discord.Color.blurple()
            )
            asyncio.run_coroutine_threadsafe(send_or_update_control_message(channel, embed), client_instance.loop)
    elif autoplay_mode and last_played_song:
        asyncio.run_coroutine_threadsafe(fetch_and_play_autoplay(client_instance, channel, last_played_song['title']), client_instance.loop)
    else:
        last_played_song = None

async def fetch_and_play_autoplay(client_instance, channel, previous_title):
    global last_played_song
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch1:{previous_title} mix", download=False))
        if 'entries' in data: data = data['entries'][0]
        stream_url = data['url']
        title = data.get('title', 'مقطع مقترح')
        song_data = {'url': stream_url, 'title': title}
        last_played_song = song_data
        
        vc = discord.utils.get(client_instance.voice_clients, guild=channel.guild)
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
    except:
        pass

@client.event
async def on_ready():
    print(f'✅ [متصل] البوت الثالث متصل باسم: {client.user}')
    
    ch = client.get_channel(TARGET_ROOM_ID)
    if ch:
        vc = discord.utils.get(client.voice_clients, guild=ch.guild)
        if not vc:
            await ch.connect(reconnect=True, self_deaf=True)
            print("🔒 تم تثبيت البوت الثالث في الروم للأبد.")

@client.event
async def on_message(message):
    global queue, last_played_song, current_volume
    if message.author == client.user: return

    if message.content.startswith('-ش '):
        query = message.content[3:].strip()
        if not message.author.voice or message.author.voice.channel.id != TARGET_ROOM_ID: return
        vc = discord.utils.get(client.voice_clients, guild=message.guild)
        if not vc: vc = await message.author.voice.channel.connect(reconnect=True, self_deaf=True)
        
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            search_query = query if query.startswith('http') else f"ytsearch1:{query}"
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))
            if 'entries' in data: data = data['entries'][0]
            
            stream_url = data['url']
            title = data.get('title', 'مقطع صوتي')
            song_data = {'url': stream_url, 'title': title}

            if vc.is_playing() or vc.is_paused():
                queue.append(song_data)
                await message.channel.send(f"➕ **أضيفت للانتظار:** `{title}`")
            else:
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
        if message.author.voice and message.author.voice.channel.id == TARGET_ROOM_ID:
            vc = discord.utils.get(client.voice_clients, guild=message.guild)
            if vc and vc.is_playing(): vc.pause(); await message.channel.send('⏸️ **تم الإيقاف مؤقتاً.**')

    elif message.content == '-كمل':
        if message.author.voice and message.author.voice.channel.id == TARGET_ROOM_ID:
            vc = discord.utils.get(client.voice_clients, guild=message.guild)
            if vc and vc.is_paused(): vc.resume(); await message.channel.send('▶️ **تم الاستئناف!**')

    elif message.content in ['-سكب', '-تخطي']:
        if message.author.voice and message.author.voice.channel.id == TARGET_ROOM_ID:
            vc = discord.utils.get(client.voice_clients, guild=message.guild)
            if vc and (vc.is_playing() or vc.is_paused()): vc.stop(); await message.channel.send('⏭️ **تم التخطي!**')

    elif message.content == '-عيد':
        if message.author.voice and message.author.voice.channel.id == TARGET_ROOM_ID:
            vc = discord.utils.get(client.voice_clients, guild=message.guild)
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

@client.event
async def on_message(message):
    # تجاهل رسائل البوت نفسه لكي لا يدخل في حلقة لا نهائية
    if message.author.bot:
        return

    # طباعة كل رسالة تصل للبوت في التيرمنال لنتأكد أنه يقرأ الدردشة
    print(f"--> Received message: {message.content} from {message.author}")

    if message.content == '-ادخل3':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        
        if message.author.voice and message.author.voice.channel:
            channel = message.author.voice.channel
            try:
                if message.guild.voice_client:
                    await message.guild.voice_client.move_to(channel)
                else:
                    await channel.connect()
                await message.channel.send(f'🔊 **سم طال عمرك 🫡** `{channel.name}`')
            except Exception as e:
                await message.channel.send(f'❌ حدث خطأ أثناء محاولة الاتصال: {e}')
        else:
            await message.channel.send('⚠️ يجب أن تكون متصلاً بروم صوتي ليتمكن البوت من دخوله!')



    elif message.content == '-ريستارت3':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        await message.channel.send('🔄 **جاري إعادة تشغيل البوت الثالث...**')
        await client.close()
        return


@client.event
async def on_ready():
    print(f'--> Logged in as {client.user}')
    try:
        channel = client.get_channel(1536716345620824144)
        if channel:
            await channel.send("✅ **تم إعادة تشغيل البوت بنجاح!**")
            print(f'--> Success: Sent message to channel {channel.name}')
        else:
            print(f'--> Warning: Channel ID 1536716345620824144 not found or no access!')
    except Exception as e:
        print(f'--> Error sending message: {e}')


client.run(os.getenv('BOT3_TOKEN'))