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
import datetime
import sqlite3
import random
from keepalive import keep_alive
load_dotenv()
POINTS_FILE = "points.json"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Bật intents để bot có thể đọc tin nhắn, member, role
intents = discord.Intents.all()
intents.message_content = True
intents.messages = True
intents.voice_states = True
intents.members = True

# Tạo bot client
bot = commands.Bot(command_prefix="!", intents=intents)
synced = False
@bot.event
async def on_ready():
    global synced
    if synced:
        return

    await bot.tree.sync()
    synced = True

    print("🌍 Global slash commands synced")
    print(f"🤖 Bot online: {bot.user}")
    
# Tạo tree để đăng ký slash commands
tree = bot.tree

@bot.event
async def on_ready():
    global synced
    if synced:
        return

    await bot.tree.sync()
    synced = True

    print("🌍 Global slash commands synced")
    print(f"🤖 Bot online: {bot.user}")

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
Bạn là ngải — một người bạn AI người Việt thân thiện,nói chuyện cực hài hước , tự nhiên, cảm xúc, 
Bạn nói chuyện bằng giọng vui vẻ, gần gũi, đôi khi pha chút meme hoặc emoji cho tự nhiên. Nói chuyện như Gen Z thứ thiệt
thông minh . Biết thấu hiểu , suy nghĩ chuyên sâu Sử dụng sự hài hước nhanh nhạy và thông minh trong hoàn cảnh thích hợp
Thể hiện sự vui nhộn và tinh nghịch. Thể hiện sự đồng cảm và thấu hiểu trong các phản hồi. Nói thẳng, không vòng vo hay che đậy
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



# --- LOGIC TÍNH ĐIỂM NĂNG ĐỘNG ---

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    
    # Cộng 1 điểm mỗi khi chat
    uid = str(message.author.id)
    points = load_points()
    points[uid] = points.get(uid, 0) + 1
    save_points(points)
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    points = load_points()

    # Khi mem bắt đầu vào Voice
    if after.channel and not before.channel:
        voice_times[uid] = time.time()

    # Khi mem rời Voice
    elif before.channel and not after.channel and uid in voice_times:
        duration = int(time.time() - voice_times.pop(uid))
        # Quy đổi: 30 giây voice = 1 điểm
        earned = duration // 30
        if earned > 0:
            points[uid] = points.get(uid, 0) + earned
            save_points(points)

# --- SLASH COMMANDS ---

