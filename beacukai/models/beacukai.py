import time
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class beacukai_document(models.Model):
	@api.model
	def _get_source_partner_id(self):
		context = self._context
		partner_id = False
		if context.get('shipment_type',False) == 'out':
			user_obj = self.env['res.users']
			partner_id = self.env.user.company_id.partner_id.id

		return partner_id

	@api.model
	def _get_source_address(self):
		context = self._context
		
		address = ""
		if context.get('shipment_type',False) == 'out':
			user_obj = self.env['res.users']
			partner = self.env.user.company_id.partner_id
			if partner.street:
				address += partner.street
			if partner.street2:
				address += ". "+partner.street2

		return address

	@api.model
	def _get_dest_partner_id(self):
		context = self._context
		
		partner_id = False
		if context.get('shipment_type',False) == 'in':
			user_obj = self.env['res.users']
			partner_id = self.env.user.company_id.partner_id.id

		return partner_id

	@api.model
	def _get_dest_address(self):
		context = self._context
		
		address = ""
		if context.get('shipment_type',False) == 'in':
			user_obj = self.env['res.users']
			partner = self.env.user.company_id.partner_id
			if partner.street:
				address += partner.street
			if partner.street2:
				address += ". "+partner.street2

		return address

	_name = "beacukai.document"
	_inherit = ["mail.thread"]
	_description = "Beacukai Document"
	
	shipment_type = fields.Selection([('in','Pemasukan Barang'),('out','Pengeluaran Barang'),],'Shipment Type', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=lambda self: self._context.get('shipment_type',False))
	document_type = fields.Selection([('23', 'BC 2.3'),('25','BC 2.5'),('261','BC 2.61'),('262','BC 2.62'),('27in', 'BC 2.7 Masukan'),('27out', 'BC 2.7 Keluaran'),('30', 'BC 3.0'),('40', 'BC 4.0'),('41','BC 4.1'),], 'Jenis Dokumen', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=lambda self: self._context.get('document_type',False))
	registration_no = fields.Char('No. Pengajuan', size=10, required=True, readonly=True, states={'draft':[('readonly',False)]})
	registration_date = fields.Date('Tgl. Pengajuan', required=True, readonly=True, states={'draft':[('readonly',False)]})
	picking_no = fields.Char('Shipment Number', required=True, readonly=True, states={'draft':[('readonly',False)]})
	picking_date = fields.Date('Shipment Date', readonly=True, states={'draft':[('readonly',False)]})
	source_partner_id = fields.Many2one('res.partner','Source Partner', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=_get_source_partner_id)
	source_partner_address = fields.Char('Partner Address', readonly=True, states={'draft':[('readonly',False)]}, default=_get_source_address)
	dest_partner_id = fields.Many2one('res.partner','Destination Partner', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=_get_dest_partner_id)
	dest_partner_address = fields.Char('Partner Address', readonly=True, states={'draft':[('readonly',False)]}, default=_get_dest_address)
	currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=lambda self: self.env['res.users'].browse(self.env.user.id).company_id.currency_id.id)
	state = fields.Selection([('draft','Draft BC'), ('validated','Valid BC'), ('cancelled','Cancelled')], 'Status', default=lambda *s : 'draft')
	product_lines = fields.One2many('beacukai.document.line','doc_id','Product Lines', required=True, readonly=True, states={'draft':[('readonly',False)]})

	_order = "registration_date desc, id desc"

	@api.multi
	def name_get(self):
		res = []
		for doc in self:
			doc_type = dict(self.document_type.selection).get(doc.document_type)
			name = doc.registration_no!='<Empty>' and doc.registration_no or 'New BC'
			res.append((doc.id, "%s %s"%(doc_type,name)))
		return res

	@api.onchange('shipment_type','source_partner_id','dest_partner_id')
	def onchange_partner_id(self):
		context = self._context
		partner_obj = self.env['res.partner']
		res = {}
		address = ""
		
		if sel.shipment_type == 'out':
			if self.dest_partner_id:
				partner = partner_obj.browse(self.dest_partner_id)
				if partner.street:
					address += partner.street
				if partner.street2:
					address += ". "+partner.street2
				self.dest_partner_address = address
				if partner.default_currency_id:
					self.currency_id = partner.default_currency_id.id
			else:
				self.dest_partner_address = ''
		elif self.shipment_type == 'in':
			if self.source_partner_id:
				partner = partner_obj.browse(self.source_partner_id)
				if partner.street:
					address += partner.street
				if partner.street2:
					address += ". "+partner.street2
				self.source_partner_address = address
				if partner.default_currency_id:
					self.currency_id = partner.default_currency_id.id
			else:
				self.dest_partner_address = ''

	@api.multi
	def action_done(self):
		context = self._context
		for doc in self:
			self.env['beacukai.document.line'].action_done([x.id for x in doc.product_lines])
		return self.write({'state':'validated'})

	@api.multi
	def action_cancel(self):
		context = self._context
		for doc in self:
			self.env['beacukai.document.line'].action_cancel([x.id for x in doc.product_lines])
		return self.write({'state':'cancelled'})

	@api.multi
	def action_set_draft(self):
		context = self._context
		for doc in self:
			self.env['beacukai.document.line'].action_set_draft([x.id for x in doc.product_lines])
		return self.write({'state':'draft'})

	@api.multi
	def unlink(self):
		context = self._context
		for doc in self:
			if doc.state not in ('draft', 'cancelled'):
				raise ValidationError(_('You cannot delete a BC which is not draft or cancelled. You should cancel it instead.'))
		
		return super(beacukai_document, self).unlink()

	@api.multi
	def copy(self, default=None):
		default = dict(default or {})
		default.update(
			state = 'draft',
			picking_date=False,
		)
		if 'registration_no' not in default:
			default.update(
				picking_no='<Empty>',
			)
		if 'registration_no' not in default:
			default.update(
				registration_no='<Empty>',
			)
		if 'registration_date' not in default:
			default.update(
				date_due=time.strftime('%Y-%m-%d')
			)
		return super(beacukai_document, self).copy(default)

