// Copyright (c) 2017, sathishpy@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('CM Payment Manager', {
	setup: function(frm) {
		frm.events.account_filters(frm)
	},
	refresh: function(frm) {
		frm.set_df_property("bank_account", "read_only", frm.doc.__islocal ? 0 : 1);
		frm.set_df_property("from_date", "read_only", frm.doc.__islocal ? 0 : 1);
		frm.set_df_property("to_date", "read_only", frm.doc.__islocal ? 0 : 1);
	},
	invoke_doc_function(frm, method) {
		frappe.call({
			doc: frm.doc,
			method: method,
			callback: function(r) {
				if(!r.exe) {
					frm.refresh_fields();
				}
			}
		});
	},
	account_filters: function(frm) {
		frm.fields_dict['bank_account'].get_query = function(doc, dt, dn) {
			return {
				filters:[
					["Account", "account_type", "in", ["Bank"]]
				]
			}
		};
		frm.fields_dict['receivable_account'].get_query = function(doc, dt, dn) {
			return {
				filters:[
					["Account", "account_type", "in", ["Receivable"]]
				]
			}
		};
		frm.fields_dict['payable_account'].get_query = function(doc, dt, dn) {
			return {
				filters:[
					["Account", "account_type", "in", ["Payable"]]
				]
			}
		};
	},

	match_invoices: function(frm) {
		frm.events.invoke_doc_function(frm, "populate_matching_invoices");
	},
	create_payments: function(frm) {
		frm.events.invoke_doc_function(frm, "create_payment_entries");
	},
	submit_payments: function(frm) {
		frm.events.invoke_doc_function(frm, "submit_payment_entries");
	},
});