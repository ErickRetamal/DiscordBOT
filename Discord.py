import discord
from discord.ext import tasks, commands
from riotwatcher import LolWatcher
import os

# Configuración de API y Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')

if not DISCORD_TOKEN:
    raise ValueError("El token de Discord no está configurado. Verifica tu archivo .env.")
if not RIOT_API_KEY:
    raise ValueError("La API key de Riot no está configurada. Verifica tu archivo .env.")

intents = discord.Intents.default()
intents.members = True  # Permite acceder a los miembros del servidor
intents.messages = True  # Permite manejar mensajes
intents.presences = True  # Permite ver actividades de los usuarios

# Crear el bot con prefijo "/"
bot = commands.Bot(command_prefix='/', intents=intents)

watcher = LolWatcher(RIOT_API_KEY)

# Diccionario de jugadores donde se guarda el ID de Discord y el nombre de invocador de LoL
players = {}

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    print("Comandos slash registrados correctamente.")

# Registro de ID de Riot
@bot.slash_command(name="register_riot", description="Registra tu ID de Riot (nombre#lema) en el sistema.")
async def register_riot(ctx, riot_id: str):
    players[ctx.author.id] = riot_id
    await ctx.send(f"{ctx.author.name} ha registrado su ID de Riot: {riot_id}.")

# Ver el rango de un jugador
@bot.slash_command(name="rank", description="Muestra el rango de LoL de un jugador registrado.")
async def rank(ctx):
    if ctx.author.id not in players:
        await ctx.send(f"{ctx.author.name}, no estás registrado con un nombre de invocador. Usa `/register_riot <nombre#lema>` para registrarte.")
        return

    summoner_name = players[ctx.author.id]
    
    import requests

@bot.slash_command(name="rank", description="Muestra el rango de LoL de un jugador registrado.")
async def rank(ctx):
    if ctx.author.id not in players:
        await ctx.send(f"{ctx.author.name}, no estás registrado con un nombre de invocador. Usa `/register_riot <nombre#lema>` para registrarte.")
        return

    summoner_name = players[ctx.author.id]
    
    try:
        # Obtener información de LoL
        summoner = watcher.summoner.by_name('LAS', summoner_name)
        rank_info = watcher.league.by_summoner('LAS', summoner['id'])
        rank = rank_info[0]['tier'] + ' ' + rank_info[0]['rank'] if rank_info else "Sin rango"
        await ctx.send(f"{ctx.author.name}, tu rango en LoL es: {rank}")
    
    except requests.exceptions.RequestException as e:
        # Error relacionado con la red (problema al conectar con la API de Riot)
        await ctx.send(f"No se pudo obtener el rango para {ctx.author.name} debido a un problema de conexión con la API de Riot. Error: {str(e)}")
    
    except Exception as e:
        # Otros errores generales
        await ctx.send(f"No se pudo obtener el rango para {ctx.author.name}. Error: {str(e)}")


# Solicitar ID de Riot a los miembros una vez a la semana
@tasks.loop(seconds=60*60*24*7)  # Corre una vez cada semana
async def send_weekly_request():
    channel = bot.get_channel(1044454523726467163)  # Reemplaza con el ID de tu canal
    message = "**¡Recordatorio semanal!**\nPor favor, todos los usuarios que no hayan registrado su ID de Riot (nombre de invocador de LoL), envíenlo aquí."

    # Recorre todos los miembros del servidor y solicita el ID de Riot solo a los que no se han registrado
    for member in channel.guild.members:
        if member.id not in players:
            try:
                await channel.send(f"{member.mention}, {message}")
            except discord.errors.HTTPException as e:
                print(f"No se pudo enviar mensaje a {member.name}: {e}")
                continue  # Ignorar el error y continuar con el siguiente miembro

# Evento para manejar actualizaciones de presencia
@bot.event
async def on_presence_update(before, after):
    # Accede directamente a after.id en lugar de after.user.id
    summoner_name = players.get(after.id, None)
    if summoner_name and after.activity and after.activity.name == "League of Legends":
        try:
            game_info = watcher.spectator.by_summoner('REGIÓN', summoner_name)
            message = f"{after.name} está jugando LoL.\nDetalles: {game_info['gameMode']}, duración: {game_info['gameLength']} segundos."
            channel = bot.get_channel(1044454523726467163)
            await channel.send(message)
        except Exception as e:
            print(f"Error al obtener información de LoL: {e}")

bot.run(DISCORD_TOKEN)

