import ssl, asyncio, discord, yt_dlp, os, json, random, io, time, aiohttp
from datetime import datetime, timezone
from discord.ui import Button, View, Select
from discord.ext import commands

try:
    if not discord.opus.is_loaded():
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
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.moderation = True

client = discord.Client(intents=intents)

# ==================== [ الإعدادات الثابتة ] ====================


TARGET_ROOM_ID = 1510342490723451021  
TICKETS_PANEL_CHANNEL_NAME = "tickets" 
LOG_CHANNEL_NAME = "logs"              
TICKETS_LOG_CHANNEL_NAME = "tickets-log" 
CREATE_VOICE_CHANNEL_NAME = "➕ إنشاء روم"  
AUTO_ROLE_NAME = "Member"              

PHOTO_CHANNEL_ID = 1511936493881397369
VIDEO_CHANNEL_ID = 1510342490580975844
MOVIE_CHANNEL_ID = 1518470808568332439

# آيدي الروم الصوتي الإحصائي الخاص بعدد أعضاء السيرفر
STATS_VOICE_CHANNEL_ID = 1561145001503891506  # <--- استبدل الأصفار بآيدي الروم الصوتي

GIRLS_ROLE_IDS = [1510342489889046555, 1523088337559097404]

TMDB_API_KEY = os.getenv('TMDB_API_KEY', '')
ALLOWED_TICKET_ROLES = [1510342489926533124, 1516701514536583258]
CACHE_FILE = "msg_cache.json"

AUTHORIZED_USERS = {
    967675648522989578: "وليد",
    851952174590066728: "أحمد",
    1434636048817721424: "عبادي",
    1558412634653462632: "waleed"
}


TARGET_USER_ID = 1134969480380960810        # آيدي الشخص المراد مراقبته
TARGET_TEXT_CHANNEL_ID = 1510342490580975843    # آيدي الروم النصي لإرسال التنبيه

logging_enabled = True
target_tracking_enabled = True  
queue = []
last_played_song = None
autoplay_mode = False
current_volume = 1.0  
active_control_message = None  
played_history = set()  


# ==================== [ اوامر الافلام ] ====================

GENRE_MAP = {
    "action": {"id": 28, "name": "أكشن 🎯"},
    "comedy": {"id": 35, "name": "كوميديا 😂"},
    "horror": {"id": 27, "name": "رعب 👻"},
    "drama": {"id": 18, "name": "دراما 🎭"},
    "scifi": {"id": 878, "name": "خيال علمي 🌌"},
    "animation": {"id": 16, "name": "أنيميشن 🎨"},
    "romance": {"id": 10749, "name": "رومانسية ❤️"},
    "crime": {"id": 80, "name": "جريمة وغموض 🕵️‍♂️"}
}

TV_GENRE_MAP = {
    "action": {"id": 10759, "name": "أكشن ومغامرة 🎯"},
    "comedy": {"id": 35, "name": "كوميديا 😂"},
    "drama": {"id": 18, "name": "دراما 🎭"},
    "scifi": {"id": 10765, "name": "خيال علمي وفانتازيا 🌌"},
    "animation": {"id": 16, "name": "أنيميشن 🎨"},
    "crime": {"id": 80, "name": "جريمة وغموض 🕵️‍♂️"},
    "mystery": {"id": 9648, "name": "غموض وتحقيق 🔍"},
    "documentary": {"id": 99, "name": "وثائقي 🌍"}
}


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

msg_memory = load_cache()

def save_cache():
    try:
        global msg_memory
        if len(msg_memory) > 3000:
            keys = list(msg_memory.keys())
            for k in keys[:-3000]: del msg_memory[k]
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(msg_memory, f, ensure_ascii=False)
    except: pass
    
