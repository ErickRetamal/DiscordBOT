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
intents.messages = True  # Permite manejar mensajes
intents.presences = True  # Permite ver actividades de los usuarios
client = discord.Client(intents=intents)

watcher = LolWatcher(RIOT_API_KEY)

# Diccionario de jugadores donde se guarda el ID de Discord y el nombre de invocador de LoL
players = {}

@client.event
async def on_ready():
    print(f'Bot conectado como {client.user}')
    send_weekly_request.start()

# Tarea semanal que solicita el ID de Riot a los usuarios que aún no se han registrado
@tasks.loop(seconds=60*60*24*7)  # Corre una vez cada semana
async def send_weekly_request():
    channel = client.get_channel(1044454523726467163)  # Reemplaza con el ID de tu canal
    message = "**¡Recordatorio semanal!**\nPor favor, todos los usuarios que no hayan registrado su ID de Riot (nombre de invocador de LoL), envíenlo aquí."

    # Recorre todos los miembros del servidor y solicita el ID de Riot solo a los que no se han registrado
    for member in channel.guild.members:
        if member.id not in players:
            try:
                await channel.send(f"{member.mention}, {message}")
            except discord.errors.HTTPException as e:
                print(f"No se pudo enviar mensaje a {member.name}: {e}")
                continue  # Ignorar el error y continuar con el siguiente miembro

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Si el mensaje empieza con "!lol", registramos el nombre de invocador
    if message.content.startswith("!lol"):
        summoner_name = message.content.split(" ")[1]  # Extraer el nombre de invocador
        players[message.author.id] = summoner_name
        await message.channel.send(f"{message.author.name} ha sido registrado con el nombre de invocador {summoner_name}!")

    # Si el mensaje contiene un ID de Riot (nombre de invocador), lo registramos automáticamente
    elif message.content.startswith("!register_riot"):
        # Registra el nombre de invocador sin que el usuario tenga que especificar un comando
        summoner_name = message.content.split(" ")[1]  # Extraer el nombre de invocador
        players[message.author.id] = summoner_name
        await message.channel.send(f"{message.author.name} ha sido registrado con el nombre de invocador {summoner_name}!")

    # Enviar un mensaje con el rango de LoL
    if message.content.startswith("!rank"):
        if message.author.id not in players:
            await message.channel.send(f"{message.author.name}, no estás registrado con un nombre de invocador. Usa `!lol <nombre>` para registrarte.")
            return
        
        summoner_name = players[message.author.id]
        
        try:
            # Obtener información de LoL
            summoner = watcher.summoner.by_name('LAS', summoner_name)
            rank_info = watcher.league.by_summoner('LAS', summoner['id'])
            rank = rank_info[0]['tier'] + ' ' + rank_info[0]['rank'] if rank_info else "Sin rango"
            await message.channel.send(f"{message.author.name}, tu rango en LoL es: {rank}")
        except Exception as e:
            await message.channel.send(f"No se pudo obtener el rango para {message.author.name}. Error: {str(e)}")

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

print(f"Discord Token: {DISCORD_TOKEN}")

client.run(DISCORD_TOKEN)
