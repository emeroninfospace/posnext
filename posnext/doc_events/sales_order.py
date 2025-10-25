# Copyright (c) 2025, Emeron and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, flt


def validate_so(doc, method):
    """Validate Sales Order for POS"""
    # ONLY run if this is a POSNext Sales Order
    if not doc.get('custom_is_posnext'):
        return  # Skip for standalone Sales Orders
    
    if doc.get('pos_profile'):
        # Validate branch if required
        show_branch = frappe.db.get_value("POS Profile", doc.pos_profile, 'show_branch')
        if not doc.get('branch') and show_branch == 1:
            frappe.throw(_("Create Branch Accounting Dimensions."))
        
        # Set delivery date if not set
        if not doc.delivery_date:
            doc.delivery_date = nowdate()
        
        # Set sales person from user
        sales_person = get_sales_person_for_user()
        if sales_person:
            if doc.get('custom_sales_person'):
                doc.custom_sales_person = sales_person
            
            # Add to sales team if not present
            if not doc.get('sales_team'):
                doc.append("sales_team", {
                    "sales_person": sales_person,
                    "allocated_percentage": 100
                })


def on_submit_so(doc, method):
    """On submit of Sales Order from POS"""
    # ONLY run if this is a POSNext Sales Order
    if not doc.get('custom_is_posnext'):
        return  # Skip for standalone Sales Orders
    
    # if doc.get('pos_profile'):
        # Create delivery note if needed
        # create_delivery_note_from_so(doc)


# def create_delivery_note_from_so(doc):
#     """Create Delivery Note from Sales Order"""
#     # Skip if not a POSNext order
#     if not doc.get('custom_is_posnext'):
#         return
    
#     delivery_note = frappe.new_doc("Delivery Note")
#     delivery_note.customer = doc.customer
#     delivery_note.posting_date = nowdate()
#     delivery_note.company = doc.company
    
#     if doc.get('taxes_and_charges'):
#         delivery_note.taxes_and_charges = doc.taxes_and_charges
    
#     all_items_sufficient = True
    
#     # Add items
#     for item in doc.items:
#         available_qty = frappe.db.get_value(
#             "Bin", 
#             {"item_code": item.item_code, "warehouse": item.warehouse}, 
#             "actual_qty"
#         ) or 0
        
#         delivery_note.append("items", {
#             "item_code": item.item_code,
#             "item_name": item.get('item_name'),
#             "uom": item.uom,
#             "qty": item.qty,
#             "rate": item.rate,
#             "warehouse": item.warehouse,
#             "against_sales_order": item.parent,
#             "so_detail": item.name,
#             "cost_center": item.get('cost_center')
#         })
        
#         if item.qty > available_qty:
#             all_items_sufficient = False
    
#     # Add taxes
#     if doc.get('taxes'):
#         for tax in doc.taxes:
#             delivery_note.append("taxes", {
#                 "charge_type": tax.charge_type,
#                 "account_head": tax.account_head,
#                 "description": tax.get('description'),
#                 "rate": tax.get('rate', 0),
#                 "tax_amount": tax.tax_amount,
#                 "total": tax.total,
#                 "cost_center": tax.get('cost_center')
#             })
    
#     # Add sales team
#     if doc.get('sales_team'):
#         for sp in doc.sales_team:
#             delivery_note.append("sales_team", {
#                 "sales_person": sp.sales_person,
#                 "allocated_percentage": sp.allocated_percentage
#             })
    
#     try:
#         delivery_note.save()
        
#         if all_items_sufficient:
#             delivery_note.submit()
#             frappe.msgprint(_("Delivery Note {0} created and submitted").format(delivery_note.name))
#         else:
#             frappe.msgprint(_("Delivery Note {0} created as draft due to insufficient stock").format(delivery_note.name))
#     except Exception as e:
#         frappe.log_error(f"Error creating Delivery Note: {str(e)}")
#         frappe.msgprint(_("Error creating Delivery Note: {0}").format(str(e)))


def get_sales_person_for_user():
    """Get Sales Person for current user"""
    current_user = frappe.session.user
    return frappe.db.get_value("Sales Person", {"custom_user": current_user}, "name")