async def fetch_movie_embed(genre_id=None, year_filter=None, specific_type="movie"):
    if not TMDB_API_KEY:
        return None, "⚠️ أضف TMDB_API_KEY إلى ملف .env لتفعيل ترشيحات الأفلام."
    endpoint = "movie" if specific_type == "movie" else "tv"
    random_page = random.randint(1, 4)
    url = f"https://api.themoviedb.org/3/discover/{endpoint}?api_key={TMDB_API_KEY}&language=ar-SA&page={random_page}"
    if genre_id: url += f"&with_genres={genre_id}"
    if year_filter == "gt": url += "&primary_release_date.gte=2001-01-01"
    elif year_filter == "lt": url += "&primary_release_date.lte=2000-12-31"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200: return None, "❌ تعذر الاتصال بموقع الأفلام."
                data = await resp.json()
            results = data.get("results", [])
            if not results: return None, "❌ لم يتم العثور على أعمال مطابقة."
            
            item = None
            for _ in range(5):
                candidate = random.choice(results)
                if candidate.get("overview"):
                    item = candidate
                    break
            if not item:
                item = random.choice(results)

            title = item.get("title") or item.get("name") or "عمل بدون اسم"
            release_date = item.get("release_date") or item.get("first_air_date") or "غير محدد"
            year = release_date.split("-")[0] if "-" in release_date else release_date
            overview = item.get("overview") or "لا توجد قصة متاحة."
            
            vote_average = item.get("vote_average", 0)
            vote_count = item.get("vote_count", 0)
            rating_text = f"⭐ `{vote_average:.1f}/10` (من `{vote_count}` صوت)" if vote_count > 0 else "⭐ `غير متوفر`"

            poster_path = item.get("poster_path")
            
            embed = discord.Embed(
                title=f"🍿 ترشيح سينمائي: {title}",
                description=f"📅 **السنة:** `{year}`\n\n📖 **القصة:**\n{overview}\n\n🌟 **التقييم:** {rating_text}",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            file = None
            if poster_path:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"https://image.tmdb.org/t/p/w500{poster_path}", timeout=10) as img_resp:
                            if img_resp.status == 200:
                                image_bytes = await img_resp.read()
                                file = discord.File(io.BytesIO(image_bytes), filename="poster.jpg")
                                embed.set_image(url="attachment://poster.jpg")
                except:
                    pass
            return embed, file
    except: return None, "❌ حدث خطأ."

class MovieGenreSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=info["name"], value=key) for key, info in GENRE_MAP.items()]
        super().__init__(placeholder="اختر التصنيف...", min_values=1, max_values=1, options=options, custom_id="persistent_movie_genre_select")
    async def callback(self, interaction: discord.Interaction):
        genre_info = GENRE_MAP.get(self.values[0])
        embed = discord.Embed(title=f"تحديد سنة الإصدار ({genre_info['name']})", color=discord.Color.dark_red())
        await interaction.response.edit_message(embed=embed, view=MovieYearView(self.values[0], genre_info))

class MoviePanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MovieGenreSelect())

class MovieYearSelect(Select):
    def __init__(self, genre_key, genre_info):
        self.genre_info = genre_info
        options = [
            discord.SelectOption(label="أفلام حديثة (فوق 2000)", value="gt", emoji="✨"),
            discord.SelectOption(label="أفلام كلاسيكية (تحت 2000)", value="lt", emoji="📼"),
            discord.SelectOption(label="الكل", value="none", emoji="🎲")
        ]
        super().__init__(placeholder="حدد السنة...", min_values=1, max_values=1, options=options, custom_id=f"movie_year_{genre_key}")
    async def callback(self, interaction: discord.Interaction):
        try: await interaction.message.delete()
        except: pass
        await interaction.response.defer(thinking=True)
        embed, file = await fetch_movie_embed(genre_id=self.genre_info["id"], year_filter=None if self.values[0] == "none" else self.values[0])
        if embed:
            if file: await interaction.followup.send(embed=embed, file=file)
            else: await interaction.followup.send(embed=embed)

class MovieYearView(View):
    def __init__(self, genre_key, genre_info):
        super().__init__(timeout=None)
        self.add_item(MovieYearSelect(genre_key, genre_info))

class TVGenreSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=info["name"], value=key) for key, info in TV_GENRE_MAP.items()]
        super().__init__(placeholder="اختر تصنيف المسلسل...", min_values=1, max_values=1, options=options, custom_id="persistent_tv_genre_select")
    async def callback(self, interaction: discord.Interaction):
        genre_info = TV_GENRE_MAP.get(self.values[0])
        try: await interaction.message.delete()
        except: pass
        await interaction.response.defer(thinking=True)
        embed, file = await fetch_movie_embed(genre_id=genre_info["id"], specific_type="tv")
        if embed:
            if file: await interaction.followup.send(embed=embed, file=file)
            else: await interaction.followup.send(embed=embed)

class TVPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TVGenreSelect())

async def movie_recommendation_loop():
    await client.wait_until_ready()
    await asyncio.sleep(5)
    try:
        movie_channel = client.get_channel(MOVIE_CHANNEL_ID)
        if movie_channel:
            embed, file = await fetch_movie_embed(specific_type=random.choice(["movie", "tv"]))
            if embed:
                if file: await movie_channel.send(embed=embed, file=file)
                else: await movie_channel.send(embed=embed)
    except:
        pass

    while not client.is_closed():
        await asyncio.sleep(600)
        try:
            movie_channel = client.get_channel(MOVIE_CHANNEL_ID)
            if movie_channel:
                embed, file = await fetch_movie_embed(specific_type=random.choice(["movie", "tv"]))
                if embed:
                    if file: await movie_channel.send(embed=embed, file=file)
                    else: await movie_channel.send(embed=embed)
        except: pass

# ==================== [ وظيفة تحديث روم الإحصائيات فورياً ] ====================

async def update_stats_channel(guild):
    try:
        if STATS_VOICE_CHANNEL_ID != 0:
            ch = guild.get_channel(STATS_VOICE_CHANNEL_ID)
            if ch:
                total_members = guild.member_count
                new_name = f"🔒 Members : {total_members}"
                if ch.name != new_name:
                    await ch.edit(name=new_name)
    except Exception as e:
        print(f"⚠️ خطأ في تحديث روم الإحصائيات: {e}")

# ==================== [ اوامر الاغاني ] ====================

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
    global last_played_song, autoplay_mode
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
    global last_played_song
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

# ==================== [ اوامر التكت ] ====================

