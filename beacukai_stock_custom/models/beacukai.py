from odoo import models, fields, api
from datetime import datetime
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT

class BeacukaiDocument(models.Model):
	_inherit = "beacukai.document"
	
	@api.model
	def _default_picking_type(self):
		type_obj = self.env['stock.picking.type']
		company_id = self.env.context.get('company_id') or self.env.user.company_id.id
		type_code = self._context.get('shipment_type',False)=='in' and 'incoming' or 'outgoing'
		types = type_obj.search([('code', '=', type_code), ('warehouse_id.company_id', '=', company_id)])
		if not types:
			types = type_obj.search([('code', '=', type_code), ('warehouse_id', '=', False)])
		return types[:1]

	picking_ids = fields.Many2many('stock.picking', 'beacukai_stock_picking_rel', 'doc_id', 'picking_id', 'Pickings', readonly=True)
	picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=_default_picking_type,\
		help="This will determine picking type of incoming shipment")
	group_id = fields.Many2one('procurement.group','Procurement Group')

	@api.model
	def _prepare_picking(self):
		context = self._context

		partner = self.shipment_type=='in' and (self.source_partner_id or False) or (self.dest_partner_id or False)
		
		if not partner:
			raise UserError(_("You must set %s Partner in this document"%(self.shipment_type=='in' and 'Source' or 'Destination')))
			
		if not self.group_id:
			self.group_id = self.group_id.create({
				'name': self.picking_no,
				'partner_id': partner.id
			})

		if self.shipment_type=='in' and not partner.property_stock_supplier:
			raise UserError(_("You must set a Vendor Location for this partner %s") % partner.name)
		elif self.shipment_type=='out' and not partner.property_stock_customer:
			raise UserError(_("You must set a Customer Location for this partner %s") % partner.name)
		
		location_id, location_dest_id = False, False
		if self.shipment_type=='in':
			location_id = partner.property_stock_supplier.id or False
			location_dest_id = self.dest_partner_id.property_stock_customer and self.dest_partner_id.property_stock_customer.id or self.picking_type_id.default_location_dest_id.id
		elif self.shipment_type=='out':
			location_id = self.source_partner_id.property_stock_customer and self.source_partner_id.property_stock_customer.id or self.picking_type_id.default_location_src_id.id
			location_dest_id = partner.property_stock_customer.id or False
		return {
			'date' : datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT),DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 00:00:00'),
			'date_done' : self.picking_date!=False and datetime.strptime(self.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 00:00:00') or \
							(self.registration_date!=False and datetime.strptime(self.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 00:00:00') \
								or time.strftime('%Y-%m-%d 00:00:00')),
			'date_done_2' : self.picking_date!=False and self.picking_date or \
							(self.registration_date!=False and self.registration_date \
								or time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
			'name' : context.get('default_name',False) and context['default_name'] or self.picking_no or '/',
			'origin' : self.registration_no,
			'state' : 'draft',
			'picking_type_id': self.picking_type_id.id,
			'partner_id' : self.shipment_type=='in' and (self.source_partner_id and self.source_partner_id.id or False) or (self.dest_partner_id and self.dest_partner_id.id or False),
			'invoice_state': 'none',
			# 'company_id': self.company_id.id,
			'company_id': self.env.user.company_id.id,
			'location_id' : location_id,
			'location_dest_id' : location_dest_id,
			# 'product_type' : context.get('product_type',False),
		}

	@api.multi
	def action_done(self):
		picking_pool = self.env['stock.picking'].sudo()
		move_pool = self.env['stock.move'].sudo()
		pickings = self.env['stock.picking'].browse()
		for doc in self:
			product_types = [(x.product_id.product_type and x.product_id.product_type or 'other') for x in doc.product_lines]
			n = 0
			dict_temp = {}
			ctx = self._context.copy()
				
			pick_dict = self._prepare_picking()
			picking = picking_pool.create(pick_dict)
			
			moves = doc.product_lines._create_stock_moves(picking)
			moves = moves.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
			seq = 0
			for move in moves:
				seq += 5
				move.sequence = seq
			moves.force_assign()
			picking.message_post_with_view('mail.message_origin_link',
				values={'self': picking},
				subtype_id=self.env.ref('mail.mt_note').id)

			pickings += picking
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

class BeacukaiDocumentLine(models.Model):
	_inherit = "beacukai.document.line"

	@api.multi
	def _prepare_stock_moves(self, picking):
		""" Prepare the stock moves data for one order line. This function returns a list of
		dictionary ready to be used in stock.move's create()
		"""
		self.ensure_one()
		res = []
		if self.product_id.type not in ['product', 'consu']:
			return res
		
		location_id = picking.location_id.id
		location_dest_id = picking.location_dest_id.id

		template = {
			# 'date' : self.doc_id.picking_date!=False and datetime.strptime(self.doc_id.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
			# 			(self.doc_id.registration_date and datetime.strptime(self.doc_id.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
			# 				time.strftime('%Y-%m-%d 07:00:00')),
			'date' : picking.date_done,
			# 'date_expected' : line.doc_id.picking_date!=False and datetime.strptime(line.doc_id.picking_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
			# 			(line.doc_id.registration_date and datetime.strptime(line.doc_id.registration_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d 07:00:00') or \
			# 				time.strftime('%Y-%m-%d 07:00:00')),
			'date_expected' : picking.date_done,
			'name' : self.name or self.product_id.name or '',
			'state' : 'draft',
			# 'type' : self.shipment_type,
			'partner_id' : self.shipment_type=='in' and (self.doc_id.source_partner_id and self.doc_id.source_partner_id.id or False) or (self.doc_id.dest_partner_id and self.doc_id.dest_partner_id.id or False),
			'product_categ_id' : self.product_id and self.product_id.categ_id.id or False,
			'product_id' : self.product_id and self.product_id.id or False,
			'product_uom_qty' : self.product_qty,
			'product_uom' : self.product_uom.id,
			'product_uos_qty' : self.product_qty,
			'product_uos' : self.product_uom.id,
			'location_id' : location_id,
			'location_dest_id' : location_dest_id,
			# 'company_id': self.doc_id.company_id.id,
			'company_id': self.env.user.company_id.id,
			'picking_id': picking.id,
			'picking_type_id': self.doc_id.picking_type_id.id,

			'group_id': self.doc_id.group_id.id,
			'procurement_id': False,
			
			'origin': self.doc_id.registration_no,
			
			'route_ids': self.doc_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.doc_id.picking_type_id.warehouse_id.route_ids])] or [],
			# 'warehouse_id': self.doc_id.picking_type_id.warehouse_id.id,
		}
		res.append(template)
		return res

	@api.multi
	def _create_stock_moves(self, picking):
		moves = self.env['stock.move']
		done = self.env['stock.move'].browse()
		for line in self:
			for val in line._prepare_stock_moves(picking):
				done += moves.create(val)
		return done