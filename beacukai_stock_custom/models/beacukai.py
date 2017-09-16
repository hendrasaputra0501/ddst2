from odoo import models, fields, api
from datetime import datetime
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT

class BeacukaiDocument(models.Model):
	_inherit = "beacukai.document"
	
	picking_ids = fields.Many2many('stock.picking', 'beacukai_stock_picking_rel', 'doc_id', 'picking_id', 'Pickings')

	@api.model
	def _prepare_picking(self, beacukai):
		context = self._context
		return {
			'date' : datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT),DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00'),
			'date_done' : beacukai.picking_date!=False and datetime.strptime(beacukai.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
							(beacukai.registration_date!=False and datetime.strptime(beacukai.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') \
								or time.strftime('%Y-%m-%d 07:00:00')),
			'date_done_2' : beacukai.picking_date!=False and beacukai.picking_date or \
							(beacukai.registration_date!=False and beacukai.registration_date \
								or time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
			'name' : context.get('default_name',False) and context['default_name'] or beacukai.picking_no or '/',
			'state' : 'draft',
			'type' : beacukai.shipment_type,
			'partner_id' : beacukai.shipment_type=='in' and (beacukai.source_partner_id and beacukai.source_partner_id.id or False) or (beacukai.dest_partner_id and beacukai.dest_partner_id.id or False),
			'invoice_state': 'none',
			'company_id': self.env.user.company_id.id,
			# 'product_type' : context.get('product_type',False),
		}

	@api.model
	def _prepare_move(self, line):
		context = self._context

		warehouse_obj = self.env['stock.warehouse']
		loc_obj = self.env['stock.location']
		location_id = False
		location_dest_id = False
		if line.shipment_type=='in':
			location_id = line.source_partner_id.property_stock_supplier and line.source_partner_id.property_stock_supplier.id or False
			location_dest_id = line.dest_partner_id.property_stock_customer and line.dest_partner_id.property_stock_customer.id or False
			if not location_id or not location_dest_id:
				loc_ids = loc_obj.search([('usage','=','supplier')])
				location_id = loc_ids and loc_ids[0] or False
				lot_ids = warehouse_obj.search([])
				if lot_ids:
					loc_ids=[lot_ids[0].lot_stock_id.id]
				else:
					loc_ids = loc_obj.search([('usage','=','internal')])
				location_dest_id = loc_ids and loc_ids[0] or False
		elif line.shipment_type == 'out':
			location_id = line.source_partner_id.property_stock_customer and line.source_partner_id.property_stock_customer.id or False
			location_dest_id = line.dest_partner_id.property_stock_customer and line.dest_partner_id.property_stock_customer.id or False
			if not location_id or not location_dest_id:
				lot_ids = warehouse_obj.search([])
				if lot_ids:
					loc_ids=[lot_ids[0].lot_stock_id.id]
				else:
					loc_ids = loc_obj.search([('usage','=','internal')])
				location_id = loc_ids and loc_ids[0] or False
				loc_ids = loc_obj.search([('usage','=','customer')])
				location_dest_id = loc_ids and loc_ids[0] or False
		return {
			'date' : line.doc_id.picking_date!=False and datetime.strptime(line.doc_id.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
						(line.doc_id.registration_date and datetime.strptime(line.doc_id.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
							time.strftime('%Y-%m-%d 07:00:00')),
			'date_expected' : line.doc_id.picking_date!=False and datetime.strptime(line.doc_id.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
						(line.doc_id.registration_date and datetime.strptime(line.doc_id.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
							time.strftime('%Y-%m-%d 07:00:00')),
			'name' : line.name or line.product_id.name or '',
			'state' : 'draft',
			'type' : line.shipment_type,
			'partner_id' : line.shipment_type=='in' and (line.doc_id.source_partner_id and line.doc_id.source_partner_id.id or False) or (line.doc_id.dest_partner_id and line.doc_id.dest_partner_id.id or False),
			'product_id' : line.product_id and line.product_id.id or False,
			'product_qty' : line.product_qty,
			'product_uom' : line.product_uom.id,
			'product_uos_qty' : line.product_qty,
			'product_uos' : line.product_uom.id,
			'location_id' : location_id,
			'location_dest_id' : location_dest_id,
			'company_id': self.env.user.company_id.id,
		}

	@api.multi
	def action_done(self):
		picking_pool = self.env['stock.picking'].sudo()
		for doc in self:
			pickings = []
			product_types = [(x.product_id.product_type and x.product_id.product_type or 'other') for x in doc.product_lines]
			n = 0
			dict_temp = {}
			ctx = self._context.copy()
				
			pick_dict = self._prepare_picking(doc)
			
			for line in doc.product_lines:
				if not pick_dict.get('move_lines',False):
					pick_dict.update({'move_lines':[]})
				pick_dict['move_lines'].append((0, 0, self._prepare_move(line)))

			pickings |= picking_pool.create(pick_dict)

			# pickings.action_confirm()
			# pickings.action_assign()
			pickings.action_done()

			self.write({'picking_ids': map(lambda x:(4,x),[x.id for x in pickings])})
	
		return super(BeacukaiDocument, self).action_done()

	@api.multi
	def action_cancel(self):
		picking_pool = self.env['stock.picking']
		for doc in self:
			for picking in doc.picking_ids:
				picking.mapped('move_lines').action_cancel()
				picking.action_cancel()
				picking.unlink()

		return super(BeacukaiDocument, self).action_cancel()