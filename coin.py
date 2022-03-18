import asyncio
from requests.exceptions import RequestException, HTTPError
from apis.coingecko import CoinGecko

import aiohttp
from apis.cmc import CoinMarketCap
from app import logger

from config import COIN_MARKET_CAP_API_KEY, HEADERS
from aiocoingecko.errors import HTTPException
from pandas import DataFrame, read_html, to_datetime


from pydantic.error_wrappers import ValidationError
import humanize
from coinmarketcapapi import CoinMarketCapAPIError

from io import BufferedReader, BytesIO
import os

from telegram import *
from telegram.ext import *
import telegram

import plotly.figure_factory as fif
import plotly.graph_objs as go
import plotly.io as pio

from popo import (
    CandleChart,
    Chart,
    Coin,
    TokenAlert
    
)


async def get_coin_ids(symbol: str) -> list:
    # getting coin ids
    #symbol - Token symbol e.g (BTC, ETH)
    # will return List of matching symbols
    coin_gecko = CoinGecko()
    coin_market_cap = CoinMarketCap()
    try:
        coin_ids = await coin_gecko.get_coin_ids(symbol=symbol)
    except (IndexError, HTTPError):
        coin_ids = coin_market_cap.get_coin_ids(symbol=symbol)
    return coin_ids




async def get_coin_stats(coin_id: str) -> dict:
    # Search CoinGecko API first
    logger.info("Getting coin stats for %s", coin_id)
    coin_gecko = CoinGecko()
    coin_stats = {}
    try:
        data = await coin_gecko.coin_lookup(ids=coin_id)

        market_data = data["market_data"]
       
     
        # Checking price of coin
        
        if market_data["current_price"]["usd"]  == None:
            price = "${:,}".format(float("0.00"))
        else:
            if float(market_data["current_price"]["usd"]) >1:
                price = "${:,}".format(float(market_data["current_price"]["usd"]))
            elif float(market_data["current_price"]["usd"]) > 0.003:
                price = "${0:,.5f}".format(float(market_data["current_price"]["usd"]))
            else:
                price = "${0:,.8f}".format(float(market_data["current_price"]["usd"]))
                
            
        #Checking all time high
        
        if market_data["ath"]["usd"]  == None:
            all_time_high = "${:,}".format(float("0.0"))
        else:
            if float(market_data["ath"]["usd"]) > 1:
                all_time_high = "${:,}".format(float(market_data["ath"]["usd"]))
            elif float(market_data["ath"]["usd"]) > 0.003:
                all_time_high = "${0:,.5f}".format(float(market_data["ath"]["usd"]))
            else:
                all_time_high = "${0:,.8f}".format(float(market_data["ath"]["usd"]))
            
        #checking market cap 
        if market_data["market_cap"]["usd"] == None:
            market_cap = "${:,}".format(float("0.0"))
        else:
            market_cap = "${:,}".format(float(market_data["market_cap"]["usd"]))
            
        # Checking 24 hours trading volume
        if market_data["total_volume"]["usd"] == None:
            volume = "${:,}".format(float("0.0"))
        else:
            volume = "${:,}".format(float(market_data["total_volume"]["usd"]))

        # Checking percentage traded within 24 hours
        if market_data["price_change_percentage_24h"] == None:
            percent_change_24h = 0
        else:
            percent_change_24h = market_data["price_change_percentage_24h"]
            
            
        #checking for 7days
        if market_data["price_change_percentage_7d"] == None:
            percent_change_7d =0
        else:
            percent_change_7d = market_data["price_change_percentage_7d"]
        
        # checking rank
        if  market_data["market_cap_rank"] == None:
            market_cap_rank = "Rank not found"
        else:
            market_cap_rank = humanize.ordinal(market_data["market_cap_rank"])

        coin_stats.update(
            {
                "name": data["name"],
                "symbol": data["symbol"].upper(),
                "price": price,
                "ath": all_time_high,
                "market_cap_rank": market_cap_rank,
                "market_cap": market_cap,
                "volume": volume,
                "percent_change_24h": percent_change_24h,
                "percent_change_7d": percent_change_7d
                
            }
        )
    except (IndexError, HTTPError, HTTPException):
        logger.info(
            "%s not found in CoinGecko. Initiated lookup on CoinMarketCap.", coin_id
        )
        ids = coin_id[0]
        coin_lookup = coin_market_cap.coin_lookup(ids=ids)
        meta_data = coin_market_cap.get_coin_metadata(ids=ids)[ids]
        data = coin_lookup[ids]
        quote = data["quote"]["USD"]
       

        for key in quote:
            if quote[key] is None:
                quote[key] = 0
        
        if quote["price"] == None:
            price = "${:,}".format(float("0.0"))      
        else:
            if float(quote['price']) >1:
                price = "${:,}".format(quote["price"])
            elif float(quote['price']) > 0.003:
                price = price = "${0:,.5f}".format(quote["price"])
            else:
                price = "${0:,.8f}".format(quote["price"])
            
        if quote["market_cap"] == None:
            market_cap = "${:,}".format(float("0.0")) 
        else:
            market_cap = "${:,}".format(quote["market_cap"])
            
        if quote["volume_24h"] == None:
            volume = "${:,}".format(float("0.0")) 
        else:
            volume = "${:,}".format(quote["volume_24h"])
            
        if quote['percent_change_24h'] == None:
            percent_change_24h = 0
        else:
            percent_change_24h = quote["percent_change_24h"]
            
        if percent_change_7d == None:
            percent_change_7d = 0
        else:
            percent_change_7d = quote["percent_change_7d"]
        
        if data["cmc_rank"] == None:
            market_cap_rank = "Rank is none"
        else:
            market_cap_rank = humanize.ordinal(data["cmc_rank"])
        coin_stats.update(
            {
                "name": data["name"],
                "symbol": data["symbol"],
                "price": price,
                "market_cap_rank": market_cap_rank,
                "market_cap": market_cap,
                "volume": volume,
                "percent_change_24h": percent_change_24h,
                "percent_change_7d": percent_change_7d
               
            }
        )
        
    
    return coin_stats

    
            



