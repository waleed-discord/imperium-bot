import os, asyncio, logging, discord, yt_dlp
try:
 from dotenv import load_dotenv
 load_dotenv()

except ImportError:
    pass

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT2_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("ضع BOT2_TOKEN في ملف .env")

TARGET_ROOM_ID = 1510342490723451022
AUTHORIZED_USERS = {
    967675648522989578: "وليد",
    851952174590066728: "أحمد",
    1434636048817721424: "عبادي",
    1558412634653462632: "waleed"
}


YTDL_OPTIONS = {"format": "bestaudio/best", "quiet": True, "no_warnings": True, "default_search": "ytsearch1", "noplaylist": True}
FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
client = discord.Client(intents=intents)

# State belongs only to this bot process.
queues = {}
last_songs = {}
volumes = {}
control_messages = {}

def guild_state(store, guild_id, default):
    return store.setdefault(guild_id, default)

async def resolve_song(query):
    loop = asyncio.get_running_loop()
    search = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
    if not data:
        raise ValueError("ما لقيت نتيجة مناسبة.")
    if data.get("entries") is not None:
        entries = [e for e in data["entries"] if e]
        if not entries:
            raise ValueError("ما لقيت نتيجة مناسبة.")
        data = entries[0]
    if not data.get("url"):
        raise ValueError("تعذر استخراج رابط الصوت.")
    return {"url": data["url"], "title": data.get("title", "مقطع صوتي")}

async def update_controls(channel, title):
    guild_id = channel.guild.id
    old = control_messages.get(guild_id)
    if old:
        try: await old.delete()
        except discord.HTTPException: pass
    embed = discord.Embed(title="🎶 جاري التشغيل الآن", description=f"🎵 `{title}`", color=discord.Color.blurple())
    control_messages[guild_id] = await channel.send(embed=embed, view=MusicView())

async def start_song(guild, channel, song):
    guild_id = guild.id
    vc = guild.voice_client
    if not vc or not vc.is_connected():
        raise RuntimeError("البوت غير متصل بالروم الصوتي.")
    last_songs[guild_id] = song
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song["url"], **FFMPEG_OPTIONS), volume=volumes.get(guild_id, 1.0))
    def after(error):
        if error: logging.warning("Audio playback error: %s", error)
        fut = asyncio.run_coroutine_threadsafe(play_next(guild, channel), client.loop)
        try: fut.result(timeout=1)
        except Exception: pass
    vc.play(source, after=after)
    await update_controls(channel, song["title"])

async def play_next(guild, channel):
    guild_id = guild.id
    queue = queues.setdefault(guild_id, [])
    vc = guild.voice_client
    if not vc or not vc.is_connected(): return
    if queue:
        song = queue.pop(0)
        try: await start_song(guild, channel, song)
        except Exception as exc: logging.exception("Could not play queued track"); await channel.send(f"❌ تعذر تشغيل الأغنية التالية: {exc}")

class MusicView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="bot2_pause")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc: return await interaction.response.send_message("❌ البوت غير متصل!", ephemeral=True)
        if vc.is_playing(): vc.pause(); msg="⏸️ تم الإيقاف مؤقتاً."
        elif vc.is_paused(): vc.resume(); msg="▶️ تم الاستئناف."
        else: msg="لا توجد أغنية تعمل حالياً."
        await interaction.response.send_message(msg, ephemeral=True)
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="bot2_skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and (vc.is_playing() or vc.is_paused()): vc.stop(); msg="⏭️ تم التخطي."
        else: msg="لا توجد أغنية لتخطيها."
        await interaction.response.send_message(msg, ephemeral=True)
    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="bot2_voldown")
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid=interaction.guild_id; volumes[gid]=max(0.1, round(volumes.get(gid,1.0)-0.1,2))
        vc=interaction.guild.voice_client if interaction.guild else None
        if vc and vc.source and hasattr(vc.source,"volume"): vc.source.volume=volumes[gid]
        await interaction.response.send_message(f"🔉 الصوت {int(volumes[gid]*100)}%", ephemeral=True)
    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="bot2_volup")
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid=interaction.guild_id; volumes[gid]=min(2.0, round(volumes.get(gid,1.0)+0.1,2))
        vc=interaction.guild.voice_client if interaction.guild else None
        if vc and vc.source and hasattr(vc.source,"volume"): vc.source.volume=volumes[gid]
        await interaction.response.send_message(f"🔊 الصوت {int(volumes[gid]*100)}%", ephemeral=True)
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="bot2_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid=interaction.guild_id; queues[gid]=[]
        vc=interaction.guild.voice_client if interaction.guild else None
        if vc:
            if vc.is_playing() or vc.is_paused(): vc.stop()
            await vc.disconnect(force=True)
        await interaction.response.send_message("⏹️ تم الإيقاف ومسح الانتظار.", ephemeral=True)

