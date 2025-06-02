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

# Font and images
FONT_PATH = "Helvetica-Bold.ttf"  # Make sure this font file exists or change to a valid font
BG_IMAGE_PATH = "background.png"  # Make sure this image file exists

# Announcement messages
ANNOUNCEMENTS = [
    "After investigation the ministry has determined it to be plausible to release 50% of the Coal from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Aluminum from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Gold from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Copper from the reserves.",
    "After investigation the ministry has determined it to be plausible to release 50% of the Iron from the reserves.",
    "In an unprecedented showing of force the native Tikitu population of Alvoria have begun to riot in the western mountains of Alvoria due to this riot the ministry has deemed it necessary to al[...]",  # truncated for brevity
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

# ---------- Guild Settings Persistence ----------
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
    default = {"channel_id": None, "enabled": False, "report_channel_id": None}
    return guild_settings.get(str(guild_id), default)

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

# ---------- Permission Helper ----------
def has_ministry_or_admin(ctx):
    is_admin = ctx.author.guild_permissions.administrator
    has_ministry_role = discord.utils.get(ctx.author.roles, name="Ministry of the Interior") is not None
    return is_admin or has_ministry_role

# ---------- Announcement Task ----------
async def wait_until_next_monday_midnight():
    now = datetime.datetime.now(datetime.timezone.utc)
    days_ahead = 0 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = (now + datetime.timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    wait_seconds = (next_monday - now).total_seconds()
    print(f"Waiting {wait_seconds} seconds until next Monday midday UTC...")
    if wait_seconds > 0:
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
                    content = "**Announcement From Ministry of Interior**\n" + message
                    try:
                        await channel.send(content)
                    except Exception as e:
                        print(f"Failed to send announcement in guild {guild.id}: {e}")

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    await wait_until_next_monday_midnight()
    send_announcements.start()

# ---------- Announcement Commands ----------
@bot.group(invoke_without_command=True)
@commands.guild_only()
async def announcement(ctx):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    settings = get_guild_setting(ctx.guild.id)
    channel_id = settings["channel_id"]
    enabled = settings["enabled"]
    channel_mention = f"<#{channel_id}>" if channel_id else "Not set"
    status = "Enabled" if enabled else "Disabled"
    await ctx.send(f"Announcement channel: {channel_mention}\nStatus: {status}")

@announcement.command(name="setchannel")
@commands.guild_only()
async def setchannel(ctx, channel: discord.TextChannel):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    set_guild_setting(ctx.guild.id, channel_id=channel.id)
    await ctx.send(f"Announcement channel set to {channel.mention}")

@announcement.command(name="enable")
@commands.guild_only()
async def enable(ctx):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    set_guild_setting(ctx.guild.id, enabled=True)
    await ctx.send("Announcement broadcast enabled.")

@announcement.command(name="disable")
@commands.guild_only()
async def disable(ctx):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    set_guild_setting(ctx.guild.id, enabled=False)
    await ctx.send("Announcement broadcast disabled.")

# Debug command to send announcement immediately
@bot.command()
@commands.guild_only()
async def announce_now(ctx):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return

    settings = get_guild_setting(ctx.guild.id)
    if not settings["channel_id"]:
        await ctx.send("Announcement channel is not set. Use !announcement setchannel #channel.")
        return
    channel = ctx.guild.get_channel(settings["channel_id"])
    if not channel:
        await ctx.send("The saved announcement channel could not be found.")
        return

    message = random.choice(ANNOUNCEMENTS)
    content = "**# <:MoI:1378355766523592824> | Ministry of the Interior**\n" + message
    await channel.send(content)
    await ctx.send("Announcement sent!")

# ---------- Command: !idcard ----------
@bot.command()
@commands.guild_only()
async def idcard(ctx, member: discord.Member = None):
    print("idcard command called")
    member = member or ctx.author
    print(f"Member: {member}")

    # Check if the author has a role containing "Citizen"
    if not any("citizen" in role.name.lower() for role in ctx.author.roles):
        await ctx.send("You must be a Citizen to request an ID card.")
        return

    # Create ID card base
    width, height = 600, 250
    card = Image.new("RGBA", (width, height))

    # Load background image
    try:
        bg_image = Image.open(BG_IMAGE_PATH).convert("RGBA")
        bg_image = bg_image.resize((width, height), Image.LANCZOS)

        # Make the background semi-transparent
        bg_alpha = bg_image.split()[3].point(lambda p: p * 0.5)
        bg_image.putalpha(bg_alpha)

        card.paste(bg_image, (0, 0), bg_image)
    except Exception as e:
        print(f"Error loading background image: {e}")
        card = Image.new("RGBA", (width, height), color=(40, 40, 60, 255))

    draw = ImageDraw.Draw(card)

    # Load fonts
    try:
        font_data = ImageFont.truetype(FONT_PATH, 20)
    except IOError:
        font_data = ImageFont.load_default()
        await ctx.send("Custom font not found, using default.")

    # Dynamically fit server name in title (with server-specific override)
    if ctx.guild.id == 1345084972746408009:
        title_text = "Alvoria Identification Card"
        font_size = 32
        try:
            font_title = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            font_title = ImageFont.load_default()
    else:
        title_text = f"{ctx.guild.name} Identification Card"
        font_size = 32
        while True:
            try:
                font_title = ImageFont.truetype(FONT_PATH, font_size)
            except IOError:
                font_title = ImageFont.load_default()
                break
            bbox = draw.textbbox((0, 0), title_text, font=font_title)
            title_width = bbox[2] - bbox[0]
            if title_width <= 540 or font_size <= 10:
                break
            font_size -= 1

    # Text info
    draw.text((30, 20), title_text, font=font_title, fill=(255, 255, 255))
    draw.text((30, 70), f"Display Name: {member.display_name}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 100), f"Username: {member.name}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 130), f"User ID: {member.id}", font=font_data, fill=(255, 255, 255))
    draw.text((30, 160), f"Joined: {member.joined_at.strftime('%m-%d-%Y') if member.joined_at else 'N/A'}", font=font_data, fill=(255, 255, 255))

    # Top role
    top_role = member.top_role.name if member.top_role and member.top_role != ctx.guild.default_role else "None"
    draw.text((30, 190), f"Rank: {top_role}", font=font_data, fill=(255, 255, 255))

    # Load and prepare avatar
    try:
        avatar_asset = member.avatar or member.default_avatar
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((120, 120), Image.LANCZOS)

        # Circular mask
        mask = Image.new("L", (120, 120), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 120, 120), fill=255)

        # Soft shadow
        shadow = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.ellipse((5, 5, 125, 125), fill=(0, 0, 0, 150))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))

        # Paste shadow and avatar
        card.paste(shadow, (450, 85), shadow)
        card.paste(avatar, (455, 90), mask)
    except Exception as e:
        print(f"Error loading avatar: {e}")
        await ctx.send("Error loading avatar.")
        return

    # Send image
    with io.BytesIO() as image_binary:
        card.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='id_card.png'))

