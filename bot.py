import os
import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI
from dotenv import load_dotenv
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import random
import json
import time
import yt_dlp
from keepalive import keep_alive
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Bật intents để bot có thể đọc tin nhắn, member, role
intents = discord.Intents.all()
intents.message_content = True
intents.messages = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Tạo bot client
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = 1126175374041161759

# Tạo tree để đăng ký slash commands
tree = bot.tree

@bot.event
async def on_ready():
    print(f"🤖 Bot đã đăng nhập thành công: {bot.user}")

    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Slash commands đã sync: {len(synced)} lệnh")
        reset_weekly_points.start()

    except Exception as e:
        print(f"⚠️ Lỗi sync lệnh: {e}")




# Slash command /ping
@tree.command(name="ping", description="Kiểm tra tốc độ phản hồi của bot 🏓")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓", ephemeral=True)


# Slash command /addrole
@tree.command(name="addrole", description="Thêm role cho một thành viên (cần quyền Manage Roles)")
@app_commands.describe(member="Thành viên cần thêm role", role="Role cần thêm")
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Bạn không có quyền để dùng lệnh này!", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Đã thêm role **{role.name}** cho {member.mention}!")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để thêm role này (hãy kéo role bot lên cao hơn).")
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Lỗi: {e}")

# ==============================
# /join – Vào kênh thoại
# ==============================
@tree.command(name="join", description="Cho bot vào kênh thoại hiện tại của bạn")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bạn phải ở trong kênh thoại trước!", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if vc and vc.is_connected():
        await vc.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(f"✅ Đã kết nối tới **{channel.name}**")


# ==============================
# /play – Phát nhạc
# ==============================
@tree.command(name="play", description="Phát nhạc từ YouTube")
@app_commands.describe(url="Link YouTube")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Bạn phải ở trong kênh thoại trước!", ephemeral=True)
        return

    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if not vc or not vc.is_connected():
        vc = await interaction.user.voice.channel.connect()

    await interaction.response.send_message("🎵 Đang tải nhạc...")

    ydl_opts = {
        'format': 'bestaudio',
        'cookiefile': 'cookies.txt'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Không rõ')
    except Exception as e:
        await interaction.followup.send(f"⚠️ Lỗi khi tải nhạc: {e}")
        return

    guild_id = interaction.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    queues[guild_id].append((audio_url, title))

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Không rõ')
    except Exception as e:
        await interaction.followup.send(f"⚠️ Lỗi khi tải nhạc: {e}")
        return

    guild_id = interaction.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    queues[guild_id].append((audio_url, title))

    if not vc.is_playing():
        await play_next(interaction.guild, vc)

    await interaction.followup.send(f"🎶 Thêm vào hàng chờ: **{title}**")


async def play_next(guild, vc):
    guild_id = guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await vc.disconnect()
        return

    url, title = queues[guild_id].pop(0)
    source = discord.FFmpegPCMAudio(url)
    vc.play(source, after=lambda e: bot.loop.create_task(play_next(guild, vc)))
    print(f"🎧 Đang phát: {title}")


# ==============================
# /pause – Tạm dừng nhạc
# ==============================
@tree.command(name="pause", description="Tạm dừng bài hát hiện tại")
async def pause(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Đã tạm dừng.")
    else:
        await interaction.response.send_message("❌ Không có nhạc đang phát.", ephemeral=True)


# ==============================
# /resume – Tiếp tục nhạc
# ==============================
@tree.command(name="resume", description="Tiếp tục phát nhạc")
async def resume(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Tiếp tục phát.")
    else:
        await interaction.response.send_message("❌ Không có nhạc bị tạm dừng.", ephemeral=True)


# ==============================
# /stop – Dừng phát và rời kênh
# ==============================
@tree.command(name="stop", description="Dừng phát và rời khỏi kênh thoại")
async def stop(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_connected():
        await vc.disconnect()
        queues[interaction.guild.id] = []
        await interaction.response.send_message("⏹️ Đã dừng và rời kênh.")
    else:
        await interaction.response.send_message("❌ Bot không ở trong kênh thoại.", ephemeral=True)


# ==============================
# /queue – Xem hàng chờ
# ==============================
@tree.command(name="queue", description="Xem danh sách bài hát trong hàng chờ")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await interaction.response.send_message("📭 Hàng chờ trống.")
        return

    queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(queues[guild_id])])
    await interaction.response.send_message(f"📜 **Hàng chờ:**\n{queue_list}")
#===============================
#tạo giveaway
#===============================
@tree.command(name="giveaway", description="Tạo một giveaway 🎉")
async def giveaway(interaction: discord.Interaction, prize: str, duration: str, winners: int = 1):
    await interaction.response.send_message(f"🎉 Giveaway cho **{prize}** đã bắt đầu!", ephemeral=True)

    # Chuyển thời gian
    time_multipliers = {"s": 1, "m": 60, "h": 3600}
    try:
        seconds = int(duration[:-1]) * time_multipliers[duration[-1].lower()]
    except:
        await interaction.followup.send("⚠️ Sai định dạng thời gian! Dùng như: `30s`, `5m`, `1h`", ephemeral=True)
        return

    # Tạo embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Giải thưởng:** {prize}\n"
                    f"**Người tổ chức:** {interaction.user.mention}\n"
                    f"**Thời gian:** {duration}\n\n"
                    f"React 🎉 để tham gia!",
        color=discord.Color.blurple()
    )
    message = await interaction.channel.send(embed=embed)
    await message.add_reaction("🎉")

    print("✅ Giveaway started!")
    await asyncio.sleep(seconds)
    print("⏰ Time’s up!")

    # Lấy danh sách người tham gia (discord.py >= 2.4)
    new_message = await interaction.channel.fetch_message(message.id)
    users = [u async for u in new_message.reactions[0].users()]
    users = [u for u in users if not u.bot]

    if not users:
        await interaction.channel.send("😢 Không có ai tham gia giveaway.")
        return

    winner_list = random.sample(users, min(winners, len(users)))
    winners_mentions = ", ".join(u.mention for u in winner_list)
    await interaction.channel.send(f"🎊 Chúc mừng {winners_mentions}! Bạn đã thắng **{prize}** 🎁")
#===================================
#CHAT  GPT
#===================================
conversation_history = {}

@tree.command(name="chat", description="Trò chuyện với AI")
@app_commands.describe(message="Tin nhắn bạn muốn nói với bot")
async def chat(interaction: discord.Interaction, message: str):
    user_id = str(interaction.user.id)
    await interaction.response.defer()

    # Tạo danh sách hội thoại cho từng người
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": message})

    # Giữ tối đa 5 tin gần nhất
    if len(conversation_history[user_id]) > 5:
        conversation_history[user_id] = conversation_history[user_id][-5:]

    # Gọi OpenAI API
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Hoặc gpt-3.5-turbo nếu bạn muốn rẻ hơn
            messages=[
                {"role": "system", "content": """
Bạn là ngải — một người bạn AI người Việt thân thiện, biết nói chuyện tự nhiên, cảm xúc, hài hước nhẹ.
Bạn nói chuyện bằng giọng vui vẻ, gần gũi, đôi khi pha chút meme hoặc emoji cho tự nhiên.
Đừng quá nghiêm túc, hãy nói chuyện như một người bạn thật sự.
"""},
                *conversation_history[user_id]
            ],
        )

        reply = response.choices[0].message.content

        # Lưu phản hồi vào lịch sử
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        await interaction.followup.send(reply)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Có lỗi khi gọi AI: {e}")