# SENDING COIN PRICE 

async def send_price(message, coin_sym) -> None:
    
   
    logger.info("Crypto command executed")
    args = coin_sym.split()

    try:
        coin = Coin(symbol=args[1].upper())
        symbol = coin.symbol
        coin_ids = await get_coin_ids(symbol=symbol)
        coin_ids_len = len(coin_ids)

        if coin_ids_len == 1:
            coin_stats = await get_coin_stats(coin_id=coin_ids[0])
            percent_change_24h = coin_stats["percent_change_24h"]
            percent_change_7d = coin_stats["percent_change_7d"]

            if "ath" in coin_stats:
             
                reply = (
                    f"*ℹ️ {coin_stats['name']} ({coin_stats['symbol']})*\n"
                    f"*📚 Price: {coin_stats['price']}*\n"
                    f"*🆙 ATH: {coin_stats['ath']}*\n\n"
                    f"`{'🔻' if percent_change_24h < 0 else '🟢'} 24H Change: {percent_change_24h}%`\n"
                    f"`{'🔻' if percent_change_7d < 0 else '🟢'} 7D Change: {percent_change_7d}%`\n\n"
                    f"*Rank: {coin_stats['market_cap_rank']}*\n"
                    f"*Cap: {coin_stats['market_cap']}*\n"
                    f"*Volume: {coin_stats['volume']}*\n"
                    
                )
            else:
                reply = (
                    f"*ℹ️ {coin_stats['name']} ({coin_stats['symbol']})*\n"
                    f"*📚 Price: {coin_stats['price']}*\n\n"
                     f"`{'🔻' if percent_change_24h > 0 else '🟢'} 24H Change: {percent_change_24h}%`\n"
                    f"`{'🔻' if percent_change_7d > 0 else '🟢'} 7D Change: {percent_change_7d}%`\n\n"
                    f"*Rank: {coin_stats['market_cap_rank']}*\n"
                    f"*Cap: {coin_stats['market_cap']}*\n"
                    f"*Volume: {coin_stats['volume']}*\n"
                   
                )
            keys = [
                           [ InlineKeyboardButton(f"Refresh", callback_data =f"refresh {coin_ids[0]}") ]
                           
                        ]
            kelo = InlineKeyboardMarkup(keys)
            message.reply_text(reply,parse_mode="markdown",reply_markup=kelo)
        elif coin_ids_len > 1:
            button_list = []
            tex = f"*select a coin*\n"
            for sym in coin_ids:
                button_list.append(InlineKeyboardButton(f"{sym}", callback_data =f"price {sym}"))
            reply_markup=InlineKeyboardMarkup(build_menu(button_list,n_cols=1))
            message.reply_text(tex,parse_mode="markdown",reply_markup=reply_markup)
        
        else:
            text="❌ Token data not found"
            message.reply_text(text)

            
    except IndexError as error:
        logger.exception(error)
        reply = f"⚠️ Please provide a crypto symbol: \n*/p* _('COIN')_"
        message.reply_text(reply,parse_mode="markdown")
        
    except ValidationError as error:
        logger.exception(error)
        error_message = error.args[0][0].exc
        reply = f"⚠️ {error_message}"
        
        #await message.reply(text=reply, parse_mode=ParseMode.MARKDOWN)

