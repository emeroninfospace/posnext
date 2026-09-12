// Copyright (c) 2026, jan and contributors
// For license information, please see license.txt

frappe.query_reports["POS Product Movement Analytics"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_default("company"),
		},
		{
			fieldname: "pos_profile",
			label: __("POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "movement_category",
			label: __("Movement"),
			fieldtype: "Select",
			options: "All\nFast Mover\nModerate\nSlow Mover\nDead Stock",
			default: "All",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "movement_category") {
			const colors = {
				"Fast Mover":  "green",
				"Moderate":    "blue",
				"Slow Mover":  "orange",
				"Dead Stock":  "red",
			};
			const color = colors[data.movement_category] || "grey";
			value = `<span class="indicator-pill ${color}">${data.movement_category || ""}</span>`;
		}

		if (column.fieldname === "current_stock") {
			const stock = flt(data.current_stock);
			if (stock <= 0) {
				value = `<span style="color: var(--red-500); font-weight: 600;">${value}</span>`;
			}
		}

		if (column.fieldname === "turnover_ratio") {
			const ratio = flt(data.turnover_ratio);
			if (ratio === 99) {
				value = `<span style="color: var(--green-500);">Sold Out</span>`;
			}
		}

		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Export to Excel"), function () {
			report.export_report("Excel");
		});
	},
};
