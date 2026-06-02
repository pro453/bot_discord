import discord
from discord.ext import commands
from groq import AsyncGroq
import asyncio
import re
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

memory = {}

def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def clean_mention(text: str) -> str:
    return re.sub(r"<@!?\d+>", "", text).strip()

async def ask_groq(user_id: str, content: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là một người bạn thân thiện trên Discord. "
                "Luôn trả lời bằng tiếng Việt tự nhiên, ngắn gọn và vui vẻ. "
                "Không được lặp lại câu trả lời cũ. "
                "Chỉ trả lời dựa trên tin nhắn mới nhất của người dùng."
            )
        }
    ]

    # Chỉ lấy 6 tin nhắn gần nhất để tránh lặp
    for msg in memory.get(user_id, [])[-6:]:
        messages.append(msg)

    messages.append({"role": "user", "content": content})

    response = await groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )

    return strip_thinking(response.choices[0].message.content)

@bot.event
async def on_ready():
    print(f"✅ Đăng nhập thành công: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Chỉ phản hồi khi DM hoặc được mention
    if (
        not isinstance(message.channel, discord.DMChannel)
        and bot.user not in message.mentions
    ):
        await bot.process_commands(message)
        return

    user_id = str(message.author.id)
    if user_id not in memory:
        memory[user_id] = []

    clean_content = clean_mention(message.content)
    if not clean_content:
        return

    async with message.channel.typing():
        try:
            answer = await ask_groq(user_id, clean_content)

            # Lưu vào memory
            memory[user_id].append({"role": "user", "content": clean_content})
            memory[user_id].append({"role": "assistant", "content": answer})

            # Giới hạn 2000 ký tự Discord
            if len(answer) > 2000:
                answer = answer[:1997] + "..."

            await message.reply(answer)

        except Exception as e:
            await message.reply(f"❌ Lỗi: {e}")

    await bot.process_commands(message)

@bot.command()
async def reset(ctx):
    user_id = str(ctx.author.id)
    memory[user_id] = []
    await ctx.reply("🗑️ Đã xóa lịch sử chat!")

bot.run(DISCORD_TOKEN)