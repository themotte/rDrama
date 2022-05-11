from json.encoder import INFINITY
import random
from .const import *

command_word = "!slots"
casino_word = "!slotsmb"
minimum_bet = 10
maximum_bet = INFINITY
payout_to_symbols = {
	2: ["👣", "🍀", "🌈", "⭐️"],
	3: ["🍎", "🔞", "⚛️", "☢️"],
	5: ["✡️", "⚔️", "🍆", "🍒"],
	12: ["🐱"]
}

def shuffle(stuff):
	random.shuffle(stuff)
	return stuff

def check_for_slots_command(in_text, from_user, from_comment):
	in_text = in_text.lower()
	if command_word in in_text:
		for word in in_text.split():
			if command_word in word:
				try:
					wager = word[len(command_word):]
					wager_value = int(wager)
				except: break

				if (wager_value < minimum_bet): break
				elif (wager_value > maximum_bet): break
				elif (wager_value > from_user.coins): break

				from_user.coins -= wager_value
				from_user.winnings -= wager_value

				payout = determine_payout()
				symbols = build_symbols(payout)
				text = build_text(wager_value, payout, from_user, "Coins")
				reward = wager_value * payout

				from_user.coins += reward
				from_user.winnings += reward

				from_comment.slots_result = f'{symbols} {text}'

	if casino_word in in_text:
		for word in in_text.split():
			if casino_word in word:
				try:
					wager = word[len(casino_word):]
					wager_value = int(wager)
				except: break

				if (wager_value < minimum_bet): break
				elif (wager_value > maximum_bet): break
				elif (wager_value > from_user.procoins): break

				from_user.procoins -= wager_value
				from_user.winnings -= wager_value

				payout = determine_payout()
				symbols = build_symbols(payout)
				text = build_text(wager_value, payout, from_user, "Marseybux")
				reward = wager_value * payout

				from_user.procoins += reward
				from_user.winnings += reward

				from_comment.slots_result = f'{symbols} {text}'


def determine_payout():
	value = random.randint(1, 100)
	if value == 100: return 12
	elif value >= 96: return 5
	elif value >= 88: return 3
	elif value >= 72: return 2
	elif value >= 61: return 1
	else: return 0

def build_symbols(for_payout):
	all_symbols = []
	
	for payout in payout_to_symbols:
		for symbol in payout_to_symbols[payout]:
			all_symbols.append(symbol)
			
	shuffle(all_symbols)
			
	if for_payout == 0:
		return "".join([all_symbols[0], all_symbols[1], all_symbols[2]])
	elif for_payout == 1:
		indices = shuffle([0, 1, 2])
		symbol_set = ["", "", ""]
		match_a = indices[0]
		match_b = indices[1]
		nonmatch = indices[2]
		matching_symbol = all_symbols[0]
		other_symbol = all_symbols[1]
		symbol_set[match_a] = matching_symbol
		symbol_set[match_b] = matching_symbol
		symbol_set[nonmatch] = other_symbol

		return "".join(symbol_set)
	else:
		relevantSymbols = shuffle(payout_to_symbols[for_payout])
		symbol = relevantSymbols[0]
		
		return "".join([symbol, symbol, symbol])

def build_text(wager_value, result, user, currency):
	if result == 0: return f'Lost {wager_value} {currency}'
	elif result == 1: return 'Broke Even'
	elif result == 12: return f'Jackpot! Won {wager_value * (result-1)} {currency}'
	else: return f'Won {wager_value * (result-1)} {currency}'
