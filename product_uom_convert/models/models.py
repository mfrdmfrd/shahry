# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.tools import pycompat,float_is_zero
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round
from odoo.tools.float_utils import float_round
from collections import defaultdict
from odoo.exceptions import AccessError, UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    uom_convert_rates = fields.One2many(comodel_name="uom.convert.rates", inverse_name="product_id")


class UomConvertRates(models.Model):
    _name = 'uom.convert.rates'

    name = fields.Char()
    product_id = fields.Many2one('product.template')
    uom_id = fields.Many2one('uom.uom', required=1)
    rate = fields.Float(string="Factor", digits='Product Unit of Measure', required=1, default=1)
class MrpBom(models.Model):
    _inherit = 'stock.move'
    
    actual_uom_id = fields.Many2one('uom.uom')
    actual_qty = fields.Float()
    @api.model
    def create(self,vals):
        res = super().create(vals)
        for move in res.group_id.stock_move_ids:
            if move.raw_material_production_id and move.product_id.id == res.product_id.id:
                res.actual_uom_id = move.actual_uom_id.id
                res.actual_qty = move.actual_qty
        return res
    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        return {
            'picking_id': self.picking_id.id if self.picking_id else False,
            'product_id': bom_line.product_id.id,
            'product_uom': bom_line.product_uom_id.id,
            'product_uom_qty': product_qty,
            'quantity_done': quantity_done,
            'state': 'draft',  # will be confirmed below
            'name': self.name,
            'bom_line_id': bom_line.id,
            'actual_uom_id' :  bom_line.actual_uom_id.id,
             'actual_qty' :  bom_line.actual_qty,
        }
    @api.onchange('actual_uom_id','actual_qty','product_uom','product_id')
    def _set_quantity(self):
        if self.actual_uom_id.id == self.product_uom:
            self.product_uom_qty = self.actual_qty
            return 
        product_factor = self.product_id.uom_convert_rates.search([('product_id', '=', self.product_id.product_tmpl_id.id), ('uom_id', '=', self.actual_uom_id.id)])
        if not(product_factor):
            self.product_uom_qty = 0
            return
        product_factor = product_factor[0].rate
        self.product_uom_qty = self.actual_qty / product_factor
class MrpBom(models.Model):
    _inherit = 'mrp.production'

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        source_location = self.location_src_id
        origin = self.name
        if self.orderpoint_id and self.origin:
            origin = self.origin.replace(
                '%s - ' % (self.orderpoint_id.display_name), '')
            origin = '%s,%s' % (origin, self.name)
        data = {
            'sequence': bom_line.sequence if bom_line else 10,
            'name': self.name,
            'date': self.date_planned_start,
            'date_deadline': self.date_planned_start,
            'bom_line_id': bom_line.id if bom_line else False,
            'picking_type_id': self.picking_type_id.id,
            'product_id': product_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.with_company(self.company_id).property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': operation_id,
            'price_unit': product_id.standard_price,
            'procure_method': 'make_to_stock',
            'origin': origin,
            'state': 'draft',
            'warehouse_id': source_location.warehouse_id.id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
            'actual_uom_id' :  bom_line.actual_uom_id.id,
             'actual_qty' :  bom_line.actual_qty,
        }
        return data
class MrpBom(models.Model):
    _inherit = 'mrp.bom.line'
    
    actual_uom_id = fields.Many2one('uom.uom')
    actual_qty = fields.Float()
    
    @api.onchange('actual_uom_id','actual_qty','product_uom_id','product_id')
    def _set_quantity(self):
        if self.actual_uom_id.id == self.product_uom_id:
            self.product_qty = self.actual_qty
            return 
        product_factor = self.product_id.uom_convert_rates.search([('product_id', '=', self.product_id.product_tmpl_id.id), ('uom_id', '=', self.actual_uom_id.id)])
        if not(product_factor):
            self.product_qty = 0
            return
        product_factor = product_factor[0].rate
        self.product_qty = self.actual_qty / product_factor