class TicketControlsView(View):
    def __init__(self, ticket_owner=None):
        super().__init__(timeout=None)
        self.claimed_by = None
        self.ticket_owner = ticket_owner

    @discord.ui.button(label="🖐️ استلام التذكرة", style=discord.ButtonStyle.success, custom_id="btn_claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = interaction.user.id in AUTHORIZED_USERS or any(rid in user_roles for rid in ALLOWED_TICKET_ROLES)
        if not has_permission: return await interaction.response.send_message("❌ غير مسموح!", ephemeral=True)
        if self.claimed_by: return await interaction.response.send_message("⚠️ مستلمة بالفعل!", ephemeral=True)
        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"مستلمة بواسطة {interaction.user.display_name}"
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🙋‍♂️ تم الاستلام بواسطة {interaction.user.mention}")

    @discord.ui.button(label="🔒 إغلاق التذكرة", style=discord.ButtonStyle.danger, custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 **جاري حفظ الترانسكريبت وإغلاق التذكرة خلال 5 ثوانٍ...**")
        
        messages = [message async for message in interaction.channel.history(limit=500, oldest_first=True)]
        transcript_content = f"=== سجل محادثات التذكرة: {interaction.channel.name} ===\n"
        attachments_collected = []
        
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            content = msg.content or "*[محتوى فارغ]*"
            transcript_content += f"[{timestamp}] {msg.author}: {content}\n"
            for att in msg.attachments:
                attachments_collected.append(f"• {msg.author}: {att.url}")
                transcript_content += f"  [مرفق: {att.url}]\n"

        file_io = io.BytesIO(transcript_content.encode('utf-8'))
        transcript_file = discord.File(file_io, filename=f"transcript-{interaction.channel.name}.txt")

        log_channel = interaction.guild.get_channel(1519217840404693002)
        if log_channel:
            claimed_by_text = self.claimed_by.mention if self.claimed_by else "غير مسجل"
            ticket_owner_text = self.ticket_owner.mention if self.ticket_owner else "غير معروف"
            
            embed = discord.Embed(
                title="📄 لوق إغلاق تذكرة (Transcript)",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="أغلق بواسطة", value=interaction.user.mention, inline=True)
            embed.add_field(name="صاحب التذكرة", value=ticket_owner_text, inline=True)
            embed.add_field(name="اسم التذكرة", value=interaction.channel.name, inline=True)
            embed.add_field(name="مستلم التذكرة", value=claimed_by_text, inline=False)

            await log_channel.send(embed=embed, file=transcript_file)
            
            if attachments_collected:
                att_text = "🖼️ **المرفقات والصور التي أرسلت بالسرية داخل التذكرة:**\n" + "\n".join(attachments_collected)
                await log_channel.send(att_text)

        await asyncio.sleep(5)
        await interaction.channel.delete()

class StandaloneTicketView(View):
    def __init__(self): 
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 فتح تذكرة دعم", style=discord.ButtonStyle.primary, custom_id="btn_standalone_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = interaction.user
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), member: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await guild.create_text_channel(name=f"ticket-{member.display_name}", overwrites=overwrites)
        await ch.send(embed=discord.Embed(title="تذكرة جديدة", description=f"أهلاً بك {member.mention}"), view=TicketControlsView(ticket_owner=member))
        await interaction.response.send_message(f"✅ تم فتح التذكرة في {ch.mention}", ephemeral=True)

# ==================== [ الأحداث العامة والإقلاع ] ====================

@client.event
async def on_ready():
    print(f'--> Logged in as {client.user}')
    client.add_view(StandaloneTicketView())
    client.add_view(TicketControlsView())
    client.add_view(MoviePanelView())
    client.add_view(TVPanelView())
    client.add_view(MusicControlView())
    client.loop.create_task(movie_recommendation_loop())
    
    for guild in client.guilds:
        await update_stats_channel(guild)
    
    ch = client.get_channel(TARGET_ROOM_ID)
    if ch:
        vc = discord.utils.get(client.voice_clients, guild=ch.guild)
        if not vc:
            await ch.connect(reconnect=True, self_deaf=True)
            print("🔒 تم تثبيت البوت الأول في الروم للأبد.")

@client.event
async def on_member_join(member):
    await asyncio.sleep(1)
    await update_stats_channel(member.guild)

    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        try: await member.add_roles(role)
        except: pass
    try:
        new_nick = f"IMP | {member.display_name}"
        if len(new_nick) <= 32: await member.edit(nick=new_nick)
    except: pass

@client.event
async def on_member_remove(member):
    await asyncio.sleep(1)
    await update_stats_channel(member.guild)

@client.event
async def on_message(message):
    global logging_enabled, target_tracking_enabled, msg_memory, last_played_song
    
    if message.author != client.user:
        msg_memory[str(message.id)] = {
            'author_mention': message.author.mention,
            'content': message.content,
            'attachments': [att.url for att in message.attachments],
            'is_bot': message.author.bot
        }
        save_cache()

    if message.author == client.user: return

    if message.content == '-wsoff':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        target_tracking_enabled = False
        return await message.channel.send('🔴 **تم إيقاف تتبع وردود الشخص المخصص مؤقتاً.**')

    elif message.content == '-wson':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        target_tracking_enabled = True
        return await message.channel.send('🟢 **تم تفعيل وإعادة تشغيل تتبع وردود الشخص المخصص بنجاح.**')

    if target_tracking_enabled and message.author.id == TARGET_USER_ID:
        await message.channel.send("الهاك يعرف يكتب غريبه")

    if message.content.strip() == '-ريستارت':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        await message.channel.send('🔄 **جاري إعادة تشغيل البوت الأول وتطبيق التحديثات...**')
        try:
            await client.close()
        except:
            pass
        import os
        os._exit(0)

    if message.content == '-logon':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        logging_enabled = True
        return await message.channel.send('🟢 **تم تفعيل جميع اللوقات بنجاح.**')

    elif message.content == '-logoff':
        if message.author.id not in AUTHORIZED_USERS:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!')
        logging_enabled = False
        return await message.channel.send('🔴 **تم إيقاف جميع اللوقات بالكامل.**')

    elif message.content.startswith(('-clear', '-مسح')):
        user_roles = [role.id for role in message.author.roles]
        has_permission = message.author.id in AUTHORIZED_USERS or any(rid in user_roles for rid in ALLOWED_TICKET_ROLES)
        if not has_permission:
            return await message.channel.send('❌ عذراً، هذا الأمر مخصص للإدارة فقط!', delete_after=5)
        
        args = message.content.split()
        limit = 10
        if len(args) > 1 and args[1].isdigit():
            limit = int(args[1])
        
        try:
            await message.delete()
            deleted = await message.channel.purge(limit=limit)
            msg = await message.channel.send(f"🧹 **تم مسح `{len(deleted)}` رسالة بنجاح.**")
            await asyncio.sleep(4)
            await msg.delete()
        except Exception as e:
            await message.channel.send(f"❌ حدث خطأ أثناء مسح الرسائل: {e}", delete_after=5)
        return

    elif message.content == '-ادخل':
        if message.author.id not in AUTHORIZED_USERS: return
        try:
            ch = client.get_channel(TARGET_ROOM_ID)
            if ch:
                vc = message.guild.voice_client
                if vc and vc.is_connected():
                    await vc.move_to(ch)
                else:
                    await ch.connect(reconnect=True, self_deaf=True)
                try: await message.delete()
                except: pass
            else:
                await message.channel.send("❌ لم يتم العثور على الروم الصوتي المحدد.")
        except Exception as e:
            await message.channel.send(f"❌ حدث خطأ: {e}")
        return

    elif message.content == '-فلم':
        await message.channel.send("🍿 مكتبة الأفلام:", view=MoviePanelView())
        return

    elif message.content == '-مسلسل':
        await message.channel.send("📺 مكتبة المسلسلات:", view=TVPanelView())
        return

    elif message.content.startswith('-ش '):
        query = message.content[3:].strip()
        if not message.author.voice or message.author.voice.channel.id != TARGET_ROOM_ID: return
        vc = message.guild.voice_client
        if not vc: vc = await message.author.voice.channel.connect(reconnect=True, self_deaf=True)
        
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query if query.startswith('http') else f"ytsearch1:{query}", download=False))
            if 'entries' in data: data = data['entries'][0]
            song_data = {'url': data['url'], 'title': data.get('title', 'مقطع صوتي')}

            if vc.is_playing() or vc.is_paused():
                queue.append(song_data)
                await message.channel.send(f"➕ **أضيفت للانتظار:** `{song_data['title']}`")
            else:
                last_played_song = song_data
                played_history.add(song_data['title'])
                audio_source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(song_data['url'], **FFMPEG_OPTIONS),
                    volume=current_volume
                )
                vc.play(audio_source, after=lambda e: play_next(client, message.channel))
                embed = discord.Embed(
                    title="🎶 جاري التشغيل الآن",
                    description=f"🎵 **العنوان:** `{song_data['title']}`\n👥 **المستدعي:** `{message.author.mention}`",
                    color=discord.Color.blurple()
                )
                await send_or_update_control_message(message.channel, embed)

    elif message.content == '-وقف':
        vc = message.guild.voice_client
        if vc and vc.is_playing(): vc.pause(); await message.channel.send('⏸️ **تم الإيقاف مؤقتاً.**')
    elif message.content == '-كمل':
        vc = message.guild.voice_client
        if vc and vc.is_paused(): vc.resume(); await message.channel.send('▶️ **تم الاستئناف!**')
    elif message.content in ['-سكب', '-تخطي']:
        vc = message.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()): vc.stop(); await message.channel.send('⏭️ **تم التخطي!**')
    elif message.content == '-عيد':
        if not last_played_song: return await message.channel.send("⚠️ لا توجد أغنية سابقة!")
        vc = message.guild.voice_client
        if vc:
            queue.insert(0, last_played_song)
            vc.stop()
            await message.channel.send(f"🔄 **إعادة تشغيل:** `{last_played_song['title']}`")


