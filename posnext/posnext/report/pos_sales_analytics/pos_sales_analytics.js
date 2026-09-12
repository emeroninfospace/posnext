// Copyright (c) 2026, jan and contributors
// For license information, please see license.txt

frappe.query_reports["POS Sales Analytics"] = {
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
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "billing_status",
			label: __("Billing Status"),
			fieldtype: "Select",
			options: "All\nFully Billed\nPartially Billed\nUnbilled\nOverbilled\nCancelled / Closed",
			default: "All",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "billing_status") {
			const colors = {
				"Fully Billed":      "green",
				"Partially Billed":  "orange",
				"Unbilled":          "red",
				"Overbilled":        "blue",
				"Cancelled / Closed":"grey",
			};
			const color = colors[data.billing_status] || "grey";
			value = `<span class="indicator-pill ${color}">${data.billing_status || ""}</span>`;
		}

		if (column.fieldname === "difference") {
			const diff = flt(data.difference);
			if (diff < -0.01) {
				value = `<span style="color: var(--red-500);">${value}</span>`;
			} else if (diff > 0.01) {
				value = `<span style="color: var(--blue-500);">${value}</span>`;
			}
		}

		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Export to Excel"), function () {
			report.export_report("Excel");
		});
	},

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function (data) {
					if (!data || !data.length) return;
				},
			},
		});
	},
};
