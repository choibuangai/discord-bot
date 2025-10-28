import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # in danh sách commands để dễ debug
    print(f"🤖 Bot đã đăng nhập thành công: {bot.user}")
    print("Loaded commands:", [c.name for c in bot.commands])

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# recommend: đặt check decorator TRƯỚC @bot.command()
@commands.has_permissions(manage_roles=True)
@bot.command()
async def addrole(ctx, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Đã thêm role **{role.name}** cho {member.mention}!")
    except discord.Forbidden:
        await ctx.send("❌ Bot không đủ quyền để thêm role này (kéo role bot lên cao hơn).")
    except Exception as e:
        await ctx.send(f"⚠️ Lỗi: {e}")

# chạy bot - KHÔNG để token công khai
import os

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))




