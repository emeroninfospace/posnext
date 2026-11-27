# Copyright (c) 2025, Emeron and contributors
# For license information, please see license.txt

import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from frappe import _
from frappe.utils import flt, nowdate


class PosnextSalesOrder(SalesOrder):
    """Custom Sales Order class for POSNext POS"""
    
    def validate(self):
        self.set_reserve_stock_for_pos()
        super().validate()

        # Only validate POS-specific fields if this is a POSNext order
        if self.get('custom_is_posnext'):
            self.validate_pos_profile()
            self.validate_pos_user()
    
    def set_reserve_stock_for_pos(self):
        """Reserve stock on submit for POSNext orders.

        ERPNext v15 has no setting that ticks "Reserve Stock" on a Sales Order
        automatically, so POSNext sets it here. Only done while Stock
        Reservation is enabled in Stock Settings, because ERPNext refuses to
        submit an order with "Reserve Stock" ticked when it is disabled.
        Non-stock items are skipped by ERPNext itself.
        """
        if not self.get('custom_is_posnext'):
            return

        if frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
            self.reserve_stock = 1

    def validate_pos_profile(self):
        """Validate POS Profile if this is a POS order"""
        if not self.get('pos_profile'):
            frappe.throw(_("POS Profile is required for POS orders"))
    
    def validate_pos_user(self):
        """Validate if user is authorized for this POS Profile"""
        pos_profile = self.get('pos_profile')
        if pos_profile:
            current_user = frappe.session.user
            pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
            
            if pos_profile_doc.get('applicable_for_users'):
                user_found = False
                for user_row in pos_profile_doc.applicable_for_users:
                    if user_row.user == current_user:
                        user_found = True
                        break
                
                if not user_found:
                    frappe.throw(_("You are not authorized to use POS Profile: {0}").format(pos_profile))
    
    def on_submit(self):
        super().on_submit()
        
        # Add any custom logic for POSNext orders
        if self.get('custom_is_posnext'):
            # You can add notification or other logic here
            pass