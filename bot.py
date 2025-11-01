import os
import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import random
import yt_dlp
from keepalive import keep_alive
load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Bật intents để bot có thể đọc tin nhắn, member, role
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Tạo bot client
bot = commands.Bot(command_prefix="!", intents=intents)

# Tạo tree để đăng ký slash commands
tree = bot.tree

@bot.event
async def on_ready():
    print(f"🤖 Bot đã đăng nhập thành công: {bot.user}")
    try:
        synced = await tree.sync()
        print(f"✅ Slash commands đã sync: {len(synced)} lệnh")
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



# Chạy web keepalive + bot
if __name__ == "__main__":
    keepalive_url = keep_alive()  # giữ bot online nếu bạn dùng Render + UptimeRobot
    print(f"🌐 Keepalive server đang chạy tại: {keepalive_url}")
    bot.run(os.getenv("DISCORD_TOKEN"))
















