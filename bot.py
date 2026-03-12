import discord
from discord.ext import commands
import os  # na načítanie tokenu zo środ. premennej

# Nastavenie intents – čo všetko bot môže vidieť a robiť
intents = discord.Intents.default()
intents.members = True          # aby bot videl nových členov
intents.message_content = True  # aby bot vedel čítať správy

# Vytvorenie bota s prefixom '!' a intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Event: keď sa bot prihlási a je pripravený
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')  # vypíše meno bota do terminálu

# Event: keď nový člen vstúpi na server
@bot.event
async def on_member_join(member):
    # bot hľadá kanál s názvom 'welcome'
    welcome_channel = discord.utils.get(member.guild.channels, name='welcome')
    if welcome_channel:
        await welcome_channel.send(f'Welcome to the server, {member.mention}!')  # pošle privítanie

# Príkaz: !hello – odpovie pozdravom
@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello, {ctx.author.mention}!')  # osloví užívateľa, ktorý napísal príkaz

# Príkaz: !rules – vypíše pravidlá servera
@bot.command()
async def rules(ctx):
    rules_message = (
        "Here are the server rules:\n"
        "1. Be respectful to everyone.\n"
        "2. No spamming or advertising.\n"
        "3. Follow Discord's Terms of Service."
    )
    await ctx.send(rules_message)

# Spustenie bota – načítame token z environment variable
bot.run(os.environ['DISCORD_TOKEN'])