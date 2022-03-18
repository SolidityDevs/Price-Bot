import logging
from pathlib import Path
from coin import *

from telegram.ext import *
from telegram import *
import telegram
from news import *
import os
from dotenv import load_dotenv
load_dotenv()
bot_api = os.getenv('bot_token')
log_folder = Path.home().joinpath("logs")
Path(log_folder).mkdir(parents=True, exist_ok=True)
log_file = log_folder.joinpath("cointend.log")

if not log_file.exists():
    open(log_file, "w").close()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler(log_file, mode="w+"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def p(update,context) -> None:
    message = update.message
    ty = asyncio.run(send_price(message=message,coin_sym=message.text))
    
def trending(update,context) -> None:
    message = update.message
    sending = asyncio.run(send_trending(message=message))
  
def listing(update,context) -> None:
    message = update.message
    sending = asyncio.run(send_latest_listings(message=message))  
    

def start(update,context) -> None:
    update.message.reply_text(f"Hello this bot is open source you can fork from https://github.com/SolidityDevs/Price-Bot.git\n\nCommands\n/p btc\n/listing\n/trending\n/news" )

def main() -> None:
    # Create the Updater and pass it your bot's token.
    
    updater = Updater(bot_api)
   
    print('started bot')
    updater.dispatcher.add_handler(CommandHandler('p', p))
    updater.dispatcher.add_handler(CommandHandler('trending', trending))
    updater.dispatcher.add_handler(CommandHandler('listing', listing))
    updater.dispatcher.add_handler(CommandHandler('news', news))
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(refresh))
    
    updater.start_polling()
    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
    
    
if __name__ == '__main__':
    main()
