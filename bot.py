import os
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

# Nastavenie intents
intents = discord.Intents.default()
intents.members = True          # bot vidi novych clenov
intents.message_content = False # nepotrebne pre slash commands

BOT_VERSION = "1.1.0"


def format_uptime(start_time: datetime) -> str:
    delta = datetime.now(timezone.utc) - start_time
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    return f"{hours}h {minutes}m {seconds}s"


async def safe_reply(interaction: discord.Interaction, message: str, ephemeral: bool = False):
    """Send an interaction response safely, even if a prior response already exists."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(message, ephemeral=ephemeral)
    except discord.Forbidden:
        # Usually means missing permission to respond in the current context.
        print("Cannot send interaction response: missing permissions.")
    except discord.HTTPException as e:
        print(f"Failed to send interaction response: {e}")


def parse_duration_to_seconds(raw: str) -> Optional[int]:
    """Parse values like 10s, 5m, 2h, 1d into seconds."""
    match = re.fullmatch(r"\s*(\d+)\s*([smhdSMHD])\s*", raw)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2).lower()
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    seconds = value * multiplier

    # Keep reminders reasonable for beginner/small-server usage.
    if seconds <= 0 or seconds > 604800:
        return None
    return seconds

# Vytvorenie bota bez prefixu (slash commands)
class MyBot(commands.Bot):
    def __init__(self):
        # Prefix commandy nepouzivame, ale Bot potrebuje validny prefix handler.
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self):
        # Sync raz pri starte (nie pri kazdom reconnecte).
        try:
            await self.tree.sync()
            print("Slash commands synced!")
        except Exception as e:
            print(f"Chyba pri sync slash commands: {e}")

bot = MyBot()

# Event: bot pripravený
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Event: nový člen
@bot.event
async def on_member_join(member):
    try:
        welcome_channel = discord.utils.get(member.guild.text_channels, name='welcome')
        if welcome_channel is None:
            return

        bot_member = member.guild.me
        if bot_member and not welcome_channel.permissions_for(bot_member).send_messages:
            return

        await welcome_channel.send(f'Welcome to the server, {member.mention}!')
    except discord.Forbidden:
        print("Missing permissions to send welcome message.")
    except discord.HTTPException as e:
        print(f"Discord HTTP error while welcoming member: {e}")
    except Exception as e:
        print(f"Chyba pri privitani clena: {e}")

# Slash command: /hello
@bot.tree.command(name="hello", description="Pozdraví užívateľa")
async def hello(interaction: discord.Interaction):
    await safe_reply(interaction, f'Hello, {interaction.user.mention}!')

# Slash command: /rules
@bot.tree.command(name="rules", description="Zobrazí pravidlá servera")
async def rules(interaction: discord.Interaction):
    rules_message = (
        "Here are the server rules:\n"
        "1. Be respectful to everyone.\n"
        "2. No spamming or advertising.\n"
        "3. Follow Discord's Terms of Service."
    )
    await safe_reply(interaction, rules_message)

# Slash command: /ping
@bot.tree.command(name="ping", description="Zistí, či je bot online")
async def ping(interaction: discord.Interaction):
    await safe_reply(interaction, f"Pong! Latencia: {round(bot.latency*1000)}ms")

# Slash command: /info
@bot.tree.command(name="info", description="Zobrazí info o bota")
async def info(interaction: discord.Interaction):
    if bot.user is None:
        await safe_reply(interaction, "Bot este nie je pripraveny.", ephemeral=True)
        return

    await safe_reply(
        interaction,
        f"Bot: {bot.user.name}\nID: {bot.user.id}\nServerov: {len(bot.guilds)}"
    )

# Slash command: /server
@bot.tree.command(name="server", description="Zobrazi zakladne info o serveri")
async def server(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    await safe_reply(
        interaction,
        f"Nazov: {guild.name}\n"
        f"ID: {guild.id}\n"
        f"Clenov: {guild.member_count}"
    )

# Slash command: /avatar
@bot.tree.command(name="avatar", description="Zobrazi avatar pouzivatela")
@app_commands.describe(user="Pouzivatel, ktoreho avatar sa ma zobrazit")
async def avatar(interaction: discord.Interaction, user: discord.Member | None = None):
    target = user or interaction.user
    await safe_reply(interaction, f"Avatar {target.mention}: {target.display_avatar.url}")

# Slash command: /uptime
@bot.tree.command(name="uptime", description="Ako dlho je bot online")
async def uptime(interaction: discord.Interaction):
    await safe_reply(interaction, f"Uptime: {format_uptime(bot.start_time)}")


# Slash command: /userinfo
@bot.tree.command(name="userinfo", description="Zobrazi informacie o pouzivatelovi")
@app_commands.describe(user="Pouzivatel, o ktorom chces info")
async def userinfo(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if interaction.guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    member = user or interaction.user
    if not isinstance(member, discord.Member):
        await safe_reply(interaction, "Nepodarilo sa nacitat informacie o pouzivatelovi.", ephemeral=True)
        return

    joined_at = member.joined_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if member.joined_at else "Unknown"
    created_at = member.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "No special roles"

    await safe_reply(
        interaction,
        f"User: {member.mention}\n"
        f"Name: {member}\n"
        f"ID: {member.id}\n"
        f"Account created: {created_at}\n"
        f"Joined server: {joined_at}\n"
        f"Roles: {roles_text}\n"
        f"Avatar: {member.display_avatar.url}"
    )


# Slash command: /roles
@bot.tree.command(name="roles", description="Zobrazi role pouzivatela")
@app_commands.describe(user="Pouzivatel, ktoreho role sa maju zobrazit")
async def roles(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    if interaction.guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    member = user or interaction.user
    if not isinstance(member, discord.Member):
        await safe_reply(interaction, "Nepodarilo sa nacitat role pouzivatela.", ephemeral=True)
        return

    role_list = [role.mention for role in member.roles if role.name != "@everyone"]
    role_text = ", ".join(role_list) if role_list else "No special roles"
    await safe_reply(interaction, f"Role pre {member.mention}: {role_text}")


# Slash command: /servericon
@bot.tree.command(name="servericon", description="Zobrazi ikonu servera")
async def servericon(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    if guild.icon is None:
        await safe_reply(interaction, "Tento server nema nastavenu ikonu.")
        return

    await safe_reply(interaction, f"Ikona servera {guild.name}: {guild.icon.url}")


# Slash command: /botinfo
@bot.tree.command(name="botinfo", description="Zobrazi technicke info o botovi")
async def botinfo(interaction: discord.Interaction):
    if bot.user is None:
        await safe_reply(interaction, "Bot este nie je pripraveny.", ephemeral=True)
        return

    await safe_reply(
        interaction,
        f"Bot: {bot.user.name}\n"
        f"Version: {BOT_VERSION}\n"
        f"Uptime: {format_uptime(bot.start_time)}\n"
        f"Serverov: {len(bot.guilds)}"
    )


# Slash command: /help
@bot.tree.command(name="help", description="Zobrazi zoznam dostupnych slash prikazov")
async def help_command(interaction: discord.Interaction):
    commands_list = sorted(bot.tree.get_commands(), key=lambda c: c.name)
    lines = ["Dostupne prikazy:"]
    for cmd in commands_list:
        lines.append(f"/{cmd.name} - {cmd.description}")

    message = "\n".join(lines)
    # Keep response within Discord limit.
    if len(message) > 1900:
        message = message[:1897] + "..."

    await safe_reply(interaction, message, ephemeral=True)


# Slash command: /remind
@bot.tree.command(name="remind", description="Nastavi pripomienku po zadanom case")
@app_commands.describe(
    time="Cas v tvare 10s, 5m, 2h alebo 1d",
    message="Text pripomienky"
)
async def remind(interaction: discord.Interaction, time: str, message: str):
    seconds = parse_duration_to_seconds(time)
    if seconds is None:
        await safe_reply(
            interaction,
            "Neplatny cas. Pouzi format napr. 10s, 5m, 2h, 1d (max 7d).",
            ephemeral=True,
        )
        return

    await safe_reply(
        interaction,
        f"Pripomienka nastavena za {time.strip().lower()}.",
        ephemeral=True,
    )

    await asyncio.sleep(seconds)
    channel = interaction.channel
    if channel is None:
        return

    try:
        await channel.send(f"{interaction.user.mention} pripomienka: {message}")
    except discord.Forbidden:
        print("Missing permissions to send reminder message.")
    except discord.HTTPException as e:
        print(f"Discord HTTP error while sending reminder: {e}")


# Slash command: /poll
@bot.tree.command(name="poll", description="Vytvori jednoduchu anketu s dvomi moznostami")
@app_commands.describe(question="Otazka", option1="Prva moznost", option2="Druha moznost")
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str):
    poll_text = (
        f"**{question}**\n"
        f"1️⃣ {option1}\n"
        f"2️⃣ {option2}"
    )

    try:
        await safe_reply(interaction, poll_text)
        poll_message = await interaction.original_response()
        await poll_message.add_reaction("1️⃣")
        await poll_message.add_reaction("2️⃣")
    except discord.Forbidden:
        await safe_reply(
            interaction,
            "Bot nema povolenie posielat spravy alebo pridavat reakcie.",
            ephemeral=True,
        )
    except discord.HTTPException as e:
        print(f"Discord HTTP error while creating poll: {e}")
        await safe_reply(interaction, "Anketu sa nepodarilo vytvorit.", ephemeral=True)


# Slash command: /serverstats
@bot.tree.command(name="serverstats", description="Zobrazi zakladne statistiky servera")
async def serverstats(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    total_members = guild.member_count or 0
    online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)

    await safe_reply(
        interaction,
        f"Server stats pre {guild.name}:\n"
        f"Clenov: {total_members}\n"
        f"Online: {online_members}\n"
        f"Text channels: {text_channels}\n"
        f"Voice channels: {voice_channels}"
    )


# Slash command: /moderate
@bot.tree.command(name="moderate", description="Zakladna moderacia: kick alebo ban")
@app_commands.describe(action="Typ akcie", user="Pouzivatel na moderovanie")
@app_commands.choices(
    action=[
        app_commands.Choice(name="kick", value="kick"),
        app_commands.Choice(name="ban", value="ban"),
    ]
)
async def moderate(interaction: discord.Interaction, action: app_commands.Choice[str], user: discord.Member):
    guild = interaction.guild
    if guild is None:
        await safe_reply(interaction, "Tento prikaz funguje len na serveri.", ephemeral=True)
        return

    if not isinstance(interaction.user, discord.Member):
        await safe_reply(interaction, "Nepodarilo sa overit tvoje opravnenia.", ephemeral=True)
        return

    if action.value == "kick" and not interaction.user.guild_permissions.kick_members:
        await safe_reply(interaction, "Nemáš oprávnenie kickovať členov.", ephemeral=True)
        return
    if action.value == "ban" and not interaction.user.guild_permissions.ban_members:
        await safe_reply(interaction, "Nemáš oprávnenie banovať členov.", ephemeral=True)
        return

    me = guild.me
    if me is None:
        await safe_reply(interaction, "Nepodarilo sa zistit opravnenia bota.", ephemeral=True)
        return

    if action.value == "kick" and not me.guild_permissions.kick_members:
        await safe_reply(interaction, "Bot nema povolenie kick_members.", ephemeral=True)
        return
    if action.value == "ban" and not me.guild_permissions.ban_members:
        await safe_reply(interaction, "Bot nema povolenie ban_members.", ephemeral=True)
        return

    if user == interaction.user:
        await safe_reply(interaction, "Nemozes moderovat sam seba.", ephemeral=True)
        return
    if user == guild.owner:
        await safe_reply(interaction, "Nie je mozne moderovat ownera servera.", ephemeral=True)
        return

    try:
        if action.value == "kick":
            await user.kick(reason=f"Moderated by {interaction.user}")
            await safe_reply(interaction, f"Pouzivatel {user} bol kicknuty.")
        else:
            await user.ban(reason=f"Moderated by {interaction.user}")
            await safe_reply(interaction, f"Pouzivatel {user} bol banovany.")
    except discord.Forbidden:
        await safe_reply(interaction, "Akciu sa nepodarilo vykonat (hierarchia alebo povolenia).", ephemeral=True)
    except discord.HTTPException as e:
        print(f"Discord HTTP error while moderating user: {e}")
        await safe_reply(interaction, "Akciu sa nepodarilo vykonat.", ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"Slash command error: {error}")
    if isinstance(error, app_commands.MissingPermissions):
        await safe_reply(interaction, "Na tento prikaz nemas potrebne povolenia.", ephemeral=True)
        return

    if isinstance(error, app_commands.BotMissingPermissions):
        await safe_reply(interaction, "Bot nema potrebne povolenia na vykonanie prikazu.", ephemeral=True)
        return

    await safe_reply(interaction, "Nastala chyba pri vykonavani prikazu.", ephemeral=True)

# Spustenie bota s tokenom z environment variable
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise RuntimeError("DISCORD_TOKEN nie je nastaveny v environment variables.")

bot.run(token)