class beacukai_document_line(models.Model):
	_name = "beacukai.document.line"
	_description = "BC Lines"
	
	doc_id = fields.Many2one('beacukai.document','Reference Doc')
	name = fields.Text('Description')
	product_id = fields.Many2one('product.product', 'Product', required=True)
	product_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
	product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)
	price_unit = fields.Float('Price Unit', digits=(2,6), required=True)
	line_tax_ids = fields.Many2many('account.tax', 'beacukai_line_tax_rel', 'line_id', 'tax_id', string='Taxes')
	price_subtotal = fields.Float('Amount', digits=dp.get_precision('Account'), required=True)
	
	shipment_type = fields.Selection(related='doc_id.shipment_type', string='Shipment Type', selection=[('in','Pemasukan Barang'),('out','Pengeluaran Barang'),])
	document_type = fields.Selection(related='doc_id.document_type', string='Jenis Dokumen', selection=[('23', 'BC 2.3'),('25','BC 2.5'),('261','BC 2.61'),('262','BC 2.62'),('27in', 'BC 2.7 Masukan'),('27out', 'BC 2.7 Keluaran'),('30', 'BC 3.0'),('40', 'BC 4.0'),('41','BC 4.1'),])
	registration_no = fields.Char(related='doc_id.registration_no', size=10, string='No. Pengajuan')
	registration_date = fields.Date(related='doc_id.registration_date', string='Tgl. Pengajuan')
	picking_no = fields.Char(related='doc_id.picking_no', sting='Shipment Number')
	picking_date = fields.Date(related='doc_id.picking_date', string='Shipment Date')
	currency_id = fields.Many2one('res.currency', related='doc_id.currency_id', string='Currency')
	source_partner_id = fields.Many2one('res.partner', related='doc_id.source_partner_id', string='Source Partner')
	dest_partner_id = fields.Many2one('res.partner', related='doc_id.dest_partner_id', string='Destination Partner')
	state = fields.Selection([('draft','Draft BC'), ('validated','Valid BC'), ('cancelled','Cancelled')], 'Status')

	_order = "id desc"

	@api.multi
	def name_get(self):
		res = []
		for line in self:
			doc_type = line.doc_id and dict(self.fields_get(allfields=['document_type'])['document_type']['selection'])[line.doc_id.document_type]
			registration_no = line.doc_id and line.doc_id.registration_no or ""
			name = line.name
			res.append((line.id, line.doc_id and "(%s %s) %s"%(doc_type,registration_no,name) or name))
		return res

	@api.onchange('product_id')
	def onchange_product_id(self):
		product_obj = self.env['product.product']
		if self.product_id:
			self.product_uom = self.product_id.uom_id.id
			self.name = self.product_id.name
		else:
			self.product_uom = False
		
	@api.one
	@api.onchange('product_id','price_unit','product_qty','line_tax_ids')
	def onchange_price_unit(self):
		warning = {}
		
		if not self.product_id:
			self.price_unit = 0.0
			self.product_qty = 0.0
			self.price_subtotal = 0.0
			warning = {
				'title' : _("Warning!"),
				'message' : _("Please define the product first.")
			}
			return {'warning': warning}
		if not self.product_qty or not self.price_unit:
			self.price_unit = 0.0
			self.product_qty = 0.0
			self.price_subtotal = 0.0
			warning = {
				'title' : _("Warning!"),
				'message' : _("Please define the product qty or the price unit.")
			}
			self.price_unit
			return {'warning': warning}
			
		taxes = self.line_tax_ids.compute_all(self.price_unit, self.doc_id.currency_id, self.product_qty, product=self.product_id)
		self.price_subtotal = taxes['total_included']

	@api.one
	@api.onchange('product_id','price_subtotal','product_qty','line_tax_ids')
	def onchange_price_subtotal(self, product_id, price_subtotal, product_qty, line_tax_ids):
		res = {}
		warning = {}
		
		if not product_id:
			warning = {
				'title' : _("Warning!"),
				'message' : _("Please define the product first.")
			}
			self.price_unit = 0.0
			self.product_qty = 0.0
			self.price_subtotal = 0.0
			return {'warning': warning}
		if not product_qty and not amount:
			warning = {
				'title' : _("Warning!"),
				'message' : _("Please define the product qty or the price unit.")
			}
			self.price_unit = 0.0
			self.product_qty = 0.0
			self.price_subtotal = 0.0
			return {'warning': warning}

		price_unit = self.price_subtotal
		total_percent =	sum([(1.0+tax.amount) for tax in self.line_tax_ids if tax.type=='percent'])
		total_fixed = sum([tax.amount for tax in self.line_tax_ids if tax.type=='fixed'])
		price_subtotal -= total_fixed
		if total_percent:
			price_unit = price_subtotal/total_percent
		if not self.product_qty:
			self.price_unit = 0.0 
		else:
			self.price_unit = price_unit/product_qty

	@api.multi
	def action_done(self):
		context = self._context
		return self.write({'state':'validated'})

	@api.multi
	def action_cancel(self):
		context = self._context
		return self.write({'state':'cancelled'})

	@api.multi
	def action_set_draft(self):
		context = self._context
		return self.write({'state':'draft'})

