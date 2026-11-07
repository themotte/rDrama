'''
The seeded system accounts. Their ids are fixed and contract: the app refers to them by id, and production data references them.
'''
SYSTEM_ID = 1
'''Authors notification messages.'''
AUTOJANNY_ID = 2
'''Authors automated moderation messages; also the modmail recipient.'''
MODMAIL_ID = AUTOJANNY_ID
'''The recipient of messages to the admins (modmail): the same account as AutoJanny.'''

# Ids 3-8 are reserved for retired system accounts: production still has their rows, and they are protected like the accounts above.
