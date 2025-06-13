import discord
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import json
import random
import asyncio
import datetime

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FONT_PATH = "Helvetica-Bold.ttf"
BG_IMAGE_PATH = "background.png"

ANNOUNCEMENTS = [
    "After investigation the ministry has determined it to be plausible to release 50% of the Coal from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Aluminum from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Gold from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Copper from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Iron from the reserves.",
    "In an unprecedented showing of force the native Tikitu population of Alvoria have begun to riot in the western mountains of Alvoria...",
    "A sudden drop in agricultural output has prompted the Ministry to initiate food rationing procedures.",
    "A cholera outbreak has been reported along the port cities. The Ministry urges all households to boil water and observe quarantine where applicable.",
    "Due to an unseasonably harsh winter, the Ministry has decreed a doubling of coal allocations to urban heating facilities.",
    "The Ministry has issued a temporary halt on iron exports to prioritize domestic manufacturing and infrastructure repair.",
    "Several caravans en route to the eastern territories have been reported missing. The Ministry suspects banditry and urges caution in overland travel.",
    "A fire at the Grand Munitions Depot has resulted in significant losses. Citizens are advised to avoid Northern Alvoria until further notice.",
    "Telegraph lines in Southern Alvoria have been sabotaged. Repairs are underway, but all messages should be sent by courier in the interim.",
    "A great storm has damaged coastal grain silos. Relief shipments will be organized by the Ministry within the week.",
    "The Ministry has uncovered evidence of foreign espionage within the capital. Residents are urged to report suspicious activity to the local constable.",
    "In response to increasing unrest in the capital, a dusk curfew has been temporarily enacted. Violators shall be fined and detained.",
    "A mysterious illness has taken hold in the mountain villages. Ministry medics are en route; all travel to those regions is strongly discouraged.",
]

SETTINGS_FILE = "guild_settings.json"
if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
        guild_settings = json.load(f)
else:
    guild_settings = {}

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(guild_settings, f, indent=4)

def get_guild_setting(guild_id):
    return guild_settings.get(str(guild_id), {"channel_id": None, "enabled": False, "report_channel_id": None})

def set_guild_setting(guild_id, channel_id=None, enabled=None, report_channel_id=None):
    guild_id_str = str(guild_id)
    settings = guild_settings.get(guild_id_str, {"channel_id": None, "enabled": False, "report_channel_id": None})
    if channel_id is not None:
        settings["channel_id"] = channel_id
    if enabled is not None:
        settings["enabled"] = enabled
    if report_channel_id is not None:
        settings["report_channel_id"] = report_channel_id
    guild_settings[guild_id_str] = settings
    save_settings()

def has_ministry_or_admin(ctx):
    return ctx.author.guild_permissions.administrator or discord.utils.get(ctx.author.roles, name="Ministry of the Interior") is not None

LINKED_CHANNELS_FILE = "linked_channels.json"

if os.path.exists(LINKED_CHANNELS_FILE):
    with open(LINKED_CHANNELS_FILE, "r") as f:
        linked_channels = json.load(f)
else:
    linked_channels = {}

def save_linked_channels():
    with open(LINKED_CHANNELS_FILE, "w") as f:
        json.dump(linked_channels, f, indent=4)


