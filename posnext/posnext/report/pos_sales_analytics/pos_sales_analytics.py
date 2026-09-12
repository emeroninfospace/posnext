# Copyright (c) 2026, jan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	return columns, data, None, None, summary


def get_columns():
	return [
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 170,
		},
		{
			"label": _("Order Date"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 170,
		},
		{
			"label": _("POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 140,
		},
		{
			"label": _("Sales Person"),
			"fieldname": "sales_person",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Order Amount"),
			"fieldname": "order_grand_total",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Order Status"),
			"fieldname": "order_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Tax Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 170,
		},
		{
			"label": _("Invoice Date"),
			"fieldname": "invoice_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Invoiced Amount"),
			"fieldname": "invoice_grand_total",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Invoice Status"),
			"fieldname": "invoice_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Difference"),
			"fieldname": "difference",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Billing Status"),
			"fieldname": "billing_status",
			"fieldtype": "Data",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	orders = frappe.db.sql(
		"""
		SELECT
			so.name          AS sales_order,
			so.transaction_date,
			so.customer,
			so.pos_profile,
			so.grand_total   AS order_grand_total,
			so.status        AS order_status,
			so.per_billed,
			GROUP_CONCAT(DISTINCT st.sales_person SEPARATOR ', ') AS sales_person
		FROM `tabSales Order` so
		LEFT JOIN `tabSales Team` st ON st.parent = so.name AND st.parenttype = 'Sales Order'
		WHERE so.custom_is_posnext = 1
		  AND so.docstatus != 2
		  {conditions}
		GROUP BY so.name
		ORDER BY so.transaction_date DESC, so.creation DESC
	""".format(
			conditions=conditions
		),
		filters,
		as_dict=1,
	)

	if not orders:
		return []

	# Fetch all linked Sales Invoices in one query
	order_names = [o.sales_order for o in orders]
	invoices = frappe.db.sql(
		"""
		SELECT
			sii.sales_order,
			si.name          AS sales_invoice,
			si.posting_date  AS invoice_date,
			si.grand_total   AS invoice_grand_total,
			si.status        AS invoice_status
		FROM `tabSales Invoice Item` sii
		INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE sii.sales_order IN ({placeholders})
		  AND si.docstatus != 2
	""".format(
			placeholders=", ".join(["%s"] * len(order_names))
		),
		tuple(order_names),
		as_dict=1,
	)

	# Build a map: sales_order → list of invoices (deduplicated by invoice name)
	invoices_map = {}
	seen = set()
	for inv in invoices:
		key = (inv.sales_order, inv.sales_invoice)
		if key in seen:
			continue
		seen.add(key)
		invoices_map.setdefault(inv.sales_order, []).append(inv)

	rows = []
	for order in orders:
		linked = invoices_map.get(order.sales_order, [])
		if linked:
			for inv in linked:
				diff = flt(inv.invoice_grand_total) - flt(order.order_grand_total)
				rows.append(
					{
						**order,
						"sales_invoice": inv.sales_invoice,
						"invoice_date": inv.invoice_date,
						"invoice_grand_total": inv.invoice_grand_total,
						"invoice_status": inv.invoice_status,
						"difference": diff,
						"billing_status": _billing_status(order, diff),
					}
				)
		else:
			rows.append(
				{
					**order,
					"sales_invoice": None,
					"invoice_date": None,
					"invoice_grand_total": 0,
					"invoice_status": None,
					"difference": -flt(order.order_grand_total),
					"billing_status": "Unbilled",
				}
			)

	return rows


def _billing_status(order, diff):
	if order.order_status in ("Cancelled", "Closed"):
		return "Cancelled / Closed"
	if abs(diff) < 0.01:
		return "Fully Billed"
	if diff < 0:
		return "Partially Billed"
	return "Overbilled"


def get_summary(data):
	order_set = {r["sales_order"] for r in data}
	invoice_set = {r["sales_invoice"] for r in data if r.get("sales_invoice")}
	unbilled = sum(1 for r in data if r["billing_status"] == "Unbilled")
	total_order_amt = sum(flt(r["order_grand_total"]) for r in data)
	total_invoice_amt = sum(flt(r["invoice_grand_total"]) for r in data)

	return [
		{"label": _("Total Orders"), "value": len(order_set), "datatype": "Int"},
		{"label": _("Invoiced Orders"), "value": len(invoice_set), "datatype": "Int"},
		{"label": _("Unbilled Orders"), "value": unbilled, "datatype": "Int", "indicator": "Red" if unbilled else "Green"},
		{"label": _("Order Amount"), "value": total_order_amt, "datatype": "Currency"},
		{"label": _("Invoiced Amount"), "value": total_invoice_amt, "datatype": "Currency"},
		{
			"label": _("Billing Gap"),
			"value": total_order_amt - total_invoice_amt,
			"datatype": "Currency",
			"indicator": "Red" if (total_order_amt - total_invoice_amt) > 0.01 else "Green",
		},
	]


def get_conditions(filters):
	conditions = []
	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")
	if filters.get("company"):
		conditions.append("so.company = %(company)s")
	if filters.get("pos_profile"):
		conditions.append("so.pos_profile = %(pos_profile)s")
	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
	if filters.get("billing_status") and filters["billing_status"] != "All":
		# handled in Python after fetch — placeholder kept for future SQL push-down
		pass
	return ("AND " + " AND ".join(conditions)) if conditions else ""
