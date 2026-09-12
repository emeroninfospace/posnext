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
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 130,
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Data",
			"width": 70,
		},
		{
			"label": _("No. of Orders"),
			"fieldname": "order_count",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Qty Sold"),
			"fieldname": "total_qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Revenue"),
			"fieldname": "total_revenue",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Avg Selling Rate"),
			"fieldname": "avg_rate",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Current Stock"),
			"fieldname": "current_stock",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Turnover Ratio"),
			"fieldname": "turnover_ratio",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Movement"),
			"fieldname": "movement_category",
			"fieldtype": "Data",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	# Aggregate sales data from POS Sales Order Items
	rows = frappe.db.sql(
		"""
		SELECT
			soi.item_code,
			soi.item_name,
			soi.item_group,
			soi.uom,
			COUNT(DISTINCT so.name)   AS order_count,
			SUM(soi.qty)              AS total_qty,
			SUM(soi.amount)           AS total_revenue,
			AVG(soi.rate)             AS avg_rate
		FROM `tabSales Order Item` soi
		INNER JOIN `tabSales Order` so ON so.name = soi.parent
		WHERE so.custom_is_posnext = 1
		  AND so.docstatus = 1
		  {conditions}
		GROUP BY soi.item_code, soi.uom
		ORDER BY total_qty DESC
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)

	if not rows:
		return []

	# Fetch current stock from Bin (sum across warehouses or specific warehouse)
	item_codes = [r.item_code for r in rows]
	warehouse_condition = ""
	if filters.get("warehouse"):
		warehouse_condition = "AND b.warehouse = %(warehouse)s"

	stock_map = {}
	stock_data = frappe.db.sql(
		"""
		SELECT b.item_code, SUM(b.actual_qty) AS actual_qty
		FROM `tabBin` b
		WHERE b.item_code IN ({placeholders})
		  {wh_condition}
		GROUP BY b.item_code
		""".format(
			placeholders=", ".join(["%s"] * len(item_codes)),
			wh_condition=warehouse_condition,
		),
		tuple(item_codes) if not filters.get("warehouse") else tuple(item_codes) + (filters["warehouse"],),
		as_dict=1,
	)
	for s in stock_data:
		stock_map[s.item_code] = flt(s.actual_qty)

	# Calculate turnover and classify movement
	data = []
	for row in rows:
		current_stock = stock_map.get(row.item_code, 0)
		qty_sold = flt(row.total_qty)

		if current_stock > 0:
			turnover_ratio = round(qty_sold / current_stock, 2)
		elif qty_sold > 0:
			turnover_ratio = 99.0  # sold out — very fast
		else:
			turnover_ratio = 0.0

		movement_category = _classify(qty_sold, turnover_ratio)

		# Skip if filtering by movement category
		if filters.get("movement_category") and filters["movement_category"] != "All":
			if movement_category != filters["movement_category"]:
				continue

		data.append(
			{
				**row,
				"current_stock": current_stock,
				"turnover_ratio": turnover_ratio,
				"movement_category": movement_category,
			}
		)

	return data


def _classify(qty_sold, turnover_ratio):
	if qty_sold == 0:
		return "Dead Stock"
	if turnover_ratio >= 3.0:
		return "Fast Mover"
	if turnover_ratio >= 1.0:
		return "Moderate"
	return "Slow Mover"


def get_summary(data):
	total_skus    = len(data)
	fast          = sum(1 for r in data if r["movement_category"] == "Fast Mover")
	moderate      = sum(1 for r in data if r["movement_category"] == "Moderate")
	slow          = sum(1 for r in data if r["movement_category"] == "Slow Mover")
	dead          = sum(1 for r in data if r["movement_category"] == "Dead Stock")
	total_revenue = sum(flt(r["total_revenue"]) for r in data)
	total_qty     = sum(flt(r["total_qty"]) for r in data)

	return [
		{"label": _("Total SKUs"),     "value": total_skus,     "datatype": "Int"},
		{"label": _("Fast Movers"),    "value": fast,           "datatype": "Int", "indicator": "Green"},
		{"label": _("Moderate"),       "value": moderate,       "datatype": "Int", "indicator": "Blue"},
		{"label": _("Slow Movers"),    "value": slow,           "datatype": "Int", "indicator": "Orange"},
		{"label": _("Dead Stock"),     "value": dead,           "datatype": "Int", "indicator": "Red" if dead else "Green"},
		{"label": _("Total Qty Sold"), "value": total_qty,      "datatype": "Float"},
		{"label": _("Total Revenue"),  "value": total_revenue,  "datatype": "Currency"},
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
	if filters.get("item_group"):
		conditions.append("soi.item_group = %(item_group)s")
	return ("AND " + " AND ".join(conditions)) if conditions else ""
