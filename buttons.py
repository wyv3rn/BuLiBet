import logging as log
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from tinydb import TinyDB, Query

from match import *
import db

def handle_error(bot, message, reason=None):
    text = 'Es ist ein Fehler aufgetreten.'
    if reason:
        text += ' {}'.format(reason)
    bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text=text)

def handle_done(user_id, day, betday, bot, message):
    update_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Update', callback_data='update')]])
    bot.edit_message_text(chat_id=message.chat_id,
                    message_id=message.message_id,
                    text='{}\n{}'.format(message.text, matchday_to_string(betday)),
                    reply_markup=update_markup)
    query = Query()
    db.bet_db.upsert({'user_id': user_id, 'day': day, 'bets': matchday_to_json(betday)}, query.user_id == user_id and query.day == day)


def handle_update(user_id, message, bot):
    day_re = re.search(r'Spieltag (?P<day>[0-9]+):', message.text)
    day = int(day_re.group('day'))
    matchday = fetch_matchday(day)
    betday = betday_from_db(user_id, day)
    if betday == None:
        handle_error(bot, message, '404')
        return
    points, string = evaluate_matchday(matchday, betday)
    update_text = 'Spieltag {}:\n{}'.format(day, string)
    if(update_text != message.text):
        update_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Update', callback_data='update')]])
        bot.edit_message_text(chat_id=message.chat_id,
                        message_id=message.message_id,
                        text=update_text,
                        reply_markup=update_markup)


def button(bot, update):
    query = update.callback_query
    username = query.from_user.username
    user_id = query.from_user.id
    message = query.message

    log.log(log.INFO, 'Received button callback from user {} ({}), base message "{}"'.format(username, user_id, message.text))
    if query.data == 'nop':
        return

    if query.data == 'update':
        handle_update(user_id, message, bot)
        return

    # TODO might be other base messages sometime
    day_re = re.search(r'Spieltag (?P<day>[0-9]+):', message.text)
    day = int(day_re.group('day'))

    if day not in db.betday_cache[user_id]:
        handle_error(bot, message, 'Vermutlich zu viel Zeit seit dem /bet vergangen. Bitte erneut tippen')
        return

    betday = db.betday_cache[user_id][day]

    if query.data == 'done':
        handle_done(user_id, day, betday, bot, message)
        return

    row, command, arg = query.data.split(' ')
    if arg not in ['home', 'guest']:
        log.log(log.WARNING, 'FIXME: Unexpected argument: {}'.format(arg))
        return

    match = betday[int(row)]
    if command == 'reset':
        if arg == 'home':
            if match.home_score == 0:
                return
            match.home_score = 0
        else:
            if match.guest_score == 0:
                return
            match.guest_score = 0
    else:
        inc_re = re.match(r'\+(?P<inc>\d+)', command)
        if not inc_re:
            log.log(log.WARNING, 'Unexpected command: {}'.format(command))
            return
        inc = int(inc_re.group('inc'))
        if arg == 'home':
            match.home_score += inc
        else:
            match.guest_score += inc

    reply_markup = InlineKeyboardMarkup(matchday_to_inc_keyboard(betday))

    bot.edit_message_reply_markup(chat_id=message.chat_id,
                          message_id=message.message_id,
                          reply_markup=reply_markup)