@bot.command(name="setreportchannel")
@commands.guild_only()
async def set_report_channel(ctx, channel: discord.TextChannel):
    if not has_ministry_or_admin(ctx):
        await ctx.send("You do not have permission to use this command.")
        return
    set_guild_setting(ctx.guild.id, report_channel_id=channel.id)
    await ctx.send(f"Report channel set to {channel.mention}")

class ReportModal(Modal, title="Report a Rulebreaker"):
    report_reason = TextInput(label="What rule was broken?", style=discord.TextStyle.paragraph)
    evidence = TextInput(label="Any evidence or extra details?", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Send to a report channel (replace with your actual channel ID)
        report_channel_id = 1345084972821778472  # ← replace this
        report_channel = interaction.client.get_channel(report_channel_id)

        if report_channel:
            await report_channel.send(
                f"📣 **New Rulebreaker Report**\n"
                f"👤 Reporter: {interaction.user.mention}\n"
                f"📄 Reason: {self.report_reason.value}\n"
                f"📎 Evidence: {self.evidence.value or 'N/A'}"
            )
            await interaction.response.send_message("✅ Report submitted to staff.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Report channel not found.", ephemeral=True)

@bot.tree.command(name="112", description="Report a rulebreaker to the staff.")
async def call_112(interaction: discord.Interaction):
    await interaction.response.send_modal(ReportModal())

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync: {e}")

# ---------- Run Bot ----------
bot.run("MTM3ODAxNzA3Mjk5NDMyMDQwNA.GwGwBo.nTb5OHZ0r_AKULHuyVECrjokcX3mjnKsh2U7QI")
