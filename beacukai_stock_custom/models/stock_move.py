from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

from datetime import datetime
import time

import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
	_inherit = "stock.move"

	product_categ_id = fields.Many2one('product.category','Product Category', default=lambda self: self._context.get('product_categ_id',False))
	
	@api.multi
	def _create_production_moves(self):
		self.ensure_one()
		warehouse_obj = self.env['stock.warehouse']
		loc_obj = self.env['stock.location']
		prod_move_obj = self.env['production.move'].sudo()
		todo_prodmove = self.env['production.move']
		
		loc_ids2 = loc_obj.search([('usage','=','inventory'),('scrap_location','=',True)])
		location_scrap_id = loc_ids2 and loc_ids2[0] or False
		
		date_done = self.picking_id and self.picking_id.date_done and \
			datetime.strptime(self.picking_id.date_done, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y-%m-%d') or \
			(self.date and datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%Y-%m-%d') or time.strftime('%Y-%m-%d'))
		
		prod_move_created_ids = []
		if self.product_id.product_type=='finish_good':
			if self.location_id.usage=='production' and self.location_dest_id.usage=='internal':
				for component in self.product_id.blend_id.blend_component_ids:
					waste_qty = ((self.product_qty*(component.gross_consume_percentage/100.0))/((100.0-component.waste_percentage)/100.0))*(component.waste_percentage/100.0)
					issued_qty = self.product_qty
					todo_prodmove |= prod_move_obj.create({
						'product_uom' : self.product_uom.id,
						'date_done' : date_done,
						'product_qty' : self.product_qty or 0.0,
						'name' : component.raw_material_categ_id.name or 'Raw Material Consumed',
						# 'blend_id' : self.blend_id.id or False,
						'raw_material_categ_id' : component.raw_material_categ_id.id,
						'location_id' : self.location_id.id,
						'location_dest_id' : self.location_dest_id.id,
						'state': 'draft',
						'move_id':self.id,
					})
					todo_prodmove |= prod_move_obj.create({
						'date_done' : date_done,
						'product_uom' : self.product_uom.id,
						'product_qty' : waste_qty or 0.0,
						'name' : component.raw_material_categ_id.name or 'Raw Material Wasted',
						'raw_material_categ_id' : component.raw_material_categ_id.id,
						'location_id' : self.location_id.id,
						'location_dest_id' : location_scrap_id and location_scrap_id.id or False,
						'state': 'draft',
						'move_id':self.id,
					})
					# prod_move_created_ids.extend([new_id1,new_id2])
		elif self.product_id.product_type=='raw_material':
			if self.location_id.usage=='internal' and self.location_dest_id.usage=='production':
				todo_prodmove |= prod_move_obj.create({
					'product_uom' : self.product_uom.id,
					'date_done' : date_done,
					'product_qty' : self.product_qty or 0.0,
					'name' : self.product_id.raw_material_categ_id.name or 'Raw Material Issued',
					# 'blend_id' : self.blend_id.id or False,
					'raw_material_categ_id' : self.product_id.raw_material_categ_id.id,
					'location_id' : self.location_id.id,
					'location_dest_id' : self.location_dest_id.id,
					'state': 'draft',
					'move_id':self.id,
				})
				prod_move_created_ids.append(new_id)

		todo_prodmove.action_done()

	@api.multi
	def action_done(self):
		""" Process completely the moves given and if all moves are done, it will finish the picking. """
		self.filtered(lambda move: move.state == 'draft').action_confirm()

		Uom = self.env['product.uom']
		Quant = self.env['stock.quant']

		pickings = self.env['stock.picking']
		procurements = self.env['procurement.order']
		operations = self.env['stock.pack.operation']

		remaining_move_qty = {}

		for move in self:
			if move.picking_id:
				pickings |= move.picking_id
			remaining_move_qty[move.id] = move.product_qty
			for link in move.linked_move_operation_ids:
				operations |= link.operation_id
				pickings |= link.operation_id.picking_id

		# Sort operations according to entire packages first, then package + lot, package only, lot only
		operations = operations.sorted(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

		for operation in operations:

			# product given: result put immediately in the result package (if False: without package)
			# but if pack moved entirely, quants should not be written anything for the destination package
			quant_dest_package_id = operation.product_id and operation.result_package_id.id or False
			entire_pack = not operation.product_id and True or False

			# compute quantities for each lot + check quantities match
			lot_quantities = dict((pack_lot.lot_id.id, operation.product_uom_id._compute_quantity(pack_lot.qty, operation.product_id.uom_id)
			) for pack_lot in operation.pack_lot_ids)

			qty = operation.product_qty
			if operation.product_uom_id and operation.product_uom_id != operation.product_id.uom_id:
				qty = operation.product_uom_id._compute_quantity(qty, operation.product_id.uom_id)
			if operation.pack_lot_ids and float_compare(sum(lot_quantities.values()), qty, precision_rounding=operation.product_id.uom_id.rounding) != 0.0:
				raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))

			quants_taken = []
			false_quants = []
			lot_move_qty = {}

			prout_move_qty = {}
			for link in operation.linked_move_operation_ids:
				prout_move_qty[link.move_id] = prout_move_qty.get(link.move_id, 0.0) + link.qty

			# Process every move only once for every pack operation
			for move in prout_move_qty.keys():
				# TDE FIXME: do in batch ?
				move.check_tracking(operation)

				# TDE FIXME: I bet the message error is wrong
				if not remaining_move_qty.get(move.id):
					raise UserError(_("The roundings of your unit of measure %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))

				if not operation.pack_lot_ids:
					preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
					quants = Quant.quants_get_preferred_domain(
						prout_move_qty[move], move, ops=operation, domain=[('qty', '>', 0)],
						preferred_domain_list=preferred_domain_list)
					Quant.quants_move(quants, move, operation.location_dest_id, location_from=operation.location_id,
									  lot_id=False, owner_id=operation.owner_id.id, src_package_id=operation.package_id.id,
									  dest_package_id=quant_dest_package_id, entire_pack=entire_pack)
				else:
					# Check what you can do with reserved quants already
					qty_on_link = prout_move_qty[move]
					rounding = operation.product_id.uom_id.rounding
					for reserved_quant in move.reserved_quant_ids:
						if (reserved_quant.owner_id.id != operation.owner_id.id) or (reserved_quant.location_id.id != operation.location_id.id) or \
								(reserved_quant.package_id.id != operation.package_id.id):
							continue
						if not reserved_quant.lot_id:
							false_quants += [reserved_quant]
						elif float_compare(lot_quantities.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
							if float_compare(lot_quantities[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
								lot_quantities[reserved_quant.lot_id.id] -= reserved_quant.qty
								quants_taken += [(reserved_quant, reserved_quant.qty)]
								qty_on_link -= reserved_quant.qty
							else:
								quants_taken += [(reserved_quant, lot_quantities[reserved_quant.lot_id.id])]
								lot_quantities[reserved_quant.lot_id.id] = 0
								qty_on_link -= lot_quantities[reserved_quant.lot_id.id]
					lot_move_qty[move.id] = qty_on_link

				remaining_move_qty[move.id] -= prout_move_qty[move]

			# Handle lots separately
			if operation.pack_lot_ids:
				# TDE FIXME: fix call to move_quants_by_lot to ease understanding
				self._move_quants_by_lot(operation, lot_quantities, quants_taken, false_quants, lot_move_qty, quant_dest_package_id)

			# Handle pack in pack
			if not operation.product_id and operation.package_id and operation.result_package_id.id != operation.package_id.parent_id.id:
				operation.package_id.sudo().write({'parent_id': operation.result_package_id.id})

		# Check for remaining qtys and unreserve/check move_dest_id in
		move_dest_ids = set()
		for move in self:
			if float_compare(remaining_move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding) > 0:  # In case no pack operations in picking
				move.check_tracking(False)  # TDE: do in batch ? redone ? check this

				preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
				quants = Quant.quants_get_preferred_domain(
					remaining_move_qty[move.id], move, domain=[('qty', '>', 0)],
					preferred_domain_list=preferred_domain_list)
				Quant.quants_move(
					quants, move, move.location_dest_id,
					lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id)

			# If the move has a destination, add it to the list to reserve
			if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
				move_dest_ids.add(move.move_dest_id.id)

			if move.procurement_id:
				procurements |= move.procurement_id

			# unreserve the quants and make them available for other operations/moves
			move.quants_unreserve()

		# Check the packages have been placed in the correct locations
		self.mapped('quant_ids').filtered(lambda quant: quant.package_id and quant.qty > 0).mapped('package_id')._check_location_constraint()

		# set the move as done
		# self.write({'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
		# self.write({'state': 'done', 'date': (self.picking_id.date_done and self.picking_id.date_done or time.strftime("%Y-%m-%d 07:00:00"))})
		for move in self:
			move.write({'state': 'done', 'date': (move.picking_id.date_done and move.picking_id.date_done or time.strftime("%Y-%m-%d 07:00:00"))})

		# if it is using product finish good or raw material, then we move of the raw material which is issue or receipt to or from production
		for move in self:
			move._create_production_moves()

		procurements.check()
		
		# assign destination moves
		if move_dest_ids:
			# TDE FIXME: record setise me
			self.browse(list(move_dest_ids)).action_assign()

		# pickings.filtered(lambda picking: picking.state == 'done' and not picking.date_done).write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
		pickings.filtered(lambda picking: picking.state == 'done' and not picking.date_done).write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

		return True

	@api.multi
	def action_cancel(self):
		prod_move_obj = self.env['production.move'].sudo()
		res = super(StockMove, self).action_cancel()
		for move in self:
			if move.product_id.categ_id.product_type in ('finish_good','raw_material'):
				for prod_move in prod_move_obj.search([('move_id','=',move.id)]):
					prod_move.action_set_draft()
					prod_move.unlink()
		return res