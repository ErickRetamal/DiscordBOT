import discord
from discord.ext import tasks
from riotwatcher import LolWatcher
import os


# Configuración de API y Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

if not DISCORD_TOKEN:
    raise ValueError("El token de Discord no está configurado. Verifica tu archivo .env.")
if not RIOT_API_KEY:
    raise ValueError("La API key de Riot no está configurada. Verifica tu archivo .env.")

print("Tokens cargados correctamente.")

intents = discord.Intents.default()
intents.members = True  # Permite acceder a los miembros del servidor
intents.presences = True  # Permite ver actividades de los usuarios
client = discord.Client(intents=intents)

watcher = LolWatcher(RIOT_API_KEY)

# Diccionario de jugadores donde se guarda el ID de Discord y el nombre de invocador de LoL
players = {}

@client.event
async def on_ready():
    print(f'Bot conectado como {client.user}')
    send_weekly_rank.start()

# Corre la tarea semanal (1 semana = 60 * 60 * 24 * 7 segundos)
@tasks.loop(seconds=60*60*24*7)
async def send_weekly_rank():
    channel = client.get_channel(1044454523726467163)  # Reemplaza con el ID de tu canal
    message = "**Resumen Semanal de Rangos:**\n"

    # Verificar y enviar la información de LoL solo para jugadores registrados
    for discord_id, summoner_name in players.items():
        if not summoner_name:
            continue  # Si no hay nombre de invocador, no se envía nada para ese usuario

        try:
            # Obtener información de LoL
            summoner = watcher.summoner.by_name('LAS', summoner_name)
            rank_info = watcher.league.by_summoner('LAS', summoner['id'])
            rank = rank_info[0]['tier'] + ' ' + rank_info[0]['rank'] if rank_info else "Sin rango"

            discord_user = await client.fetch_user(discord_id)
            player_name = discord_user.name  # Nombre original de Discord
            message += f"- {player_name} (LoL): {rank}\n"
        except Exception as e:
            message += f"- {discord_id} (LoL): Error al obtener datos.\n"

    # Agregar código para obtener rangos de Valorant (si es necesario) usando la API de Tracker.gg

    await channel.send(message)

@client.event
async def on_member_join(member):
    # Cuando un nuevo miembro se une, le pedimos el nombre de invocador de LoL si no está registrado
    if member.id not in players:
        await member.send("¡Bienvenido! Por favor, envía tu nombre de invocador de LoL para ser registrado en el sistema.")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith("!lol"):
        summoner_name = message.content.split(" ")[1]  # Extraer el nombre de invocador

        # Verificamos si el usuario ya está registrado, si no, lo registramos
        players[message.author.id] = summoner_name
        await message.channel.send(f"{message.author.name} ha sido registrado con el nombre de invocador {summoner_name}!")

@client.event
async def on_presence_update(before, after):
    # Actualizar la actividad de un jugador si está jugando LoL
    if after.activity and after.activity.name == "League of Legends":
        summoner_name = players.get(after.user.id, None)
        if summoner_name:
            try:
                game_info = watcher.spectator.by_summoner('REGIÓN', summoner_name)
                message = f"{after.user.name} está jugando LoL.\nDetalles: {game_info['gameMode']}, duración: {game_info['gameLength']} segundos."
                channel = client.get_channel(1044454523726467163)
                await channel.send(message)
            except Exception:
                pass

client.run(DISCORD_TOKEN)
