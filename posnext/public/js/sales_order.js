// Copyright (c) 2025, Emeron and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Order', {
    company() {
        erpnext.selling.dimensions.update_dimension(this.frm, this.frm.doctype);
        this.frm.set_value("set_warehouse", "");
        this.frm.set_value("taxes_and_charges", "");
    },

    refresh(frm) {
        // Add WhatsApp button for POS orders
        if (frm.doc.docstatus === 1 && frm.doc.is_pos) {
            frm.add_custom_button(__('Send via WhatsApp'), function () {
                send_receipt_whatsapp(frm);
            }, __('Actions'));
        }
    },

    set_pos_data(frm) {
        // Load POS Profile data including taxes
        if (frm.doc.pos_profile) {
            console.log("Loading POS Profile data:", frm.doc.pos_profile); // Debug
            frappe.db.get_doc('POS Profile', frm.doc.pos_profile).then(pos_profile => {
                console.log("POS Profile loaded:", pos_profile); // Debug
                console.log("POS Profile taxes_and_charges:", pos_profile.taxes_and_charges); // Debug
                
                // Set taxes and charges from POS Profile
                if (pos_profile.taxes_and_charges) {
                    console.log("Setting taxes_and_charges:", pos_profile.taxes_and_charges); // Debug
                    frm.set_value('taxes_and_charges', pos_profile.taxes_and_charges);
                    // Trigger taxes_and_charges to load the actual tax rows
                    frm.trigger('taxes_and_charges');
                }
                
                // Set other POS Profile fields
                if (pos_profile.selling_price_list && !frm.doc.selling_price_list) {
                    frm.set_value('selling_price_list', pos_profile.selling_price_list);
                }
                
                if (pos_profile.warehouse && !frm.doc.set_warehouse) {
                    frm.set_value('set_warehouse', pos_profile.warehouse);
                }
                
                if (pos_profile.currency && !frm.doc.currency) {
                    frm.set_value('currency', pos_profile.currency);
                }
            });
        }
    },

    pos_profile(frm) {
        // When POS Profile changes, load the data
        frm.trigger('set_pos_data');
    },

    taxes_and_charges(frm) {
        // Load tax template rows when taxes_and_charges is set
        if (frm.doc.taxes_and_charges) {
            console.log("Loading taxes from template:", frm.doc.taxes_and_charges); // Debug
            frappe.call({
                method: 'erpnext.controllers.accounts_controller.get_taxes_and_charges',
                args: {
                    'master_doctype': 'Sales Taxes and Charges Template',
                    'master_name': frm.doc.taxes_and_charges
                },
                callback: function(r) {
                    console.log("Tax template response:", r); // Debug
                    if (!r.exc && r.message) {
                        console.log("Tax rows from template:", r.message); // Debug
                        // Clear existing taxes
                        frm.clear_table('taxes');
                        
                        // Add taxes from template
                        r.message.forEach(function(tax) {
                            let row = frm.add_child('taxes');
                            Object.assign(row, tax);
                        });
                        
                        console.log("Taxes after adding:", frm.doc.taxes); // Debug
                        frm.refresh_field('taxes');
                        frm.cscript.calculate_taxes_and_totals();
                        console.log("Taxes after calculation:", frm.doc.taxes); // Debug
                    }
                }
            });
        }
    }
});

function send_receipt_whatsapp(frm) {
    frappe.db.get_value('Customer', frm.doc.customer, 'mobile_no', (r) => {
        if (r && r.mobile_no) {
            show_whatsapp_dialog(frm, r.mobile_no);
        } else {
            frappe.msgprint(__('Please add mobile number for customer'));
        }
    });
}

function show_whatsapp_dialog(frm, mobile) {
    let dialog = new frappe.ui.Dialog({
        title: __('Send Receipt via WhatsApp'),
        fields: [
            {
                fieldname: 'mobile_number',
                label: __('WhatsApp Number'),
                fieldtype: 'Data',
                reqd: 1,
                default: mobile
            },
            {
                fieldname: 'message',
                label: __('Message'),
                fieldtype: 'Small Text',
                default: get_default_message(frm),
                reqd: 1
            }
        ],
        primary_action_label: __('Send'),
        primary_action: function (values) {
            send_via_whatsapp(frm, values, dialog);
        }
    });

    dialog.show();
}

function get_default_message(frm) {
    return `Hello ${frm.doc.customer_name},

Thank you for your order at ${frm.doc.company}!

Order Number: ${frm.doc.name}
Amount: ${format_currency(frm.doc.grand_total, frm.doc.currency)}

We appreciate your business!`;
}

function send_via_whatsapp(frm, values, dialog) {
    let mobile = values.mobile_number.replace(/[^0-9]/g, '');
    let message = values.message;

    let site_url = window.location.origin;
    let receipt_url = site_url + '/printview?doctype=Sales%20Order&name=' + frm.doc.name;
    receipt_url += '&format=Standard&no_letterhead=0';

    message += `\n\nView Receipt: ${receipt_url}`;

    let encoded_message = encodeURIComponent(message);
    let whatsapp_url;

    if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
        whatsapp_url = `https://api.whatsapp.com/send?phone=${mobile}&text=${encoded_message}`;
    } else {
        whatsapp_url = `https://web.whatsapp.com/send?phone=${mobile}&text=${encoded_message}`;
    }

    window.open(whatsapp_url, '_blank');

    frappe.show_alert({
        message: __('Opening WhatsApp...'),
        indicator: 'green'
    }, 3);

    dialog.hide();
}