@client.event
async def on_ready():
    logging.info("Bot 2 connected as %s", client.user)
    client.add_view(MusicView())
    channel=client.get_channel(TARGET_ROOM_ID)
    if channel and channel.guild.voice_client is None:
        try: await channel.connect(reconnect=True, self_deaf=True)
        except Exception: logging.exception("Voice connect failed")

@client.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    content=message.content.strip()
    if content == "-ريست2":
        if message.author.id in AUTHORIZED_USERS:
            await message.channel.send("🔄 سيتم إيقاف البوت؛ شغّله مجدداً من Terminal.")
            await client.close()
        return
    if content == "-ادخل2":
        if message.author.id not in AUTHORIZED_USERS: return
        channel=client.get_channel(TARGET_ROOM_ID)
        if channel:
            vc=message.guild.voice_client
            try:
                if vc and vc.is_connected(): await vc.move_to(channel)
                else: await channel.connect(reconnect=True, self_deaf=True)
                await message.channel.send("✅ دخلت الروم الصوتي.")
            except Exception as exc: await message.channel.send(f"❌ تعذر الدخول: {exc}")
        return
    if not message.author.voice or message.author.voice.channel.id != TARGET_ROOM_ID: return
    gid=message.guild.id; vc=message.guild.voice_client
    if content.startswith("-ش "):
        query=content[3:].strip()
        if not query: return await message.channel.send("اكتب اسم الأغنية بعد الأمر، مثال: `-ش اسم الأغنية`")
        try:
            if not vc or not vc.is_connected(): vc=await message.author.voice.channel.connect(reconnect=True, self_deaf=True)
            async with message.channel.typing(): song=await resolve_song(query)
            if vc.is_playing() or vc.is_paused():
                queues.setdefault(gid, []).append(song)
                await message.channel.send(f"➕ أضيفت للانتظار: `{song['title']}`")
            else: await start_song(message.guild, message.channel, song)
        except Exception as exc:
            logging.exception("Search/play failed")
            await message.channel.send(f"❌ تعذر البحث أو التشغيل: `{exc}`")
    elif content == "-وقف":
        if vc and vc.is_playing(): vc.pause(); await message.channel.send("⏸️ تم الإيقاف مؤقتاً.")
    elif content == "-كمل":
        if vc and vc.is_paused(): vc.resume(); await message.channel.send("▶️ تم الاستئناف.")
    elif content in ("-سكب", "-تخطي"):
        if vc and (vc.is_playing() or vc.is_paused()): vc.stop(); await message.channel.send("⏭️ تم التخطي.")
    elif content == "-عيد":
        song=last_songs.get(gid)
        if not song: return await message.channel.send("⚠️ ما فيه أغنية سابقة.")
        if vc and vc.is_connected():
            if vc.is_playing() or vc.is_paused(): queues.setdefault(gid, []).insert(0, song); vc.stop()
            else: await start_song(message.guild, message.channel, song)
            await message.channel.send(f"🔄 إعادة تشغيل: `{song['title']}`")


        elif message.content == '-ادخل2':
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


        elif message.content == '-ريستارت2':
            if message.author.id not in AUTHORIZED_USERS:
                return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
            await message.channel.send('🔄 **جاري إعادة تشغيل البوت الثاني...**')
            import sys
            sys.exit(0)

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


# ==================== [ تشغيل البوت - يجب أن يكون الأخير دائماً ] ====================
if not TOKEN:
    raise RuntimeError("BOT2_TOKEN غير موجود في ملف .env")

client.run(os.getenv('BOT2_TOKEN'))