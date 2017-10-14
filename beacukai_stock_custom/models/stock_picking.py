from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

from datetime import datetime
import time

import logging

_logger = logging.getLogger(__name__)

class PickingType(models.Model):
	_inherit = 'stock.picking.type'
	default_product_categ_id = fields.Many2one('product.category','Default Product Category')

class Picking(models.Model):
	_inherit = 'stock.picking'

	date_done = fields.Datetime('Date of Transfer', copy=False, readonly=False, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="Completion Date of Transfer")
	date_done_2 = fields.Date('Date of Transfer', copy=False, help="Completion Date of Transfer (Date Format)", readonly=False, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]})
	product_categ_id = fields.Many2one('product.category','Default Product Category',
		default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_product_categ_id,
		readonly=True,
		states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
	
	@api.onchange('date_done_2')
	def _onchange_date_done_2(self):
		if self.date_done_2:
			self.date_done = datetime.strptime(self.date_done_2,DEFAULT_SERVER_DATE_FORMAT).strftime("%Y-%m-%d 07:00:00")

	@api.multi
	def action_revert_done(self):
		self.filtered(lambda picking: picking.state == 'done').write({'state':'assigned'})
		self.mapped('move_lines').filtered(lambda move: move.state == 'done').write({'state':'assigned'})
		self.mapped('move_lines').action_cancel()
		self.mapped('move_lines').write({'state':'draft'})
		return self.write({'state':'draft'})