async def hey_now(coin) -> None:
    coin_stats = await get_coin_stats(coin_id=coin)
    percent_change_24h = coin_stats["percent_change_24h"]
    percent_change_7d = coin_stats["percent_change_7d"]

    if "ath" in coin_stats:
             
        reply = (
            f"*ℹ️ {coin_stats['name']} ({coin_stats['symbol']})*\n"
            f"*📚 Price: {coin_stats['price']}*\n"
            f"*🆙 ATH: {coin_stats['ath']}*\n\n"
            f"`{'🔻' if percent_change_24h < 0 else '🟢'} 24H Change: {percent_change_24h}%`\n"
            f"`{'🔻' if percent_change_7d < 0 else '🟢'} 7D Change: {percent_change_7d}%`\n\n"
            f"*Rank: {coin_stats['market_cap_rank']}*\n"
            f"*Cap: {coin_stats['market_cap']}*\n"
            f"*Volume: {coin_stats['volume']}*\n"
                    
        )
    else:
        reply = (
            f"*ℹ️ {coin_stats['name']} ({coin_stats['symbol']})*\n"
            f"*📚 Price: {coin_stats['price']}*\n\n"
            f"`{'🔻' if percent_change_24h > 0 else '🟢'} 24H Change: {percent_change_24h}%`\n"
            f"`{'🔻' if percent_change_7d > 0 else '🟢'} 7D Change: {percent_change_7d}%`\n\n"
            f"*Rank: {coin_stats['market_cap_rank']}*\n"
            f"*Cap: {coin_stats['market_cap']}*\n"
            f"*Volume: {coin_stats['volume']}*\n"
                   
        )
            
    return reply

       
def refresh(update,context) -> None:
    query : CallbackQuery = update.callback_query
    texty = update.callback_query.data  # data received from inline button user clicked
    user = update.effective_chat.id # userid of the caller
    query.answer("🟢 Fetching...")
    text = texty.split()
    
    
    if len (text) > 1:
        if text[0] == "price":
            keys = [
                           [ InlineKeyboardButton(f"Refresh", callback_data =f"refresh {text[1]}") ]
                           
                        ]
            kelo = InlineKeyboardMarkup(keys)
            getPrice = asyncio.run(hey_now(coin=text[1]))
            query.edit_message_text(getPrice,parse_mode="markdown",reply_markup=kelo)
            
        elif text[0] == "refresh":
            keys = [
                           [ InlineKeyboardButton(f"Refresh", callback_data =f"refresh {text[1]}") ]
                           
                        ]
            kelo = InlineKeyboardMarkup(keys)
            getPrice = asyncio.run(hey_now(coin=text[1]))
            query.edit_message_text(getPrice,parse_mode="markdown",reply_markup=kelo)
            
# GETTING TRENDING COIN


async def send_trending(message) -> None:
    
    logger.info("Retrieving trending addresses from CoinGecko")
    coin_gecko = CoinGecko()
    coin_market_cap = CoinMarketCap()
    coin_gecko_trending_coins = "\n".join(
        f"{coin['item']['name']} ({coin['item']['symbol']})"
        for coin in await coin_gecko.get_trending_coins()
    )

    coin_market_cap_trending_coins = "\n".join(
        await coin_market_cap.get_trending_coins()
    )

    reply = (
        f"*Trending CoinGecko 🐸*\n\n`{coin_gecko_trending_coins}`\n\n"
        f"*Trending CoinMarketCap ❄️*\n\n`{coin_market_cap_trending_coins}`"
    )

    message.reply_text(text=reply,parse_mode="markdown")    
    
    
    
#Listing new coins


async def send_latest_listings(message) -> None:
    logger.info("Retrieving latest crypto listings from CoinGecko")
    count = 5
    reply = "*CoinGecko Latest Listings_* 🐸\n"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.coingecko.com/en/coins/recently_added", headers=HEADERS
        ) as response:
            df = read_html(await response.text(), flavor="bs4")[0]

            for row in df.itertuples():
                if count == 0:
                    break

                words = row.Coin.split()
                words = sorted(set(words), key=words.index)
                words[-1] = f"({words[-1]})"

                coin = " ".join(words)
                reply += f"\n`{coin}`"
                count -= 1
        count = 5
        logger.info("Retrieving latest crypto listings from CoinMarketCap")
        reply += "\n\n*CoinMarketCap Latest Listings* ❄️\n\n"
        async with session.get(
            "https://coinmarketcap.com/new/", headers=HEADERS
        ) as response:
            df = read_html(await response.text(), flavor="bs4")[0]
            for index, row in df.iterrows():
                if count == 0:
                    break

                coin = row.Name.replace(str(index + 1), "-").split("-")
                name, symbol = coin[0], f"({coin[1]})"
                reply += f"`{name} {symbol}`\n"
                count -= 1

    message.reply_text(text=reply,parse_mode="markdown")
    
    
    
    


def build_menu(buttons,n_cols,header_buttons=None,footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu
   
        
