	# -*- coding: utf-8 -*-
# Copyright (c) 2017, sathishpy@gmail.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CMBoxDescription(Document):
	def autoname(self):
		items = frappe.db.sql_list("""select name from `tabCM Box Description` where item=%s""", self.item)
		if items:
			idx = len(items) + 1
		else:
			idx = 1
		self.name = self.item + "-DESC" + ('-%.3i' % idx)

	def add_paper_item(self, layer):
		colour = "Brown"
		if "White" in self.item_top_type and layer == "Top":
			colour = 'White'

		rm_item = frappe.new_doc("CM Paper Item")
		rm_item.rm_type = layer
		papers = get_layer_papers(self.sheet_length, self.sheet_width, colour)
		if (len(papers) > 0):
			print "Assigning paper {0} for {1}".format(papers[0], layer)
			paper, deck = papers[0]
			rm_item.rm = paper
		self.append("item_papers", rm_item)

	def populate_paper_materials(self):
		self.sheet_length = 2 * (self.item_width + self.item_length) + self.item_pin_lap
		self.sheet_width = self.item_per_sheet * (self.item_width + self.item_height + self.item_fold_lap)

		count, self.item_papers = 1, []
		self.add_paper_item("Top")
		while count < int(self.item_ply_count):
			self.add_paper_item("Flute")
			self.add_paper_item("Liner")
			count += 2

	def populate_misc_materials(self, rm_type, percent):
		rm_item = frappe.new_doc("CM Misc Item")
		rm_item.rm_type = rm_type
		rm_item.rm_percent = percent
		self.append("item_others", rm_item)

	def populate_raw_materials(self):
		self.populate_paper_materials()

		self.item_others = []
		for (rm_type, percent) in [("Corrugation Gum", 3), ("Pasting Gum", 2), ("Printing Ink", 0.3)]:
			self.populate_misc_materials(rm_type, percent)

	def validate(self):
		if (int(self.item_ply_count) != len(self.item_papers)):
			frappe.trow("Not all box layers added as paper items")

		expected_type = "Top"
		for paper in self.item_papers:
			if (paper.rm_type != expected_type):
				frappe.throw("Paper Type in Item description should follow the order Top, Flute and Liner")
			if (paper.rm_type == "Top" or paper.rm_type == "Liner"):
				expected_type = "Flute"
			else:
				expected_type = "Liner"

	def get_paper_weight_cost(self, paper):
		if paper is None: return (0, 0)
		(gsm, bf, deck) = get_paper_measurements(paper)
		weight = float((self.sheet_length * deck) * gsm/1000)/10000
		cost = weight * get_item_rate(paper)
		print ("Sheet {0} sl={1} sw={2} deck={3}".format(gsm, self.sheet_length, self.sheet_width, deck))
		print("Paper {0} weight={1} rate={2} cost={3}".format(paper, weight, get_item_rate(paper), cost))
		return (weight, cost)

	def update_cost(self):
		self.item_rm_cost = 0
		paper_weight = 0
		for item in self.item_papers:
			if item.rm is None: continue
			if (item.rm_type == 'Top' or item.rm_type == 'Liner'):
				(weight, cost) = self.get_paper_weight_cost(item.rm)
				item.rm_weight = float(weight/self.item_per_sheet)
				item.rm_cost = float(cost/self.item_per_sheet)
				self.item_rm_cost += item.rm_cost
				paper_weight += item.rm_weight
			elif (item.rm_type == 'Flute'):
				(weight, cost) = self.get_paper_weight_cost(item.rm)
				item.rm_weight = float(weight * self.item_flute/self.item_per_sheet)
				item.rm_cost = float(cost * self.item_flute/self.item_per_sheet)
				self.item_rm_cost += item.rm_cost
				paper_weight += item.rm_weight
			print "Cost of rm {0} having weight {1} is {2}".format(item.rm, item.rm_weight, item.rm_cost)

		for item in self.item_others:
			if item.rm is None: continue
			item.rm_weight = paper_weight * item.rm_percent / 100
			item.rm_cost = item.rm_weight * get_item_rate(item.rm)
			self.item_rm_cost += item.rm_cost
			print "Cost of rm {0} having weight {1} is {2}".format(item.rm, item.rm_weight, item.rm_cost)

		print("Raw Material cost={0} items={1}".format(self.item_rm_cost, self.item_per_sheet))
		if (self.item_rm_cost == 0): return

		total_expense = get_total_expenses(0)
		(boxes, production) = get_production_details(0)
		print("Boxes = {0} production={1} expense={2}".format(boxes, production, total_expense))
		if (boxes != 0 and self.item_prod_cost == 0): self.item_prod_cost = total_expense/boxes
		self.item_rate = get_item_rate(self.item)
		self.item_total_cost = float(self.item_rm_cost + self.item_prod_cost)
		self.item_profit = float((self.item_rate - self.item_total_cost)*100/self.item_total_cost)
		print("RM cost={0} OP Cost={1} Rate={2}".format(self.item_rm_cost, self.item_prod_cost, get_item_rate(self.item)))

	def get_board_name(self, layer_no):
		idx = layer_no - 1
		board_name = None
		if (idx == 0):
			board_name = "Layer-Top-{0:.1f}-{1:.1f}".format(self.sheet_length, self.sheet_width)
			paper_elements = self.item_papers[idx].rm.split("-")
			board_name += "-" + paper_elements[2] + "-" + paper_elements[3] + "-" + paper_elements[4]
		else:
			board_name = "Layer-Flute-{0:.1f}-{1:.1f}".format(self.sheet_length, self.sheet_width)
			paper_elements = self.item_papers[idx-1].rm.split("-")
			board_name += "-" + paper_elements[2] + "-" + paper_elements[3] + "-" + paper_elements[4]
			paper_elements = self.item_papers[idx].rm.split("-")
			board_name += "-" + paper_elements[2] + "-" + paper_elements[3] + "-" + paper_elements[4]
		return board_name

	def get_all_boards(self):
		layer, boards = 1, []
		while layer <= int(self.item_ply_count):
			boards += [self.get_board_name(layer)]
			layer += 2
		return boards

	def create_board_item(self, layer_no, rate):
		boardname = self.get_board_name(layer_no)
		board = frappe.db.get_value("Item", filters={"name": boardname})
		if board is not None: return board

		item = frappe.new_doc("Item")
		item.item_code = item.item_name = boardname
		item.item_group = "Board Layer"
		item.valuation_rate = rate
		item.weight_uom = "Kg"
		item.save()
		return item.name

	def make_board_items(self):
		layer, boards = 1, []
		while layer <= int(self.item_ply_count):
			item = self.item_papers[layer-1]
			valuation_rate = item.rm_cost
			if (item.rm_type == 'Flute'):
				layer += 1
				item = self.item_papers[layer-1]
				valuation_rate += item.rm_cost
			boards += [self.create_board_item(layer, valuation_rate)]
			layer += 1
		return boards

	def make_new_bom(self):
		bom = frappe.new_doc("BOM")
		bom.item = self.item
		bom.item_name = self.item_name
		bom.quantity, bom.items = 1, []

		for item in (self.item_papers + self.item_others):
			if item.rm is None: continue

			quantity = (bom.quantity * item.rm_weight)/int(self.item_per_sheet)
			print ("Updating Item {0} of quantity {1}".format(item.rm, quantity))

			if (len(bom.items) > 0):
				bom_item = next((bi for bi in bom.items if bi.item_code == item.rm), None)
				if bom_item is not None:
					bom_item.qty += quantity
					continue

			bom_item = frappe.new_doc("BOM Item")
			bom_item.item_code = item.rm
			bom_item.stock_qty = bom_item.qty = quantity
			bom_item.rate = get_item_rate(item.rm)
			rm_item = frappe.get_doc("Item", item.rm)
			bom_item.stock_uom = rm_item.stock_uom
			bom.append("items", bom_item)

		bom.base_operating_cost = bom.operating_cost = bom.quantity * self.item_prod_cost
		bom.save()
		print "Creating new bom {0} for {1} with operating cost {2}".format(bom.name, bom.item_name, bom.operating_cost)
		bom.submit()
		self.item_bom = bom.name

	def before_save(self):
		self.update_cost()

	def before_submit(self):
		self.make_new_bom()

	def on_submit(self):
		boards = self.make_board_items()
		print("Created item decsription {0} with bom {1}".format(self.name, self.item_bom))

	def update_cost_after_submit(self):
		self.update_cost();
		self.save(ignore_permissions=True)

