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
bot = discord.Bot(intents=intents)

watcher = LolWatcher(RIOT_API_KEY)

# Diccionario de jugadores donde se guarda el ID de Discord y el nombre de invocador de LoL
players = {}

@bot.event
async def on_ready():
    try:
        await bot.sync_commands()  # Sincroniza los comandos slash
        print(f'Bot conectado como {bot.user}. Comandos slash sincronizados.')
    except Exception as e:
        print(f'Error al sincronizar los comandos slash: {e}')

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
    
    try:
        # Obtener información de LoL
        summoner = watcher.summoner.by_name('LA2', summoner_name)
        rank_info = watcher.league.by_summoner('LA2', summoner['id'])
        rank = rank_info[0]['tier'] + ' ' + rank_info[0]['rank'] if rank_info else "Sin rango"
        await ctx.send(f"{ctx.author.name}, tu rango en LoL es: {rank}")
    
    except Exception as e:
        await ctx.send(f"No se pudo obtener el rango para {ctx.author.name}. Error: {str(e)}")

# Solicitar ID de Riot a los miembros una vez a la semana
@tasks.loop(seconds=60*60*24*7)  # Corre una vez cada semana
async def send_weekly_request():
    channel = bot.get_channel(1044454523726467163)  # Reemplaza con el ID de tu canal
    if not channel:
        print("El canal no fue encontrado o el ID es incorrecto.")
        return

    message = "**¡Recordatorio semanal!**\nPor favor, todos los usuarios que no hayan registrado su ID de Riot (nombre de invocador de LoL), envíenlo aquí."
    for member in channel.guild.members:
        if member.id not in players:
            try:
                await channel.send(f"{member.mention}, {message}")
            except discord.errors.HTTPException as e:
                print(f"No se pudo enviar mensaje a {member.name}: {e}")

bot.run(DISCORD_TOKEN)

