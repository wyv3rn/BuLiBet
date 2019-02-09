import logging as log

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from tinydb import TinyDB, Query

from match import *
import db

def start(bot, update):
    log.log(log.INFO, 'Received start command message {}'.format(update.message))
    bot.send_message(chat_id=update.message.chat_id, text='You wanna start? But beware that I\'m in beta testing!')

def bet(bot, update, args):
    if len(args) != 1:
        update.message.reply_text('Benutzung: \\bet [day], z.B. \\bet 13')

    # TODO support updating the bet even after some matches have started
    user_id = update.message.from_user.id
    day = int(args[0])
    matchday = fetch_matchday(day)
    betday = []
    for match in matchday:
        betday.append(match.create_bet_match())

    user = db.user_db.search(Query().user_id == user_id)
    if len(user) == 0:
        log.log(log.INFO, 'Inserting new user with id {} and username {}'.format(user_id, update.message.from_user.username))
        db.user_db.insert({'user_id': user_id, 'bootstrap_points': 0})

    db.betday_cache[user_id][day] = betday
    reply_markup = InlineKeyboardMarkup(matchday_to_inc_keyboard(betday))
    update.message.reply_text('Spieltag {}:'.format(day), reply_markup=reply_markup)