# ————————————————————————————
# (Tùy chọn) Tự động phản hồi khi ai nhắc tên bot
# ————————————————————————————
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message):
        user_id = str(message.author.id)

        if user_id not in conversation_history:
            conversation_history[user_id] = []

        conversation_history[user_id].append({"role": "user", "content": message.content})

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """
Bạn là ngải — một người bạn AI người Việt thân thiện, tự nhiên, dễ thương, biết pha trò và bộc lộ cảm xúc.
Luôn nói chuyện gần gũi, không quá nghiêm túc, như đang nhắn tin với bạn bè.
"""},
                    *conversation_history[user_id]
                ],
            )

            reply = response.choices[0].message.content
            conversation_history[user_id].append({"role": "assistant", "content": reply})
            await message.reply(reply)

        except Exception as e:
            await message.reply(f"⚠️ Có lỗi khi gọi AI: {e}")
# ============================
# 🔇 MUTE
# ============================
from datetime import timedelta

@bot.tree.command(name="mute", description="Tắt tiếng một thành viên", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="Người cần mute", duration="Thời gian (phút)", reason="Lý do")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "Không có lý do"):
    try:
        await member.timeout_for(timedelta(minutes=duration), reason=reason)
        await interaction.response.send_message(
            f"🔇 {member.mention} đã bị hạn chế {duration} phút. Lý do: {reason}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Không thể mute {member.mention}: {e}", ephemeral=True)


# ============================
# ⚠️ WARN
# ============================
warnings = {}

@bot.tree.command(name="warn", description="Cảnh cáo thành viên", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="Người cần cảnh cáo", reason="Lý do cảnh cáo")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("🚫 Bạn không có quyền cảnh cáo!", ephemeral=True)

    user_id = str(member.id)
    warnings[user_id] = warnings.get(user_id, 0) + 1

    await interaction.response.send_message(f"⚠️ {member.mention} đã bị cảnh cáo ({warnings[user_id]} lần).\n📄 Lý do: {reason}")

    if warnings[user_id] >= 3:
        await member.kick(reason="Nhận 3 cảnh cáo")
        await interaction.channel.send(f"🚪 {member.mention} đã bị kick vì quá 3 cảnh cáo.")

