import logging as log
import urllib.request
import re
import copy

from telegram import InlineKeyboardButton
from tinydb import TinyDB, Query

import db

HIGHEST_INC = 2  # TODO config

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
        if self.has_started():
            bet.home_score = -1
            bet.guest_score = -1
        else:
            bet.home_score = 0
            bet.guest_score = 0
        return bet

    def eval(self, other):
        if not (self.has_started() and other.has_started()):
            return 0
        if self.home_score == other.home_score and self.guest_score == other.guest_score:
            return 3

        self_rel = 0
        if self.home_score > self.guest_score:
            self_rel = 1
        elif self.home_score < self.guest_score:
            self_rel = -1
        other_rel = 0
        if other.home_score > other.guest_score:
            other_rel = 1
        elif other.home_score < other.guest_score:
            other_rel = -1

        if self_rel == other_rel:
            return 1
        else:
            return 0

    def to_string(self):
        string = '{} {}:{} {}'.format(self.home, self.home_score, self.guest_score, self.guest)
        return string.replace('-1', '-')

    def to_dict(self):
        ret = {}
        ret['home_team'] = self.home
        ret['guest_team'] = self.guest
        ret['home_score'] = self.home_score
        ret['guest_score'] = self.guest_score
        return ret


def init_match_from_dict(d):
    return Match(d['home_team'], d['guest_team'], d['home_score'], d['guest_score'])

def matchday_to_inc_keyboard(matchday):
    keyboard = []
    for i in range(len(matchday)):
        if matchday[i].home_score != -1:
            # -1 indicates that it's too late to bet
            keyboard.append(matchday[i].to_inc_buttons(i))
    keyboard.append([InlineKeyboardButton('Done 🙈', callback_data='done')])
    return keyboard

def matchday_to_string(matchday):
    match_strings = [match.to_string() for match in matchday]
    return '\n'.join(match_strings)

def matchday_to_json(matchday):
    ret = []
    for match in matchday:
        ret.append(match.to_dict())
    return ret

def betday_from_db(user_id, day):
    query = Query()
    entry = db.bet_db.search(query.user_id == user_id and query.day == day)
    if len(entry) != 1:
        log.log(log.ERROR, 'Found {} matching entries instead of 1'.format(len(entry)))
        return None
    else:
        betday_json = entry[0]['bets']
        betday = []
        for json in betday_json:
            betday.append(init_match_from_dict(json))
        return betday

def evaluate_matchday(matchday, betday):
    points = 0
    string = ''
    for i in range(len(matchday)):
        match = matchday[i]
        bet = betday[i]
        points += match.eval(bet)
        string += '{} {} {}:{} ({}:{})\n'.format(match.home, match.guest, bet.home_score, bet.guest_score, match.home_score, match.guest_score)
    string = string.replace('-1', '-')
    string += 'Summe: {} Punkte'.format(points)
    return points, string