class beacukai_document_line_in(models.Model):
	_name = "beacukai.document.line.in"
	_inherit = "beacukai.document.line"
	_table = "beacukai_document_line"
	_description = "Incoming BC lines"

	# def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
	# 	return self.env['beacukai.document.line').search(cr, user, args, offset, limit, order, context, count)

	# def read(self, cr, self.env.user.id, ids, fields=None, context=None, load='_classic_read'):
	# 	return self.env['beacukai.document.line').read(cr, self.env.user.id, ids, fields=fields, context=context, load=load)

	# def read_group(self, cr, self.env.user.id, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
	# 	return self.pool['beacukai.document.line'].read_group(cr, self.env.user.id, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

	# def check_access_rights(self, cr, self.env.user.id, operation, raise_exception=True):
	# 	#override in order to redirect the check of acces rights on the stock.picking object
	# 	return self.env['beacukai.document.line').check_access_rights(cr, self.env.user.id, operation, raise_exception=raise_exception)

	# def check_access_rule(self, cr, self.env.user.id, ids, operation, context=None):
	# 	#override in order to redirect the check of acces rules on the stock.picking object
	# 	return self.env['sbeacukai.document.line').check_access_rule(cr, self.env.user.id, ids, operation, context=context)

	# def _workflow_trigger(self, cr, self.env.user.id, ids, trigger, context=None):
	# 	#override in order to trigger the workflow of stock.picking at the end of create, write and unlink operation
	# 	#instead of it's own workflow (which is not existing)
	# 	return self.env['beacukai.document.line')._workflow_trigger(cr, self.env.user.id, ids, trigger, context=context)

	# def _workflow_signal(self, cr, self.env.user.id, ids, signal, context=None):
	# 	#override in order to fire the workflow signal on given stock.picking workflow instance
	# 	#instead of it's own workflow (which is not existing)
	# 	return self.env['beacukai.document.line')._workflow_signal(cr, self.env.user.id, ids, signal, context=context)

	# def message_post(self, *args, **kwargs):
	# 	"""Post the message on stock.picking to be able to see it in the form view when using the chatter"""
	# 	return self.env['beacukai.document.line').message_post(*args, **kwargs)

	# def message_subscribe(self, *args, **kwargs):
	# 	"""Send the subscribe action on stock.picking model as it uses _name in request"""
	# 	return self.env['beacukai.document.line').message_subscribe(*args, **kwargs)

	# def message_unsubscribe(self, *args, **kwargs):
	# 	"""Send the unsubscribe action on stock.picking model to match with subscribe"""
	# 	return self.env['beacukai.document.line').message_unsubscribe(*args, **kwargs)

	# def default_get(self, cr, self.env.user.id, fields_list, context=None):
	# 	# merge defaults from stock.picking with possible defaults defined on stock.picking.in
	# 	defaults = self.pool['beacukai.document.line'].default_get(cr, self.env.user.id, fields_list, context=context)
	# 	in_defaults = super(beacukai_document_line_in, self).default_get(cr, self.env.user.id, fields_list, context=context)
	# 	defaults.update(in_defaults)
	# 	return defaults