# ==================== [ اللوقات الكاملة وتتبع الشخص المحدد ] ====================


@client.event
async def on_voice_state_update(member, before, after):
    global logging_enabled, target_tracking_enabled
    
    if target_tracking_enabled and member.id == TARGET_USER_ID:
        text_channel = client.get_channel(TARGET_TEXT_CHANNEL_ID)
        
        if before.channel is None and after.channel is not None:
            msg = f"الهاك دخل في : {after.channel.name}"
            if text_channel:
                try: await text_channel.send(msg)
                except: pass
            try: await member.send(msg)
            except: pass
                
        elif before.channel is not None and after.channel is None:
            msg = "الهاك طلع"
            if text_channel:
                try: await text_channel.send(msg)
                except: pass
            try: await member.send(msg)
            except: pass

    if not logging_enabled: return
    if member.bot: return

    log_channel = discord.utils.get(member.guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return

    if after.channel and after.channel.name == CREATE_VOICE_CHANNEL_NAME:
        guild = member.guild
        category = after.channel.category
        new_channel = await guild.create_voice_channel(name=f"🔊 روم {member.display_name}", category=category)
        await member.move_to(new_channel)
        def check_empty(m, b, a): return len(new_channel.members) == 0
        await client.wait_for('voice_state_update', check=check_empty)
        await new_channel.delete()
        return

    async def get_actor(action_type):
        for _ in range(5):
            try:
                async for entry in member.guild.audit_logs(limit=15, action=action_type):
                    if entry.target.id == member.id:
                        created = entry.created_at
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                        if abs((discord.utils.utcnow() - created).total_seconds()) < 15:
                            return entry.user
            except: pass
            await asyncio.sleep(1)
        return None

    if before.channel is not None and after.channel is None:
        disconnecter = await get_actor(discord.AuditLogAction.member_disconnect)
        if disconnecter and disconnecter.id != member.id:
            embed = discord.Embed(
                title="📤 تم فصل عضو من قناة صوتية",
                description=f"تم فصل {member.mention} من قناة صوتية بواسطة {disconnecter.mention}.\n\n**العضو:**\n{member.mention}\n\n**فصله:**\n{disconnecter.mention}\n\n**القناة:**\n🔊 {before.channel.name}",
                color=discord.Color.from_rgb(88, 101, 242)
            )
        else:
            embed = discord.Embed(
                title="📤 تم فصل عضو من قناة صوتية",
                description=f"تم فصل {member.mention} من قناة صوتية.\n\n**العضو:**\n{member.mention}\n\n**فصله:**\n{member.mention} (من نفسه)\n\n**القناة:**\n🔊 {before.channel.name}",
                color=discord.Color.from_rgb(88, 101, 242)
            )
        await log_channel.send(embed=embed)

    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        mover = await get_actor(discord.AuditLogAction.member_move)
        if mover and mover.id != member.id:
            embed = discord.Embed(
                title="↔️ تم نقل عضو بين القنوات الصوتية",
                description=f"تم نقل العضو {member.mention} بواسطة {mover.mention} إلى قناة صوتية أخرى.\n\n**العضو:**\n{member.mention}\n\n**نقله:**\n{mover.mention}\n\n**من:**\n🔊 {before.channel.name}\n\n**إلى:**\n🔊 {after.channel.name}",
                color=discord.Color.from_rgb(88, 101, 242)
            )
        else:
            embed = discord.Embed(
                title="↔️ تم نقل عضو بين القنوات الصوتية",
                description=f"تم نقل العضو {member.mention} بين القنوات الصوتية.\n\n**العضو:**\n{member.mention}\n\n**نقله:**\n{member.mention} (من نفسه)\n\n**من:**\n🔊 {before.channel.name}\n\n**إلى:**\n🔊 {after.channel.name}",
                color=discord.Color.from_rgb(88, 101, 242)
            )
        await log_channel.send(embed=embed)

    elif before.channel is None and after.channel is not None:
        embed = discord.Embed(
            title="📥  انضم العضو الى القناه",
            description=f"دخل العضو {member.mention} إلى قناة صوتية.\n\n**العضو:**\n{member.mention}\n\n**القناة:**\n🔊 {after.channel.name}",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        await log_channel.send(embed=embed)

    if before.mute != after.mute or before.deaf != after.deaf:
        actor = await get_actor(discord.AuditLogAction.member_update)
        performer = actor.mention if (actor and actor.id != member.id) else "نفسه العضو"

        if not before.mute and after.mute:
            embed = discord.Embed(title="🔇  إعطاء ميوت صوتي (Mute)", description=f"👤 **العضو:** {member.mention}\n🛠️ **بواسطة:** {performer}", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)
        elif before.mute and not after.mute:
            embed = discord.Embed(title="🔊  فك الميوت الصوتي", description=f"👤 **العضو:** {member.mention}\n🛠️ **بواسطة:** {performer}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)

        if not before.deaf and after.deaf:
            embed = discord.Embed(title="🎧  إعطاء ديفن (Deafen)", description=f"👤 **العضو:** {member.mention}\n🛠️ **بواسطة:** {performer}", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)
        elif before.deaf and not after.deaf:
            embed = discord.Embed(title="🎧  فك الديفن", description=f"👤 **العضو:** {member.mention}\n🛠️ **بواسطة:** {performer}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)

@client.event
async def on_member_update(before, after):
    global logging_enabled
    if not logging_enabled: return
    log_channel = discord.utils.get(after.guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return

    if before.timed_out_until != after.timed_out_until:
        performer = "غير معروف"
        reason = "غير محدد"
        await asyncio.sleep(1.5)
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    performer = entry.user.mention
                    if entry.reason: reason = entry.reason
                    break
        except: pass

        if after.timed_out_until is not None:
            log_desc = f"👤 **العضو:** {after.mention}\n🛠️ **بواسطة:** {performer}\n⏰ **حتى تاريخ:** {after.timed_out_until.strftime('%Y-%m-%d %H:%M:%S')}\n📝 **السبب:** {reason}"
            embed = discord.Embed(title="⏰  إعطاء تايم أوت (Mute)", description=log_desc, color=discord.Color.red(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)
        else:
            log_desc = f"👤 **العضو:** {after.mention}\n🛠️ **بواسطة:** {performer}"
            embed = discord.Embed(title="🔊  فك التايم أوت", description=log_desc, color=discord.Color.green(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)

    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        performer = "غير معروف"
        await asyncio.sleep(1.5)
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    performer = entry.user.mention
                    break
        except: pass

        for role in added_roles:
            log_desc = f"👤 **العضو:** {after.mention}\n🛠️ **بواسطة:** {performer}\n🛡️ **الرول المضافة:** {role.mention}"
            embed = discord.Embed(title="🛡️  إضافة رول", description=log_desc, color=discord.Color.green(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)

        for role in removed_roles:
            log_desc = f"👤 **العضو:** {after.mention}\n🛠️ **بواسطة:** {performer}\n🛡️ **الرول المزالة:** {role.mention}"
            embed = discord.Embed(title="🛡️  إزالة رول", description=log_desc, color=discord.Color.red(), timestamp=discord.utils.utcnow())
            await log_channel.send(embed=embed)

@client.event
async def on_member_ban(guild, user):
    global logging_enabled
    if not logging_enabled: return
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return
    performer = "غير معروف"
    reason = "غير محدد"
    await asyncio.sleep(1.5)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                performer = entry.user.mention
                if entry.reason: reason = entry.reason
                break
    except: pass
    log_desc = f"👤 **العضو المحظور:** {user.mention} (`{user.display_name}`)\n🛠️ **بواسطة:** {performer}\n📝 **السبب:** {reason}"
    embed = discord.Embed(title="🔨  حظر عضو (Ban)", description=log_desc, color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    await log_channel.send(embed=embed)

@client.event
async def on_member_unban(guild, user):
    global logging_enabled
    if not logging_enabled: return
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return
    performer = "غير معروف"
    await asyncio.sleep(1.5)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                performer = entry.user.mention
                break
    except: pass
    log_desc = f"👤 **العضو:** {user.mention} (`{user.display_name}`)\n🛠️ **بواسطة:** {performer}"
    embed = discord.Embed(title="🔓  فك الحظر (Unban)", description=log_desc, color=discord.Color.green(), timestamp=discord.utils.utcnow())
    await log_channel.send(embed=embed)

@client.event
async def on_guild_channel_delete(channel):
    global logging_enabled
    if not logging_enabled: return
    log_channel = discord.utils.get(channel.guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return
    deleter = "غير معروف"
    await asyncio.sleep(1.5)
    try:
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user.mention
                break
    except: pass
    ch_type = "نصي 💬" if isinstance(channel, discord.TextChannel) else "صوتي 🔊" if isinstance(channel, discord.VoiceChannel) else "فئة/قسم 📁"
    log_desc = f"📌 **اسم الروم المحذوف:** #{channel.name}\n📁 **نوع الروم:** {ch_type}\n🛠️ **حُذفت بواسطة:** {deleter}"
    embed = discord.Embed(title="🗑️  حذف روم", description=log_desc, color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    await log_channel.send(embed=embed)

@client.event
async def on_raw_message_delete(payload):
    global logging_enabled, msg_memory
    if not logging_enabled: return
    
    guild = client.get_guild(payload.guild_id)
    if not guild: return
    
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not log_channel: return

    saved_info = msg_memory.pop(str(payload.message_id), None)
    save_cache()
    
    author_mention = saved_info['author_mention'] if saved_info else "شخص غير معروف"
    message_content = saved_info['content'] if saved_info else "*[نص غير مسجل]*"
    attachments_list = saved_info['attachments'] if saved_info else []
    is_bot = saved_info['is_bot'] if saved_info else False

    if is_bot: return

    await asyncio.sleep(1.5)
    deleter = author_mention

    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.message_delete):
            if entry.target and entry.target.id != client.user.id:
                deleter = entry.user.mention
                break
    except: pass

    target_channel = guild.get_channel(payload.channel_id)
    channel_mention = target_channel.mention if target_channel else "روم غير معروف"

    log_desc = f"👤 **صاحب الرسالة:** {author_mention}\n🛠️ **حُذفت بواسطة:** {deleter}\n📌 **الروم:** {channel_mention}\n\n"
    if message_content and message_content != "*[نص غير مسجل]*":
        log_desc += f"💬 **المحتوى النصي:**\n{message_content}\n\n"

    if attachments_list:
        log_desc += "🖼️ **المرفقات:**\n"
        for url in attachments_list:
            log_desc += f"• [فتح الملف أو المقطع]({url})\n"
    elif not message_content or message_content == "*[نص غير مسجل]*":
        log_desc += "🖼️ **المحتوى:** *[تم حذف صورة أو مقطع بدون نص]*"

    embed = discord.Embed(title="🗑️  حذف رسالة أو مقطع", description=log_desc, color=discord.Color.dark_orange(), timestamp=discord.utils.utcnow())
    await log_channel.send(embed=embed)




# ==================== [ التوكن ] ====================


client.run(os.getenv('BOT1_TOKEN'))