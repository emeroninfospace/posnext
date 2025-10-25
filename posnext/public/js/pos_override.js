// Override ERPNext's POS to create Sales Order instead of Sales Invoice
frappe.provide("erpnext.PointOfSale");

// Store original function
const original_init_sales_invoice = erpnext.PointOfSale.Controller.prototype.init_sales_invoice;

// Override to create Sales Order
erpnext.PointOfSale.Controller.prototype.init_sales_invoice = function () {
    // Create Sales Order instead of Sales Invoice
    this.frm = {};
    this.frm.doc = frappe.model.get_new_doc("Sales Order");
    this.frm.doc.is_pos = 1;
    this.frm.doc.pos_profile = this.pos_profile_data.name;
    this.frm.doc.docstatus = 0; // Draft

    // Set other fields
    this.frm.doc.transaction_date = frappe.datetime.get_today();
    this.frm.doc.delivery_date = frappe.datetime.get_today();
    this.frm.doc.company = this.pos_profile_data.company;
    this.frm.doc.currency = this.pos_profile_data.currency || frappe.defaults.get_user_default("currency");
    this.frm.doc.selling_price_list = this.pos_profile_data.selling_price_list;
    this.frm.doc.set_warehouse = this.pos_profile_data.warehouse;

    // Set customer
    if (this.pos_profile_data.customer) {
        this.frm.doc.customer = this.pos_profile_data.customer;
    }
};

// Override submit invoice to submit Sales Order
const original_submit_invoice = erpnext.PointOfSale.Controller.prototype.submit_sales_invoice;

erpnext.PointOfSale.Controller.prototype.submit_sales_invoice = function () {
    // Submit Sales Order instead
    this.frm.doc.doctype = "Sales Order";

    return frappe.call({
        method: "posnext.api.pos.submit_sales_order",
        freeze: true,
        args: {
            sales_order: this.frm.doc
        },
        callback: (r) => {
            if (r.message) {
                frappe.show_alert({
                    message: __("Sales Order {0} created successfully", [r.message.name]),
                    indicator: "green"
                });
                this.toggle_components(false);
                this.order_summary.toggle_component(true);
                this.order_summary.load_summary_of(r.message, true);
                frappe.utils.play_sound("submit");
            }
        }
    });
};

// Override print to print Sales Order
const original_print_receipt = erpnext.PointOfSale.Controller.prototype.print_receipt;

erpnext.PointOfSale.Controller.prototype.print_receipt = function () {
    const print_format = this.pos_profile_data.print_format_for_online || this.pos_profile_data.print_format;
    const letter_head = this.pos_profile_data.letter_head || "";

    // Print Sales Order instead of Sales Invoice
    const print_url = frappe.urllib.get_full_url(
        `/printview?doctype=Sales%20Order&name=${encodeURIComponent(this.frm.doc.name)}`
        + `&trigger_print=1`
        + `&format=${encodeURIComponent(print_format)}`
        + `&no_letterhead=${letter_head ? 0 : 1}`
        + `&letterhead=${encodeURIComponent(letter_head)}`
        + `&settings={}`
        + `&_lang=en`
    );

    const printWindow = window.open(print_url, "Print");
    if (printWindow) {
        printWindow.addEventListener("load", function () {
            printWindow.print();
        });
    }
};

console.log("POSNext: POS overridden to create Sales Orders");