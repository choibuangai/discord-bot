import os
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import yt_dlp
from keepalive import keep_alive

# Bật intents để bot có thể đọc tin nhắn, member, role
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
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
# ==== LỆNH PHÁT NHẠC ====
def play_next(ctx):
    guild_id = ctx.guild.id
    if queues[guild_id]:
        source = queues[guild_id].pop(0)
        ctx.voice_client.play(source, after=lambda e: play_next(ctx))

async def join_vc(interaction):
    if interaction.user.voice is None:
        await interaction.response.send_message("❌ Bạn phải vào voice channel trước!", ephemeral=True)
        return None
    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if vc is None:
        vc = await channel.connect()
    return vc

@tree.command(name="play", description="Phát nhạc từ link YouTube 🎵")
@app_commands.describe(url="Link YouTube cần phát")
async def play(interaction: discord.Interaction, url: str):
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
        return

    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if not vc:
        vc = await voice_channel.connect()

    await interaction.response.defer()  # tránh Discord timeout

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info["url"]

    ffmpeg_options = {
        "options": "-vn"
    }

    vc.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options))
    await interaction.followup.send(f"🎶 Đang phát: **{info['title']}**")
    else:
        queues[guild_id].append(source)
        await interaction.followup.send(f"📀 Đã thêm vào hàng chờ: **{title}**")

@tree.command(name="pause", description="Tạm dừng nhạc ⏸️")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Đã tạm dừng nhạc!")
    else:
        await interaction.response.send_message("⚠️ Không có bài hát nào đang phát!")

@tree.command(name="resume", description="Tiếp tục phát nhạc ▶️")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Tiếp tục phát nhạc!")
    else:
        await interaction.response.send_message("⚠️ Nhạc chưa bị tạm dừng!")

@tree.command(name="stop", description="Dừng phát nhạc và rời kênh 🔇")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queues[interaction.guild.id] = []
        await vc.disconnect()
        await interaction.response.send_message("🛑 Đã dừng nhạc và rời kênh!")
    else:
        await interaction.response.send_message("⚠️ Bot chưa vào kênh thoại nào!")

@tree.command(name="queue", description="Xem danh sách bài hát trong hàng chờ 🎧")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        await interaction.response.send_message("📭 Hàng chờ trống!")
    else:
        desc = "\n".join([f"{i+1}. {src.title}" for i, src in enumerate(queues[guild_id])])
        await interaction.response.send_message(f"📜 **Danh sách hàng chờ:**\n{desc}")


# Chạy web keepalive + bot
if __name__ == "__main__":
    keepalive_url = keep_alive()  # giữ bot online nếu bạn dùng Render + UptimeRobot
    print(f"🌐 Keepalive server đang chạy tại: {keepalive_url}")
    bot.run(os.getenv("DISCORD_TOKEN"))










