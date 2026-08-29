import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import string
import os
from datetime import datetime

# ==================== KONFIGURACJA ====================
TOKEN = "os.getenv"
OWNER_ID = 1042355571178868847
KEYS_FILE = "keys.json"
# ======================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=4, ensure_ascii=False)

def generate_key():
    parts = []
    for _ in range(4):
        part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        parts.append(part)
    return "WICIA-" + "-".join(parts)

def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend")
    except Exception as e:
        print(e)

@bot.tree.command(name="generate", description="Generuje nowy klucz licencyjny")
@app_commands.describe(ilosc="Ile kluczy wygenerować (domyślnie 1)")
async def generate(interaction: discord.Interaction, ilosc: int = 1):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return

    if ilosc < 1 or ilosc > 20:
        await interaction.response.send_message("❌ Możesz wygenerować od 1 do 20 kluczy naraz.", ephemeral=True)
        return

    keys = load_keys()
    nowe = []

    for _ in range(ilosc):
        while True:
            key = generate_key()
            if key not in keys:
                break
        keys[key] = {
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "used": False,
            "hwid": None,
            "used_at": None
        }
        nowe.append(key)

    save_keys(keys)

    tekst = "**Wygenerowane klucze:**\n" + "\n".join(f"`{k}`" for k in nowe)
    await interaction.response.send_message(tekst, ephemeral=True)

@bot.tree.command(name="list", description="Pokazuje wszystkie klucze")
async def list_keys(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return

    keys = load_keys()
    if not keys:
        await interaction.response.send_message("Brak kluczy.", ephemeral=True)
        return

    linie = []
    for key, data in keys.items():
        status = "✅ Użyty" if data["used"] else "🟢 Wolny"
        hwid = data["hwid"] or "-"
        linie.append(f"`{key}` | {status} | HWID: `{hwid}`")

    # Discord ma limit długości wiadomości
    tekst = "\n".join(linie)
    if len(tekst) > 1900:
        tekst = tekst[:1900] + "\n... (za dużo kluczy)"

    await interaction.response.send_message(tekst, ephemeral=True)

@bot.tree.command(name="revoke", description="Blokuje klucz")
@app_commands.describe(klucz="Klucz do zablokowania")
async def revoke(interaction: discord.Interaction, klucz: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return

    keys = load_keys()
    klucz = klucz.upper().strip()

    if klucz not in keys:
        await interaction.response.send_message("❌ Taki klucz nie istnieje.", ephemeral=True)
        return

    del keys[klucz]
    save_keys(keys)
    await interaction.response.send_message(f"✅ Klucz `{klucz}` został usunięty.", ephemeral=True)

import asyncio
from fastapi import FastAPI, Header
from fastapi.middle
ware.cors import CORSMiddleware
import uvicorn@bot.tree.command(name="info", description="Informacje o kluczu")
@app_commands.describe(klucz="Klucz do sprawdzenia")
async def info(interaction: discord.Interaction, klucz: str):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return

    keys = load_keys()
    klucz = klucz.upper().strip()

    if klucz not in keys:
        await interaction.response.send_message("❌ Taki klucz nie istnieje.", ephemeral=True)
        return

    data = keys[klucz]
    status = "Użyty" if data["used"] else "Wolny"
    tekst = (
        f"**Klucz:** `{klucz}`\n"
        f"**Status:** {status}\n"
        f"**Utworzony:** {data['created']}\n"
        f"**HWID:** `{data['hwid'] or 'brak'}`\n"
        f"**Użyty:** {data['used_at'] or 'jeszcze nie'}"
    )
    await interaction.response.send_message(tekst, ephemeral=True)
# ==================== API DLA CLIENTA ====================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Wicia License API online"}

@app.post("/api/verify")
async def verify_license(payload: dict):
    key = (payload.get("key") or payload.get("license") or "").strip().upper()
    hwid = (payload.get("hwid") or payload.get("HWID") or "").strip()

    if not key or not hwid:
        return {"valid": False, "reason": "missing_fields"}

    keys = load_keys()

    if key not in keys:
        return {"valid": False, "reason": "not_found"}

    data = keys[key]

    # jeśli klucz był usunięty przez /revoke to go nie ma w pliku
    # dodatkowo możesz dodać status "revoked" jak chcesz

    if data.get("used"):
        if data.get("hwid") != hwid:
            return {"valid": False, "reason": "hwid_mismatch"}
        return {"valid": True, "reason": "ok"}

    # pierwsza aktywacja
    data["used"] = True
    data["hwid"] = hwid
    data["used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_keys(keys)

    return {"valid": True, "reason": "activated"}

# ==================== START ====================
async def start_bot():
    await bot.start(TOKEN)

async def start_api():
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(start_bot(), start_api())

if __name__ == "__main__":
    asyncio.run(main())

bot.run(TOKEN)