async def wait_until_next_monday_midnight():
    now = datetime.datetime.now(datetime.timezone.utc)
    days_ahead = (7 - now.weekday()) % 7
    next_monday = (now + datetime.timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    wait_seconds = (next_monday - now).total_seconds()
    print(f"Waiting {wait_seconds} seconds until next Monday midnight UTC...")
    await asyncio.sleep(wait_seconds)

@tasks.loop(minutes=60)
async def send_announcements():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() == 0 and now.hour == 12:
        print("Sending Monday announcements...")
        for guild in bot.guilds:
            settings = get_guild_setting(guild.id)
            if settings["enabled"] and settings["channel_id"]:
                channel = guild.get_channel(settings["channel_id"])
                if channel:
                    message = random.choice(ANNOUNCEMENTS)
                    try:
                        await channel.send(f"**# MoI:1378355766523592824 | Announcement From Ministry of Interior**\n{message}")
                    except Exception as e:
                        print(f"Failed to send announcement to {guild.name}: {e}")

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot is online as {bot.user}")
    await wait_until_next_monday_midnight()
    send_announcements.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    for group, channels in linked_channels.items():
        if message.channel.id in channels:
            for channel_id in channels:
                if channel_id != message.channel.id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send(
                                f"**[{message.guild.name}] {message.author.display_name}:** {message.content}"
                            )
                        except Exception as e:
                            print(f"Failed to send to {channel.name}: {e}")
            break  # Only match one group

    await bot.process_commands(message)

@bot.group(invoke_without_command=True)
@commands.guild_only()
async def announcement(ctx):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    settings = get_guild_setting(ctx.guild.id)
    channel_id = settings["channel_id"]
    channel_mention = f"<#{channel_id}>" if channel_id else "Not set"
    await ctx.send(f"Announcement channel: {channel_mention}\nStatus: {'Enabled' if settings['enabled'] else 'Disabled'}")

@announcement.command(name="setchannel")
@commands.guild_only()
async def setchannel(ctx, channel: discord.TextChannel):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    set_guild_setting(ctx.guild.id, channel_id=channel.id)
    await ctx.send(f"Set channel to {channel.mention}")

@announcement.command(name="enable")
@commands.guild_only()
async def enable(ctx):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    set_guild_setting(ctx.guild.id, enabled=True)
    await ctx.send("Enabled announcements.")

@announcement.command(name="disable")
@commands.guild_only()
async def disable(ctx):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    set_guild_setting(ctx.guild.id, enabled=False)
    await ctx.send("Disabled announcements.")

@bot.command()
@commands.guild_only()
async def announce_now(ctx):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    settings = get_guild_setting(ctx.guild.id)
    if not settings["channel_id"]:
        return await ctx.send("Set a channel first.")
    channel = ctx.guild.get_channel(settings["channel_id"])
    if not channel:
        return await ctx.send("Channel not found.")
    message = random.choice(ANNOUNCEMENTS)
    await channel.send(f"**# <:MoI:1378355766523592824> | Ministry of the Interior**\n{message}")
    await ctx.send("Announcement sent.")

@bot.command()
@commands.guild_only()
async def idcard(ctx, member: discord.Member = None):
    member = member or ctx.author
    if not any("citizen" in role.name.lower() for role in ctx.author.roles):
        return await ctx.send("You must be a Citizen.")
    width, height = 600, 250
    card = Image.new("RGBA", (width, height))
    try:
        bg = Image.open(BG_IMAGE_PATH).convert("RGBA").resize((width, height))
        alpha = bg.split()[3].point(lambda p: p * 0.5)
        bg.putalpha(alpha)
        card.paste(bg, (0, 0), bg)
    except Exception:
        card = Image.new("RGBA", (width, height), color=(40, 40, 60, 255))
    draw = ImageDraw.Draw(card)
    try:
        font_data = ImageFont.truetype(FONT_PATH, 20)
    except:
        font_data = ImageFont.load_default()
    title_text = "Alvoria Identification Card" if ctx.guild.id == 1345084972746408009 else f"{ctx.guild.name} Identification Card"
    try:
        font_title = ImageFont.truetype(FONT_PATH, 32)
    except:
        font_title = ImageFont.load_default()
    draw.text((30, 20), title_text, font=font_title, fill=(255, 255, 255))
    draw.text((30, 70), f"Display Name: {member.display_name}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 100), f"Username: {member.name}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 130), f"User ID: {member.id}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 160), f"Joined: {member.joined_at.strftime('%m-%d-%Y') if member.joined_at else 'N/A'}", font=font_data, fill=(255, 255, 255))
    top_role = member.top_role.name if member.top_role != ctx.guild.default_role else "None"
    draw.text((30, 190), f"Rank: {top_role}", font=font_data, fill=(255, 255, 255))
    try:
        avatar_asset = member.avatar or member.default_avatar
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((120, 120))
        mask = Image.new("L", (120, 120), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 120, 120), fill=255)
        shadow = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((5, 5, 125, 125), fill=(0, 0, 0, 150))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        card.paste(shadow, (450, 85), shadow)
        card.paste(avatar, (455, 90), mask)
    except Exception as e:
        print(f"Avatar error: {e}")
        return await ctx.send("Error loading avatar.")
    with io.BytesIO() as image_binary:
        card.save(image_binary, "PNG")
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename="id_card.png"))

@bot.command(name="setreportchannel")
@commands.guild_only()
async def set_report_channel(ctx, channel: discord.TextChannel):
    if not has_ministry_or_admin(ctx):
        return await ctx.send("You do not have permission.")
    set_guild_setting(ctx.guild.id, report_channel_id=channel.id)
    await ctx.send(f"Report channel set to {channel.mention}")

class ReportModal(Modal, title="Report a Rulebreaker"):
    report_reason = TextInput(label="What rule was broken and who broke that rule?", style=discord.TextStyle.paragraph)
    evidence = TextInput(label="Any links to the illegal message(s)?", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        report_channel_id = 1345084972821778472
        report_channel = interaction.client.get_channel(report_channel_id)
        if report_channel:
            police_role_id = 1368273752135176315  
            await report_channel.send(
                f"📣 **New Rulebreaker Report**\n"
                f"<@&{police_role_id}>\n"
                f"👤 Reporter: {interaction.user.mention}\n"
                f"📄 Reason: {self.report_reason.value}\n"
                f"📎 Evidence: {self.evidence.value or 'N/A'}"
            )
            await interaction.response.send_message("✅ Report submitted.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Report channel not found.", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def linkchannel(ctx, group_name: str):
    channel_id = ctx.channel.id
    linked_channels.setdefault(group_name, [])
    if channel_id not in linked_channels[group_name]:
        linked_channels[group_name].append(channel_id)
        save_linked_channels()
        await ctx.send(f"Channel linked to group `{group_name}`.")
    else:
        await ctx.send("This channel is already linked to that group.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlinkchannel(ctx, group_name: str):
    channel_id = ctx.channel.id
    if group_name in linked_channels and channel_id in linked_channels[group_name]:
        linked_channels[group_name].remove(channel_id)
        save_linked_channels()
        await ctx.send(f"Channel unlinked from group `{group_name}`.")
    else:
        await ctx.send("This channel is not linked to that group.")

@bot.tree.command(name="112", description="Report a rulebreaker to the staff.")
async def call_112(interaction: discord.Interaction):
    await interaction.response.send_modal(ReportModal())

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
