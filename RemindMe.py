#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@program:    RemindMe Module, to parse natural language into timedate object
@author:     Ahmed Hefnawi (@draco003)
@date:       June, 2015
@client:     Singh
@credit:     Paul McGuire for pyparsing module examples
@credit:     https://github.com/Shrugs/remind.me
"""

import re
import iso8601
from pytz import timezone
from datetime import datetime, timedelta
from pyparsing import Optional, Suppress, Word, Group, oneOf, CaselessLiteral, Combine, replaceWith
import calendar
import pyparsing


class RemindMe(object):
    """RemindMe Class"""
    # 
    def __init__(self, user_message, user_timezone):
        """RemindMe Class Initialization"""

        self.usr_msg = user_message
        self.usr_tz = timezone(user_timezone)
        self.suffix = ''

        # raw regex compilations list
        self.regexes = list()

        # remind me to (take the trash out) (tomorrow) at 5
        regex = {}
        regex['regex'] = r'^([rR]emind me to )?([\s\S]+?) ((([sS]un|[mM]on|([tT](ues|hurs))|[fF]ri)(day|\.)?|[wW]ed(\.|nesday)?|[sS]at(\.|urday)?|[tT]((ue?)|(hu?r?))\.?)( (at )?(\w+)?)?|([tT]omorrow|[tT]oday)( (at )?(\w+)?)?|(\d+|\w+) \w+ from now)$'
        regex['reminder'] = 1
        regex['time'] = 19
        regex['add'] = ''
        self.regexes.append(regex)

        # remind me to (take out the trash) in (3 hours)
        regex = {}
        regex['regex'] = r'^([rR]emind me to )?([\s\S]+?) in ([\s\S]+)$'
        regex['reminder'] = 1
        regex['time'] = 2
        regex['add'] = 'from now'
        self.regexes.append(regex)

        # (tomorrow) at (5), remind me to (take out the trash)
        regex = {}
        regex['regex'] = r'^((([sS]un|[mM]on|([tT](ues|hurs))|[fF]ri)(day|\.)?|[wW]ed(\.|nesday)?|[sS]at(\.|urday)?|[tT]((ue?)|(hu?r?))\.?)( (at )?(\w+)?)?|([Tt]omorrow|[Tt]oday)( (at )?(\w+)?)?|(\d+|\w+) \w+ from now),? (remind me to )?([\s\S]+?)$'
        regex['reminder'] = 20
        regex['time'] = 17
        regex['add'] = ''
        self.regexes.append(regex)

        # In 5 hours remind me to take out the trash
        regex = {}
        regex['regex'] = r'^[iI]n ((\d+|\w+) \w+),? (remind me to )?([\s\S]+?)$'
        regex['reminder'] = 3
        regex['time'] = 0
        regex['add'] = 'from now'
        self.regexes.append(regex)

        self.CL = CaselessLiteral

        # grammar definitions
        self.today, self.tomorrow, self.yesterday, self.noon, self.midnight, self.now = map(self.CL, "today tomorrow yesterday noon midnight now".split())
        self.plural = lambda s: Combine(self.CL(s) + Optional(self.CL("s")))
        self.week, self.day, self.hour, self.minute, self.second = map(self.plural, "week day hour minute second".split())
        self.am = self.CL("am")
        self.pm = self.CL("pm")
        self.COLON = Suppress(':')

        # are these actually operators?
        self.in_ = self.CL("in").setParseAction(replaceWith(1))
        self.from_ = self.CL("from").setParseAction(replaceWith(1))
        self.before = self.CL("before").setParseAction(replaceWith(-1))
        self.after = self.CL("after").setParseAction(replaceWith(1))
        self.ago = self.CL("ago").setParseAction(replaceWith(-1))
        self.next_ = self.CL("next").setParseAction(replaceWith(1))
        self.last_ = self.CL("last").setParseAction(replaceWith(-1))

        self.couple = (Optional(self.CL("a")) + self.CL("couple") + Optional(self.CL("of"))).setParseAction(replaceWith(2))
        self.a_qty = self.CL("a").setParseAction(replaceWith(1))
        self.integer = Word(pyparsing.nums).setParseAction(lambda t:int(t[0]))
        self.int4 = Group(Word(pyparsing.nums,exact=4).setParseAction(lambda t: [int(t[0][:2]),int(t[0][2:])] ))
        self.qty = self.integer | self.couple | self.a_qty
        self.dayName = oneOf( list(calendar.day_name) )

        self.dayOffset = (self.qty("qty") + (self.week | self.day)("timeunit"))
        self.dayFwdBack = (self.from_ + self.now.suppress() | self.ago)("dir")
        self.weekdayRef = (Optional(self.next_ | self.last_,1)("dir") + self.dayName("day"))
        self.dayRef = Optional( (self.dayOffset + (self.before | self.after | self.from_)("dir") ).setParseAction(self.convert_to_timedelta) ) + ((self.yesterday | self.today | self.tomorrow)("name") | self.weekdayRef("wkdayRef")).setParseAction(self.convert_to_day)
        self.todayRef = (self.dayOffset + self.dayFwdBack).setParseAction(self.convert_to_timedelta) | (self.in_("dir") + self.qty("qty") + self.day("timeunit")).setParseAction(self.convert_to_timedelta)
        self.dayTimeSpec = self.dayRef | self.todayRef
        self.dayTimeSpec.setParseAction(self.calculate_time)

        self.hourMinuteOrSecond = (self.hour | self.minute | self.second)

        self.timespec = Group(self.int4("miltime") | self.integer("HH") + Optional(self.COLON + self.integer("MM")) + Optional(self.COLON + self.integer("SS")) + (self.am | self.pm)("ampm"))
        self.absTimeSpec = ((self.noon | self.midnight | self.now | self.timespec("timeparts"))("timeOfDay") + Optional(self.dayRef)("dayRef"))
        self.absTimeSpec.setParseAction(self.convert_to_abs_time,self.calculate_time)

        self.relTimeSpec = self.qty("qty") + self.hourMinuteOrSecond("timeunit") + (self.from_ | self.before | self.after)("dir") + self.absTimeSpec("absTime") | self.qty("qty") + self.hourMinuteOrSecond("timeunit") + self.ago("dir") | self.in_ + self.qty("qty") + self.hourMinuteOrSecond("timeunit")
        self.relTimeSpec.setParseAction(self.convert_to_timedelta,self.calculate_time)

    # string conversion parse actions
    def convert_to_timedelta(self, toks):
        unit = toks.timeunit.lower().rstrip("s")
        td = {
            'week': timedelta(7),
            'day': timedelta(1),
            'hour': timedelta(0, 0, 0, 0, 0, 1),
            'minute': timedelta(0, 0, 0, 0, 1),
            'second': timedelta(0, 1),
            }[unit]
        if toks.qty:
            td *= int(toks.qty)
        if toks.dir:
            td *= toks.dir
        toks["timeOffset"] = td

    def convert_to_day(self, toks):
        now = self.user_tz_now()
        if "wkdayRef" in toks:
            todaynum = now.weekday()
            daynames = [n.lower() for n in calendar.day_name]
            nameddaynum = daynames.index(toks.wkdayRef.day.lower())
            if toks.wkdayRef.dir > 0:
                daydiff = (nameddaynum + 7 - todaynum) % 7
            else:
                daydiff = -((todaynum + 7 - nameddaynum) % 7)
            toks["absTime"] = datetime(now.year, now.month, now.day)+timedelta(daydiff)
        else:
            name = toks.name.lower()
            toks["absTime"] = {
                "now": now,
                "today": datetime(now.year, now.month, now.day),
                "yesterday": datetime(now.year, now.month, now.day)+timedelta(-1),
                "tomorrow": datetime(now.year, now.month, now.day)+timedelta(+1),
                }[name]

    def convert_to_abs_time(self, toks):
        now = self.user_tz_now()
        if "dayRef" in toks:
            day = toks.dayRef.absTime
            day = datetime(day.year, day.month, day.day)
        else:
            day = datetime(now.year, now.month, now.day)
        if "timeOfDay" in toks:
            if isinstance(toks.timeOfDay, basestring):
                timeOfDay = {
                    "now": timedelta(0, (now.hour * 60 + now.minute) * 60 + now.second, now.microsecond),
                    "noon": timedelta(0, 0, 0, 0, 0, 12),
                    "midnight": timedelta(),
                    }[toks.timeOfDay]
            else:
                hhmmss = toks.timeparts
                if hhmmss.miltime:
                    hh, mm = hhmmss.miltime
                    ss = 0
                else:
                    hh, mm, ss = (hhmmss.HH % 12), hhmmss.MM, hhmmss.SS
                    if not mm:
                        mm = 0
                    if not ss:
                        ss = 0
                    if toks.timeOfDay.ampm == 'pm':
                        hh += 12
                timeOfDay = timedelta(0, (hh * 60 + mm) * 60 + ss, 0)
        else:
            timeOfDay = timedelta(0, (now.hour*60+now.minute)*60+now.second, now.microsecond)
        toks["absTime"] = day + timeOfDay

    def calculate_time(self, toks):
        if toks.absTime:
            absTime = toks.absTime
        else:
            absTime = self.user_tz_now()
        if toks.timeOffset:
            absTime += toks.timeOffset
        toks["calculatedTime"] = absTime

    def test_grammar(self):
        """Test pyparsing  Time Conversion Grammar"""

        nl_time_expression = (self.absTimeSpec | self.dayTimeSpec | self.relTimeSpec)
        # test grammar
        tests = """\
        today
        tomorrow
        yesterday
        in a couple of days
        a couple of days from now
        a couple of days from today
        in a day
        3 days ago
        3 days from now
        a day ago
        now
        10 minutes ago
        10 minutes from now
        in 10 minutes
        in a minute
        in a couple of minutes
        20 seconds ago
        in 30 seconds
        20 seconds before noon
        20 seconds before noon tomorrow
        noon
        midnight
        noon tomorrow
        6am tomorrow
        0800 yesterday
        12:15 AM today
        3pm 2 days from today
        a week from today
        a week from now
        3 weeks ago
        noon next Sunday
        noon Sunday
        noon last Sunday""".splitlines()

        for t in tests:
            print t.strip(), "(relative to %s)" % self.user_tz_now()
            res = nl_time_expression.parseString(t.strip())
            if "calculatedTime" in res:
                print res.calculatedTime
            else:
                print "???"
            print

    def fuzzy_parse(self, text):
        """Fuzzy Text Parser"""

        nl_time_expression = (self.absTimeSpec | self.dayTimeSpec | self.relTimeSpec)
        # print text.strip(), "(relative to %s)" % self.user_tz_now()
        res = nl_time_expression.parseString(text.strip())
        if "calculatedTime" in res:
            return str(res.calculatedTime).strip()
        else:
            return None

    def day_suffix(self, day):
        """Get day suffix (StackOverFlow)"""
        if 4 <= day <= 20 or 24 <= day <= 30:
            self.suffix = "th"
        else:
            self.suffix = ["st", "nd", "rd"][day % 10 - 1]

    def parse_msg(self):
        """Parse user message"""
        day_names = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for regex in self.regexes:
            msg = re.findall(regex['regex'], self.usr_msg)
            # print msg
            if msg:
                for p in msg[0]:
                    if 'hour' in str(p).lower():
                        fuzzy_in = 'in ' + str(msg[0][regex['time']])
                    elif 'tomorrow' in str(p).lower():
                        fuzzy_in = str(msg[0][regex['time']]) + " tomorrow"
                    elif any(x in (str(p).lower()) for x in day_names):
                        # 5am next Monday
                        fuzzy_in = str(msg[0][15]) + " next " + str(msg[0][3])

                usr_dt = iso8601.parse_date( self.fuzzy_parse(fuzzy_in) )
                # populate day suffix
                self.day_suffix(usr_dt.day)
                return str(usr_dt), "We'll remind you to " + str(msg[0][regex['reminder']]) + " on " + usr_dt.strftime('%A the %d' + self.suffix + ' of %B at %I:%M %p')
        # otherwise None
        return None

    def utc_now(self):
        """Get GMT/UTC datetime NOW()"""
        return datetime.now(timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')

    def user_tz_now(self):
        """Get user timezone datetime NOW()"""
        return datetime.now(self.usr_tz) #.strftime('%Y-%m-%d %H:%M:%S')

    def get_client_utc(self):
        """Convert user time to GMT/UTC"""
        return self.usr_dt.astimezone(self.usr_tz).strftime('%Y-%m-%d %H:%M:%S')
