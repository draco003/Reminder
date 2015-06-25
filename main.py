#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@program: RemindMe test cases
@author: Ahmed Hefnawi (@draco003)
@date: June, 2015
@client: Singh
"""

from RemindMe import RemindMe

msgs = list()
msgs.append('Tomorrow at 3pm, remind me to take out the trash')
msgs.append('Remind me to take out the trash in 3 hours')
msgs.append('Remind me to take the trash out tomorrow at 5am')
msgs.append('In 5 hours remind me to take out the trash')
msgs.append('Remind me to take the trash out next Monday at 5am')

for msg in msgs: 
    reminder = RemindMe(str(msg), 'UTC')
    print reminder.parse_msg()
    