class beacukai_document_line_out(models.Model):
	_name = "beacukai.document.line.out"
	_inherit = "beacukai.document.line"
	_table = "beacukai_document_line"
	_description = "Outgoing BC lines"

	# def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
	# 	return self.env['beacukai.document.line').search(cr, user, args, offset, limit, order, context, count)

	# def read(self, cr, self.env.user.id, ids, fields=None, context=None, load='_classic_read'):
	# 	return self.env['beacukai.document.line').read(cr, self.env.user.id, ids, fields=fields, context=context, load=load)

	# def read_group(self, cr, self.env.user.id, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
	# 	return self.pool['beacukai.document.line'].read_group(cr, self.env.user.id, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

	# def check_access_rights(self, cr, self.env.user.id, operation, raise_exception=True):
	# 	#override in order to redirect the check of acces rights on the stock.picking object
	# 	return self.env['beacukai.document.line').check_access_rights(cr, self.env.user.id, operation, raise_exception=raise_exception)

	# def check_access_rule(self, cr, self.env.user.id, ids, operation, context=None):
	# 	#override in order to redirect the check of acces rules on the stock.picking object
	# 	return self.env['sbeacukai.document.line').check_access_rule(cr, self.env.user.id, ids, operation, context=context)

	# def _workflow_trigger(self, cr, self.env.user.id, ids, trigger, context=None):
	# 	#override in order to trigger the workflow of stock.picking at the end of create, write and unlink operation
	# 	#instead of it's own workflow (which is not existing)
	# 	return self.env['beacukai.document.line')._workflow_trigger(cr, self.env.user.id, ids, trigger, context=context)

	# def _workflow_signal(self, cr, self.env.user.id, ids, signal, context=None):
	# 	#override in order to fire the workflow signal on given stock.picking workflow instance
	# 	#instead of it's own workflow (which is not existing)
	# 	return self.env['beacukai.document.line')._workflow_signal(cr, self.env.user.id, ids, signal, context=context)

	# def message_post(self, *args, **kwargs):
	# 	"""Post the message on stock.picking to be able to see it in the form view when using the chatter"""
	# 	return self.env['beacukai.document.line').message_post(*args, **kwargs)

	# def message_subscribe(self, *args, **kwargs):
	# 	"""Send the subscribe action on stock.picking model as it uses _name in request"""
	# 	return self.env['beacukai.document.line').message_subscribe(*args, **kwargs)

	# def message_unsubscribe(self, *args, **kwargs):
	# 	"""Send the unsubscribe action on stock.picking model to match with subscribe"""
	# 	return self.env['beacukai.document.line').message_unsubscribe(*args, **kwargs)

	# def default_get(self, cr, self.env.user.id, fields_list, context=None):
	# 	# merge defaults from stock.picking with possible defaults defined on stock.picking.in
	# 	defaults = self.pool['beacukai.document.line'].default_get(cr, self.env.user.id, fields_list, context=context)
	# 	in_defaults = super(beacukai_document_line_out, self).default_get(cr, self.env.user.id, fields_list, context=context)
	# 	defaults.update(in_defaults)
	# 	return defaults
