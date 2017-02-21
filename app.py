#!/usr/bin/env python

import os
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import re
import json

from flask import (
	Flask,
	request,
	make_response,
	jsonify
)

app = Flask(__name__)
log = app.logger

def parameters_extractor(params):
	dicts = [params]
	values = []

	while len(dicts):
		d = dicts.pop()

		for value in d.values():
			if isinstance(value, dict):
				dicts.append(value)
			elif isinstance(value, basestring) and len(value) > 0:
				values.append(unicode(value))

	return values

def gsheets_auth():
	print 'auth in progress'
	with open('account.json', 'r') as data_file:
		json_key = json.loads(data_file.read())
	scope = ['https://spreadsheets.google.com/feeds']
	credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)
	gc = gspread.authorize(credentials)
	sh = gc.open_by_key('1MI5C__3it4KgMVK6I8fZMa0Y3QQBg5lI_dcjkTqMZS4')
	return sh

def sheets_get(spreadsheet):
	shopping_list = spreadsheet.worksheet("Shopping List")
	return shopping_list

sh = gsheets_auth()

@app.route('/webhook', methods=['POST'])
def webhook():
	req = request.get_json(silent=True, force=True)

	try:
		action = req.get("result").get('action')
	except AttributeError:
		return "No action, sorry."

	if action == 'shopping.add':
		res = shopping_add(req)
	# elif action == 'shopping.update':
	# 	res = shopping_update(req)
	elif action == 'shopping.sub':
		res = shopping_sub(req)
	elif action == 'shopping.search':
		res = shopping_search(req)
	else:
		log.error("Unexpeted action.")
		res = ''

	return make_response(jsonify(res))

def shopping_search(req):

	shopping_list = sheets_get(sh)

	db_products_list = shopping_list.get_all_values()[1:]
	response = 'You told me that you need '
	for product in db_products_list:
		product_cell = product[0]
		product_amount = product[1]
		if not product_amount:
			product_amount = 0
		response += '%s of %s, ' % (product_amount, product_cell)
	response = re.sub(',\s$', '.', response)

	return {
		"speech": response,
		"displayText": response
	}

# def shopping_add(req):
#
# 	shopping_list = sheets_get(sh)
# 	parameters = req['result']['parameters']
# 	context = req['result']['contexts']
# 	action = req['result']['action']
#
# 	product = parameters.get('product')
# 	quantity = int(parameters.get('quantity'))
#
# 	try:
# 		product_cell = shopping_list.find(product)
# 		product_amount = shopping_list.cell(product_cell.row, product_cell.col + 1).value
# 		if not product_amount:
# 			product_amount = 0
# 		shopping_list.update_cell(product_cell.row, product_cell.col + 1, int(product_amount) + quantity)
# 		response = 'Okay, i\'ve added %s of %s to your shopping list.' % (quantity, product)
# 	except CellNotFound:
# 		response = 'Not found'
#
# 	return {
# 		"speech": response,
# 		"displayText": response
# 	}

# def shopping_update(req):
#
# 	shopping_list = sheets_get(sh)
# 	parameters = req['result']['parameters']
# 	context = req['result']['contexts']
# 	action = req['result']['action']
#
# 	product = parameters.get('product')
# 	quantity = int(parameters.get('quantity'))
#
# 	try:
# 		product_cell = shopping_list.find(product)
# 		product_amount = shopping_list.cell(product_cell.row, product_cell.col + 1).value
# 		if not product_amount:
# 			product_amount = 0
# 		shopping_list.update_cell(product_cell.row, product_cell.col + 1, quantity)
# 		response = 'You got it. Updating your entry to %s of %s.' % (quantity, product)
# 	except CellNotFound:
# 		response = 'Not found'
#
# 	return {
# 		"speech": response,
# 		"displayText": response
# 	}

def shopping_add(req):

	shopping_list = sheets_get(sh)
	parameters = req['result']['parameters']
	context = req['result']['contexts']

	product = parameters.get('product')
	quantity = int(parameters.get('quantity'))

	db_values = shopping_list.get_all_values()
	db_product_list = [item[0].lower() for item in db_values[1:]]

	if product in db_product_list:
		product_row = db_product_list.index(product) + 1
		product_q = int(db_values[product_row][1])
		shopping_list.update_cell(product_row + 1, 2, product_q+quantity)
		response = 'You got it. Updating your entry to %s of %s.' % (quantity, product)
	else:
		row = len(db_product_list) + 2
		cell_list_key_a = shopping_list.range('A' + str(row) + ':B' + str(row))
		cell_list_key_a[0].value = product.capitalize()
		cell_list_key_a[1].value = quantity
		shopping_list.update_cells(cell_list_key_a)
		response = 'Okay, i\'ve added %s of %s to your shopping list.' % (quantity, product)

	return {
		"speech": response,
		"displayText": response
	}

def shopping_sub(req):

	shopping_list = sheets_get(sh)
	parameters = req['result']['parameters']
	context = req['result']['contexts']

	product = parameters.get('product')
	quantity = int(parameters.get('quantity'))

	db_values = shopping_list.get_all_values()
	db_product_list = [item[0].lower() for item in db_values[1:]]

	if product in db_product_list:
		product_row = db_product_list.index(product) + 1
		product_q = int(db_values[product_row][1])
		if product_q > quantity:
			shopping_list.update_cell(product_row + 1, 2, product_q-quantity)
			response = 'You got it. Updating your entry to %s of %s.' % (quantity, product)
		else:
			shopping_list.update_cell(product_row + 1, 2, 0)
			response = 'Great job! I\'ve updated your shopping list.'

	return {
		"speech": response,
		"displayText": response
	}


@app.route('/test', methods=['GET'])
def test():
	return 'shopping Test is done!'


if __name__ == '__main__':
	port = int(os.getenv('PORT', 5000))

	app.run(
		debug=True,
		port=port,
		host='0.0.0.0'
	)