def get_paper_measurements(paper):
	(gsm, bf, deck) = (0, 0, 0)
	item = frappe.get_doc("Item", paper)
	for attribute in item.attributes:
		if attribute.attribute == "GSM":
			gsm = int(attribute.attribute_value)
		elif attribute.attribute == "BF":
			bf = int(attribute.attribute_value)
		elif attribute.attribute == "Deck":
			deck = float(attribute.attribute_value)
	return (gsm, bf, deck)

def get_item_rate(item_name):
	item = frappe.get_doc("Item", item_name)
	rate = item.valuation_rate
	if (rate == 0):
		rate = item.standard_rate
	return rate

def get_total_expenses(month):
	expenses = frappe.get_all("Journal Entry", fields={"voucher_type":"Journal Entry"})
	expense_total = 0

	for expense_entry in expenses:
		expense = frappe.get_doc("Journal Entry", expense_entry.name)
		print("{0}    {1}".format(expense.title, expense.total_debit))
		expense_total += expense.total_debit

	return expense_total

def get_production_details(month):
	prod_orders = frappe.get_all("Production Order", fields={"status":"Completed"})
	total_boxes = total_production = 0

	for order_entry in prod_orders:
		order = frappe.get_doc("Production Order", order_entry.name)
		stock_entry = frappe.get_doc("Stock Entry", {"production_order":order.name})
		total_boxes += order.produced_qty
		total_production += stock_entry.total_outgoing_value

	return (total_boxes, total_production)