# ============================
# 🔨 BAN
# ============================
@bot.tree.command(name="ban", description="Cấm vĩnh viễn một thành viên", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="Người cần ban", reason="Lý do")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("🚫 Bạn không có quyền ban!", ephemeral=True)

    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ {member.mention} đã bị ban.\n📄 Lý do: {reason}")
    
# ==========================
# 👢 KICK
# ==========================
@bot.tree.command(name="kick", description="kick thành viên", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="Người cần kick", reason="Lý do")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"🚫 {member.mention} đã bị kick. Lý do: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Không thể kick {member.mention}: {e}", ephemeral=True)

# ============================
# ♻️ UNMUTE
# ============================
@bot.tree.command(name="unmute", description="Gỡ hạn chế thành viên", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="Người cần gỡ mute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout_for(None)  # Bỏ giới hạn
        await interaction.response.send_message(f"✅ {member.mention} đã được gỡ hạn chế.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi khi unmute: {e}", ephemeral=True)


POINTS_FILE = "points.json"

# ==========================
# 📦 DỮ LIỆU
# ==========================
def load_points():
    try:
        with open(POINTS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_points(data):
    with open(POINTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

points = load_points()
voice_times = {}  # {user_id: join_timestamp}


# ==========================
# 🚀 KHI BOT KHỞI ĐỘNG
# ==========================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced ({len(synced)} lệnh)")
    except Exception as e:
        print(f"⚠️ Lỗi sync: {e}")
    reset_weekly_points.start()


# ==========================
# 💬 TÍNH ĐIỂM CHAT
# ==========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    points[user_id] = points.get(user_id, 0) + 1
    save_points(points)
    await bot.process_commands(message)


# ==========================
# 🔊 TÍNH ĐIỂM VOICE
# ==========================
@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)

    # Vào voice
    if after.channel and not before.channel:
        voice_times[user_id] = time.time()

    # Rời voice
    elif before.channel and not after.channel and user_id in voice_times:
        duration = int(time.time() - voice_times[user_id])
        del voice_times[user_id]

        points[user_id] = points.get(user_id, 0) + duration // 60
        save_points(points)


# ==========================
# 📊 /rank
# ==========================
@bot.tree.command(name="rank", description="Xem điểm hoạt động cá nhân")
async def rank(interaction: discord.Interaction):
    user = interaction.user
    user_id = str(user.id)
    score = points.get(user_id, 0)

    # Tính rank
    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)
    rank_pos = next((i + 1 for i, (uid, _) in enumerate(sorted_points) if uid == user_id), "Chưa có")

    embed = discord.Embed(
        title="📊 Xếp hạng cá nhân",
        description=f"Bạn đang ở hạng **#{rank_pos}** với **{score}** điểm 🎯",
        color=discord.Color.random()
    )
    embed.set_author(name=user.display_name, icon_url=user.avatar)
    embed.set_footer(text="Hoạt động dựa trên chat & voice trong tuần")
    await interaction.response.send_message(embed=embed)


# ==========================
# 🏆 /leaderboard
# ==========================
@bot.tree.command(name="leaderboard", description="Xem bảng xếp hạng năng động nhất tuần")
async def leaderboard(interaction: discord.Interaction):
    if not points:
        return await interaction.response.send_message("❌ Chưa có dữ liệu hoạt động!")

    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)
    top = sorted_points[:10]

    embed = discord.Embed(
        title="🏆 BẢNG XẾP HẠNG NĂNG ĐỘNG TUẦN NÀY 🏆",
        color=discord.Color.gold()
    )

    desc = ""
    for i, (user_id, score) in enumerate(top, start=1):
        medal = "👑" if i == 1 else "2️⃣" if i == 2 else "3️⃣" if i == 3 else f"{i}️⃣"
        desc += f"{medal} <@{user_id}> — **{score}** điểm\n"
    embed.description = desc
    embed.set_footer(text="Tự động reset mỗi 7 ngày")

    await interaction.response.send_message(embed=embed)


# ==========================
# 🔁 /resetleaderboard (admin only)
# ==========================
@bot.tree.command(name="resetleaderboard", description="Reset bảng xếp hạng (admin)")
@app_commands.checks.has_permissions(administrator=True)
async def resetleaderboard(interaction: discord.Interaction):
    global points
    points = {}
    save_points(points)
    await interaction.response.send_message("🔁 Đã reset bảng xếp hạng tuần!", ephemeral=True)


@resetleaderboard.error
async def resetleaderboard_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này!", ephemeral=True)


# ==========================
# 🕒 RESET TỰ ĐỘNG MỖI 7 NGÀY
# ==========================
@tasks.loop(hours=168)
async def reset_weekly_points():
    global points
    points = {}
    save_points(points)
    print("🔁 Đã reset bảng xếp hạng tuần!")




# Chạy web keepalive + bot
if __name__ == "__main__":
    keepalive_url = keep_alive()  # giữ bot online nếu bạn dùng Render + UptimeRobot
    print(f"🌐 Keepalive server đang chạy tại: {keepalive_url}")
    bot.run(os.getenv("DISCORD_TOKEN"))


























