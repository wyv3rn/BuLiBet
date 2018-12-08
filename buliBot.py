#!/usr/bin/env python3

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from collections import defaultdict
import logging as log
import time
import sys
import argparse
import urllib.request
import re
import copy

log.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=log.INFO)

team_short = {
    'Frankfurt': 'EIN',
    'Düsseldorf': 'DÜS',
    'Leverkusen': 'LEV',
    'Hannover': 'H96',
    'Stuttgart': 'VfB',
    'Dortmund': 'BVB',
    'Augsburg': 'FCA',
    'Leipzig': 'RBL',
    'Wolfsburg': 'VfL',
    'Bayern': 'FCB',
    'Nürnberg': 'FCN',
    'Hoffenheim': 'TSG',
    'Schalke': 'S04',
    'Bremen': 'SVB',
    'Hertha': 'BSC',
    'Freiburg': 'SCF',
    'Gladbach': 'BMG',
    'Mainz': 'FSV'
}

user_db = defaultdict(lambda: {'matchdays': {}})

HIGHEST_INC = 2

def fetch_matchday(day):
    matchday = []

    # TODO don't hardcode
    url = 'http://www.kicker.de/news/fussball/bundesliga/spieltag/1-bundesliga/2018-19/{}/0/spieltag.html'.format(day)
    contents = urllib.request.urlopen(url).read().decode()

    teams = []
    team_regex = r'<div class="ovVrnLink2015">\r\n\r\n.*\r\n.*class=".*">(?P<{}>.*)</a>\r\n\r\n</div>\r\n'
    home_team_regex = team_regex.format('home_team')
    guest_team_regex = team_regex.format('guest_team')
    score_regex = r'<td class="alignleft nowrap".*>(?P<home_final>[0-9\-]+):(?P<guest_final>[0-9\-]+).*&nbsp;\(.*(?P<home_half>[0-9\-]+):(?P<guest_half>[0-9\-]+).*\)</td>'
    match_regex = r'{}(.*\r\n){{6}}{}(.*\r\n){{3}}{}'.format(home_team_regex, guest_team_regex, score_regex)
    log.log(log.DEBUG, 'Match regex {}'.format(match_regex))
    for result in re.finditer(match_regex, contents):
        home_team = result.group('home_team')
        guest_team = result.group('guest_team')
        home_final = result.group('home_final')
        guest_final = result.group('guest_final')
        home_half = result.group('home_half')
        guest_half = result.group('guest_half')
        log.log(log.INFO, 'Parsed match: {} {}:{} ({}:{}) {}'.format(home_team, home_final, guest_final, home_half, guest_half, guest_team))
        home_current = home_final
        if home_current == '-':
            home_current = home_half
        guest_current = guest_final
        if guest_current == '-':
            guest_current = guest_half

        home_current = home_current.replace('-', '-1')
        guest_current = guest_current.replace('-', '-1')

        home_score = int(home_current)
        guest_score = int(guest_current)

        match = Match(home_team, guest_team, home_score, guest_score)
        matchday.append(match)
    return matchday

class Match:
    def __init__(self, home, guest, home_score, guest_score):
        self.home = home
        self.guest = guest
        self.home_score = home_score
        self.guest_score = guest_score

    def to_inc_buttons(self, row, highest_inc=HIGHEST_INC):
        buttons = []
        inc = highest_inc
        while inc > 0:
            buttons.append(InlineKeyboardButton('+{}'.format(inc), callback_data='{} +{} home'.format(row, inc)))
            inc -= 1

        buttons.append(InlineKeyboardButton(team_short[self.home], callback_data='{} reset home'.format(row)))
        buttons.append(InlineKeyboardButton('{} : {}'.format(self.home_score, self.guest_score), callback_data='nop'.format(row)))
        buttons.append(InlineKeyboardButton(team_short[self.guest], callback_data='{} reset guest'.format(row)))

        while inc < highest_inc:
            inc += 1
            buttons.append(InlineKeyboardButton('+{}'.format(inc), callback_data='{} +{} guest'.format(row, inc)))
        return buttons

    def has_started(self):
        return self.home_score != -1

    def create_bet_match(self):
        bet = copy.copy(self)
        bet.home_score = 0
        bet.guest_score = 0
        return bet

    def to_string(self):
        return '{} {}:{} {}'.format(self.home, self.home_score, self.guest_score, self.guest)


def matchday_to_inc_keyboard(matchday):
    keyboard = []
    for i in range(len(matchday)):
        keyboard.append(matchday[i].to_inc_buttons(i))
    keyboard.append([InlineKeyboardButton('Done 🙈', callback_data='done')])
    return keyboard

def matchday_to_string(matchday):
    match_strings = [match.to_string() for match in matchday]
    return '\n'.join(match_strings)


def start(bot, update):
    log.log(log.INFO, 'Received start command message {}'.format(update.message))
    bot.send_message(chat_id=update.message.chat_id, text='You wanna start? But beware that I\'m in beta testing!')

def bet(bot, update, args):
    global user_db
    # TODO check args
    user_id = update.message.from_user.id
    day = int(args[0])
    matchday = fetch_matchday(day)
    betday = []
    for match in matchday:
        if not match.has_started():
            betday.append(match.create_bet_match())

    user_db[user_id]['matchdays'][day] = betday

    reply_markup = InlineKeyboardMarkup(matchday_to_inc_keyboard(betday))
    update.message.reply_text('Spieltag {}:'.format(day), reply_markup=reply_markup)

def test(bot, update, args):
    day = int(args[0])
    fetch_matchday(day)

def button(bot, update):
    global user_db
    query = update.callback_query
    username = query.from_user.username
    user_id = query.from_user.id
    msg = query.message.text
    log.log(log.INFO, 'Received button callback from user {} ({}), base message "{}"'.format(username, user_id, msg))

    # TODO might be other base messages sometimes
    day_re = re.search(r'Spieltag (?P<day>[0-9]+):', msg)
    day = int(day_re.group('day'))

    matchday = user_db[user_id]['matchdays'][day]

    if query.data == 'nop':
        return

    if query.data == 'done':
        bot.edit_message_text(chat_id=query.message.chat_id,
                        message_id=query.message.message_id,
                        text='{}\n{}'.format(msg, matchday_to_string(matchday)))
        return

    row, command, arg = query.data.split(' ')
    if arg not in ['home', 'guest']:
        log.log(log.WARNING, 'FIXME: Unexpected argument: {}'.format(arg))
        return

    match = matchday[int(row)]
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

    reply_markup = InlineKeyboardMarkup(matchday_to_inc_keyboard(matchday))

    bot.edit_message_reply_markup(chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup)


def main(token, storage):
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    log.log(log.INFO, 'Bot controller started')

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('bet', bet, pass_args=True))
    dispatcher.add_handler(CommandHandler('test', test, pass_args=True))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    log.log(log.INFO, 'Starting to poll ...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('token', help='Token for telegram bot API')
    parser.add_argument('--storage', default='db/', help='Storage directory for the databasa (default: ./db/')
    args = parser.parse_args()
    main(args.token, args.storage)