@frappe.whitelist()
def get_no_of_boards_for_box(box_desc_name, layer, box_count):
	box_desc = frappe.get_doc("CM Box Description", box_desc_name)
	boards = box_count/box_desc.item_per_sheet
	if (layer != "Top"):
		boards = boards * int(int(box_desc.item_ply_count)/2)
	return boards

@frappe.whitelist()
def get_no_of_boxes_from_board(box_desc_name, layer, boards):
	box_desc = frappe.get_doc("CM Box Description", box_desc_name)
	if (layer != "Top"):
		boards = boards/int(int(box_desc.item_ply_count)/2)
	box_count = boards * box_desc.item_per_sheet
	return box_count

@frappe.whitelist()
def get_planned_paper_quantity(box_desc, rmtype, paper, mfg_qty):
	box_details = frappe.get_doc("CM Box Description", box_desc)
	for paper_item in box_details.item_papers:
		if paper_item.rm_type == rmtype and paper_item.rm == paper:
			return paper_item.rm_weight * mfg_qty
	return 0

@frappe.whitelist()
def filter_papers(doctype, txt, searchfield, start, page_len, filters):
	sheet_length = filters["sheet_length"]
	sheet_width = filters["sheet_width"]
	layer_type = filters["layer_type"]
	colour = 'Brown'
	if layer_type == "Top" and "White" in filters["top_type"]:	colour = 'White'
	return get_layer_papers(sheet_length, sheet_width, colour, txt)

def get_layer_papers(sheet_length, sheet_width, colour, txt=""):
	filter_query =	"""select item.name, attr.attribute_value
						from tabItem item left join `tabItem Variant Attribute` attr
						on (item.name=attr.parent)
						where item.docstatus < 2
							and item.variant_of='Paper-RM'
							and item.disabled=0
							and (attr.attribute='Deck' and
									((attr.attribute_value >= {0} and attr.attribute_value <= {1})
										or (attr.attribute_value >= {2} and attr.attribute_value <= {3})
									)
								)
							and exists (
									select name from `tabItem Variant Attribute` iv_attr
									where iv_attr.parent=item.name
										and (iv_attr.attribute='Colour' and iv_attr.attribute_value = '{4}')
									)
							and item.name LIKE %(txt)s
						order by attr.attribute_value * 1 asc
					""".format(sheet_length, sheet_length+10, sheet_width, sheet_width+10, colour)
	#print "Searching papers matching deck {0} with query {1}".format(sheet_length, filter_query)
	return frappe.db.sql(filter_query, {"txt": "%%%s%%" % txt})
