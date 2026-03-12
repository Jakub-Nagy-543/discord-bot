import discord
from discord.ext import commands
from discord import app_commands
import os

# Nastavenie intents – čo bot môže vidieť a robiť
intents = discord.Intents.default()
intents.members = True          # bot vidí nových členov
intents.message_content = True  # bot môže čítať správy

# Vytvorenie bota bez prefixu (slash commands)
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=None, intents=intents)
        self.tree = app_commands.CommandTree(self)

bot = MyBot()

# Event: keď je bot pripravený
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()  # synchronizuje slash commands

# Event: keď nový člen vstúpi na server
@bot.event
async def on_member_join(member):
    welcome_channel = discord.utils.get(member.guild.channels, name='welcome')
    if welcome_channel:
        await welcome_channel.send(f'Welcome to the server, {member.mention}!')

# Slash command: /hello
@bot.tree.command(name="hello", description="Pozdraví užívateľa")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hello, {interaction.user.mention}!')

# Slash command: /rules
@bot.tree.command(name="rules", description="Zobrazí pravidlá servera")
async def rules(interaction: discord.Interaction):
    rules_message = (
        "Here are the server rules:\n"
        "1. Be respectful to everyone.\n"
        "2. No spamming or advertising.\n"
        "3. Follow Discord's Terms of Service."
    )
    await interaction.response.send_message(rules_message)

# Slash command: /ping – kontrola online
@bot.tree.command(name="ping", description="Zistí, či je bot online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latencia: {round(bot.latency*1000)}ms")

# Slash command: /info – info o bota
@bot.tree.command(name="info", description="Zobrazí info o bota")
async def info(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Bot: {bot.user.name}\nID: {bot.user.id}\nServerov: {len(bot.guilds)}"
    )

# Spustenie bota s tokenom z environment variable
bot.run(os.environ['DISCORD_TOKEN'])
