# -*- coding: utf-8 -*-
# Copyright (c) 2017, sathishpy@gmail.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CMPaperRoll(Document):
	def autoname(self):
		rolls = frappe.db.sql_list("""select name from `tabCM Paper Roll` where paper=%s""", self.paper)
		if rolls:
			idx = len(rolls) + 1
		else:
			idx = 1

		self.name = self.paper + "-Roll" + ('-%.3i' % idx)