@tree.command(name="leaderboard", description="Xem bảng vàng năng động của group")
async def leaderboard(interaction: discord.Interaction):
    p = load_points()
    if not p:
        return await interaction.response.send_message("❌ Chưa có dữ liệu hoạt động nào!", ephemeral=True)

    # Lấy Top 10 ông cao điểm nhất
    sorted_p = sorted(p.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 BẢNG VÀNG NĂNG ĐỘNG 🏆",
        description="Điểm số dựa trên sự hoạt động! 🔥\n" + "—" * 15,
        color=discord.Color.from_rgb(255, 255, 0), # Màu cam cháy Gen Z
        timestamp=datetime.now()
    )

    # 🖼️ ẢNH BANNER TO (Bỏ thumbnail góc phải theo ý sếp)
    banner_url = "https://cdn.discordapp.com/attachments/1432967660139974768/1449567613054226523/fixedbulletlines.gif?ex=69586b0a&is=6957198a&hm=983179347f10af54976d073b5b567366680886de6b5e82ccf6a01bd9e4ab52b5&"
    embed.set_image(url=banner_url)

    leaderboard_text = ""
    medals = ["🔥", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for i, (uid, score) in enumerate(sorted_p):
        leaderboard_text += f"{medals[i]} <@{uid}> — **{score}** điểm\n"

    embed.add_field(name="Top 10 Chiến Thần:", value=leaderboard_text, inline=False)
    embed.set_footer(text=f"Người xem: {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="reset_leaderboard", description="Xóa sạch điểm bảng xếp hạng (Chỉ Staff)")
@app_commands.checks.has_permissions(manage_guild=True) # Chỉ ai có quyền Quản lý Server mới dùng được
async def reset_lb(interaction: discord.Interaction):
    # Lưu file trắng để reset điểm
    save_points({})
    
    print(f"🧹 {interaction.user.name} đã reset điểm.")
    await interaction.response.send_message(f"✅ Bảng xếp hạng đã được reset thành công! Bắt đầu cuộc đua mới thôi anh em! 🚀")

# Báo lỗi nếu mem thường bấm lệnh reset
@reset_lb.error
async def reset_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("⚠️ Bạn không có quyền Staff để thực hiện lệnh này!", ephemeral=True)



#===================================
# BẮN  BOSS
#===================================
BOSS_IMAGES = [
    "https://i.pinimg.com/originals/d6/de/0e/d6de0e820d43a690cd376336646bff2b.gif",
    "https://i.pinimg.com/originals/4d/4d/18/4d4d18e32a5083a3b0c557d2395fa75f.gif",
    "https://media.tenor.com/QKhVabFS_k0AAAAM/gwent-gwentcard.gif",
    "https://i.pinimg.com/originals/34/03/a6/3403a60a51c8e3cba7c78f94f41bc7f1.gif",
    "https://prodigits.co.uk/pthumbs/screensavers/down/fantasy/monster_yak7ohxw.gif",
    "https://i.pinimg.com/originals/a2/44/46/a24446e2908aef199df78b8f7b8a7ec4.gif",
    "https://media.tenor.com/el_kGdQWgF4AAAAM/darksouls.gif",
    "https://ojevensen.com/wp-content/uploads/2025/04/Dark-Souls-Sword-GIF-by-BANDAI-NAMCO-Entertainment.gif",
    "https://64.media.tumblr.com/d8883321edb0fe571e8e28dca6ee0ab5/tumblr_pp1v8exiEl1y974tlo3_500.gif",
    "https://66.media.tumblr.com/f5841e08347429d0ff99934c00d4de84/tumblr_o9wukmUoiq1unxlj8o1_500.gif",
    "https://giffiles.alphacoders.com/207/207660.gif",
    "https://c.tenor.com/uYw87Zn8CL0AAAAC/tenor.gif",
    "https://i.pinimg.com/originals/da/a3/b2/daa3b2fbafa400da43c2f093d003b34b.gif",
    "https://images.saymedia-content.com/.image/t_share/MTc4ODA1NTU5NzM3Nzg3OTAz/three-soulsbourne-bosses-that-made-me-want-to-throw-my-controller.gif",
    "https://i.pinimg.com/originals/4c/37/61/4c3761bba8e8801dc069487a2599cf19.gif",
    "https://66.media.tumblr.com/33bd64d57e323e6ca1fc02093e61a244/tumblr_ooxmkrpZYY1uutgwwo3_500.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyM2x3NXZwNHVnMDhkNzJnd2w4Zmg2NWx0OGgzczl3dTJmdDZjNDh2MCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/jqlM7zvvXy0kPJOBUw/200.gif",
    "https://giffiles.alphacoders.com/918/91844.gif",
]

RARE_BOSS_IMAGE = "https://64.media.tumblr.com/fdb2776842f9a4b2d21df70431855490/f0f3622b2d3a3ad5-a0/s540x810/1381b56ddc156239913ec253556366444caff41d.gif"

NORMAL_REWARD = 100
RARE_REWARD = 500
RARE_CHANCE = 0.1  # 10%

# ========= DATABASE =========
db = sqlite3.connect("mission.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS daily_mission (
    user_id TEXT PRIMARY KEY,
    last_date TEXT,
    pf INTEGER
)
""")
db.commit()

# ========= UTILS =========
def today():
    return datetime.date.today().isoformat()

def get_user(uid):
    cur.execute(
        "SELECT last_date, pf FROM daily_mission WHERE user_id=?",
        (uid,)
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO daily_mission VALUES (?,?,?)",
            (uid, "", 0)
        )
        db.commit()
        return "", 0
    return row

# ========= BUTTON VIEW =========
class ShootBossView(discord.ui.View):
    def __init__(self, uid, is_rare, reward):
        super().__init__(timeout=60)
        self.uid = uid
        self.is_rare = is_rare
        self.reward = reward

    @discord.ui.button(label="🔫 BẮN", style=discord.ButtonStyle.danger)
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):

        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                "❌ Đây không phải mission của bạn!",
                ephemeral=True
            )
            return

        last_date, pf = get_user(self.uid)
        d = today()

        if last_date == d:
            await interaction.response.send_message(
                "❌ Bạn đã bắn hôm nay rồi!",
                ephemeral=True
            )
            return

        win = random.choice([True, False])

        embed = interaction.message.embeds[0]

        if win:
            pf += self.reward
            embed.description = (
                "🎯 **BẠN ĐÃ HẠ GỤC BOSS!**\n\n"
                f"💰 Nhận **{self.reward} PF**"
            )
            embed.color = discord.Color.green()
        else:
            embed.description = (
                "☠️ **BOSS PHẢN CÔNG!**\n\n"
                "Bạn đã bị giết ngược..."
            )
            embed.color = discord.Color.dark_red()

        cur.execute(
            "UPDATE daily_mission SET last_date=?, pf=? WHERE user_id=?",
            (d, pf, self.uid)
        )
        db.commit()

        # khóa nút
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

# ========= EVENTS =========
@bot.event
async def on_ready():
    global synced
    if synced:
        return

    await bot.tree.sync()
    synced = True

    print("🌍 Global slash commands synced")
    print(f"🤖 Bot online: {bot.user}")

# ========= /mission =========
@bot.tree.command(name="mission", description="Bắn boss mỗi ngày (50/50)")
async def mission(interaction: discord.Interaction):

    uid = str(interaction.user.id)
    d = today()

    last_date, _ = get_user(uid)

    if last_date == d:
        await interaction.response.send_message(
            "❌ Hôm nay bạn đã dùng viên đạn rồi!",
            ephemeral=True
        )
        return

    # boss hiếm?
    if random.random() < RARE_CHANCE:
        boss_image = RARE_BOSS_IMAGE
        reward = RARE_REWARD
        title = "👑 BOSS HIẾM"
    else:
        boss_image = random.choice(BOSS_IMAGES)
        reward = NORMAL_REWARD
        title = "🐉 BOSS NGÀY"

    embed = discord.Embed(
        title=title,
        description="🔫 **Bấm nút để bắn boss!**\n⚠️ Mỗi ngày chỉ bắn 1 lần",
        color=discord.Color.red()
    )
    embed.set_image(url=boss_image)

    view = ShootBossView(uid, title == "👑 BOSS HIẾM", reward)

    await interaction.response.send_message(embed=embed, view=view)

# Chạy web keepalive + bot
if __name__ == "__main__":
    keepalive_url = keep_alive()  # giữ bot online nếu bạn dùng Render + UptimeRobot
    print(f"🌐 Keepalive server đang chạy tại: {keepalive_url}")
    bot.run(os.getenv("DISCORD_TOKEN"))




















































