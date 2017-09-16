from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

from datetime import datetime
import time

import logging

_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
	_inherit = 'stock.quant'

	@api.model
	def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False,
								src_package_id=False, dest_package_id=False,
								force_location_from=False, force_location_to=False):
		'''Create a quant in the destination location and create a negative
		quant in the source location if it's an internal location. '''
		price_unit = move.get_price_unit()
		location = force_location_to or move.location_dest_id
		rounding = move.product_id.uom_id.rounding
		vals = {
			'product_id': move.product_id.id,
			'location_id': location.id,
			'qty': float_round(qty, precision_rounding=rounding),
			'cost': price_unit,
			'history_ids': [(4, move.id)],
			'in_date': move.picking_id and move.picking_id.date_done and move.picking_id.date_done or datetime.now().strftime("%Y-%m-%d 07:00:00"),
			'company_id': move.company_id.id,
			'lot_id': lot_id,
			'owner_id': owner_id,
			'package_id': dest_package_id,
		}
		if move.location_id.usage == 'internal':
			# if we were trying to move something from an internal location and reach here (quant creation),
			# it means that a negative quant has to be created as well.
			negative_vals = vals.copy()
			negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
			negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
			negative_vals['cost'] = price_unit
			negative_vals['negative_move_id'] = move.id
			negative_vals['package_id'] = src_package_id
			negative_quant_id = self.sudo().create(negative_vals)
			vals.update({'propagated_from_id': negative_quant_id.id})

		picking_type = move.picking_id and move.picking_id.picking_type_id or False
		if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
			if qty != 1.0:
				raise UserError(_('You should only receive by the piece with the same serial number'))

		# create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
		return self.sudo().create(vals)