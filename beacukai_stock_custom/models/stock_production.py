from odoo import models, fields, api
from datetime import datetime
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT

class ProductionMove(models.Model):
	_name = 'production.move'

	name = fields.Char('Description', required=True, readonly=True, states={'draft':[('readonly',False)]})
	move_id = fields.Many2one("stock.move","Move ID", readonly=True, states={'draft':[('readonly',False)]}, ondelete='cascade')
	date_done = fields.Date("Date", required=True, readonly=True, states={'draft':[('readonly',False)]})
	raw_material_categ_id = fields.Many2one('product.rm.category', 'Raw Material Category', readonly=True, states={'draft':[('readonly',False)]})
	product_uom = fields.Many2one("product.uom", "Unit of Measure", required=True, readonly=True, states={'draft':[('readonly',False)]})
	product_qty = fields.Float("Quantity", digits=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, states={'draft':[('readonly',False)]})
	location_id = fields.Many2one("stock.location","Source Location",required=True, domain="[('usage','!=','view')]", readonly=True, states={'draft':[('readonly',False)]})
	location_dest_id = fields.Many2one("stock.location","Destination Location",required=True, domain="[('usage','!=','view')]", readonly=True, states={'draft':[('readonly',False)]})
	state = fields.Selection([('draft','Draft'),('done','Done')], string="Status", required=True, default='draft')

	_order = "date_done desc, id asc"

	@api.onchange('raw_material_categ_id')
	def onchange_product_id(self):
		if not self.raw_material_categ_id:
			self.product_uom = False
		else:
			self.product_uom = self.raw_material_categ_id.product_uom.id
			self.name = self.raw_material_categ_id.name

	@api.multi
	def action_done(self):
		""" Makes the move done and if all moves are done, it will finish the picking.
		@return:
		"""
		self.write({'state': 'done'})
		return True

	@api.multi
	def action_set_draft(self):
		""" Makes the move done and if all moves are done, it will finish the picking.
		@return:
		"""
		self.write({'state': 'draft'})
		return True

	@api.multi
	def unlink(self):
		for move in self:
			if move.state != 'draft':
				raise osv.except_osv(_('User Error!'), _('You can only delete draft moves.'))
		return super(ProductionMove, self).unlink()