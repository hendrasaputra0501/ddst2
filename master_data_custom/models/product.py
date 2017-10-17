import math
import re
from datetime import datetime

# from openerp import tools, SUPERUSER_ID
# from openerp.osv import osv, fields, expression
# from openerp.tools.translate import _
import odoo.addons.decimal_precision as dp
# from openerp.tools.Float_utils import Float_round

from odoo import models, fields, api


class ProductCategory(models.Model):
	_inherit = "product.category"

	product_type = fields.Selection([
			('finish_good','Finish Goods'),
			('raw_material','Raw Materials'),
			('auxiliary_material','Auxiliary Materials'),
			('tools','Tools and Spares'),
			('waste','Waste or Scrap Materials'),
			('asset','Asset'),
			('others','Others'),
			], 'Product Type',
		help="Type of Product to provide spesific information for the category of the product")
	
class ProductRMCategory(models.Model):
	_name = "product.rm.category"
	
	name = fields.Char('Description', required=True)
	code = fields.Char('Code/Alias', required=True)
	product_uom = fields.Many2one('product.uom', 'Unit of Measure', required=True)


class ProductBlendComponent(models.Model):
	@api.multi
	@api.depends('gross_consume_percentage','waste_percentage')
	def _compute_consume_percent(self):
		for line in self:
			line.consume_percentage = line.gross_consume_percentage - (line.gross_consume_percentage * (line.waste_percentage / 100))
		# return result

	_name = "product.blend.component"
	
	blend_id = fields.Many2one('product.blend', 'Blend')
	raw_material_categ_id = fields.Many2one('product.rm.category', 'Raw Material Category', required=True)
	gross_consume_percentage = fields.Float('Gross Consume %', digits=dp.get_precision('Product Unit of Measure'), required=True)
	consume_percentage = fields.Float(compute=_compute_consume_percent, string='Net Consume %', digits=dp.get_precision('Product Unit of Measure'), store=True, default=0.0)
	waste_percentage = fields.Float('Waste %', digits=dp.get_precision('Product Unit of Measure'), required=True, default=0.0)
	
	
class ProductBlend(models.Model):
	_name = "product.blend"
	
	code = fields.Char('Code/Alias', required=True)
	name = fields.Char('Description', required=True)
	product_uom = fields.Many2one('product.uom', string='Unit of Measure', required=False)
	blend_component_ids = fields.One2many('product.blend.component', 'blend_id', string='Components')
	
class ProductUosList(models.Model):
	_name = "product.uos.list"
	
	product_tmpl_id = fields.Many2one('product.template', string='Product', required=True)
	uos_id = fields.Many2one('product.uom', string='Unit of Sale', required=True, 
			help='Sepcify a unit of measure here if invoicing is made in another unit of measure than inventory. Keep empty to use the default unit of measure.')
	uos_coeff = fields.Float(string='Unit of Measure -> UOS Coeff', digits= dp.get_precision('Product UoS'), required=True, 
			help='Coefficient to convert default Unit of Measure to Unit of Sale\n'
			' uos = uom * coeff')

class ProductTemplate(models.Model):
	_inherit = "product.template"

	def _compute_quantity_mutation(self):
		res = {}
		date_first = datetime.now().strftime('%Y-01-01 00:00:00')
		date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		if self._context.get('from_date',False) and not self._context.get('to_date',False):
			from_date = self._context.get('from_date')
			to_date = date_now
			c.update({'from_date':from_date,'to_date':to_date})
		elif not self._context.get('from_date',False) and context.get('to_date',False):
			from_date = date_first
			to_date = self._context.get('to_date',False)
		elif not self._context.get('from_date',False) and not context.get('to_date',False):
			from_date = date_first
			to_date = date_now
		else:
			from_date = self._context.get('from_date',False)
			to_date = self._context.get('to_date',False)
		field_names = ['available_qty','opening_qty','in_qty','out_qty','all_qty','adj_qty']
		for product in self:
			res[product.id] = {}.fromkeys(field_names, 0.0)
		
		for f in field_names:
			ctx = {'from_date':from_date,'to_date':to_date}
			if f == 'available_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in', 'all_out') })
			if f == 'opening_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in', 'all_out') })
			if f == 'in_qty':
				ctx.update({'states': ('done',), 'move_type': ('in')})
			if f == 'out_qty':
				ctx.update({'states': ('done',), 'move_type': ('out'),})
			if f == 'all_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in','all_out','in','out2','adj_in','adj_out'),})
			if f == 'adj_qty':
				ctx.update({'states': ('done',), 'move_type': ('adj_in','adj_out'),})
			result_qty = self.mapped('product_variant_ids').with_context(ctx)._compute_movement_quantities(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), from_date, to_date)
			for template in self:
				qty_available = 0
				virtual_available = 0
				incoming_qty = 0
				outgoing_qty = 0
				for p in template.product_variant_ids:
					res[template.id][f] += result_qty.get(p.id, 0.0)
		
		for template in self:
			template.available_qty = res[template.id]['available_qty']
			template.opening_qty = res[template.id]['opening_qty']
			template.in_qty = res[template.id]['in_qty']
			template.out_qty = res[template.id]['out_qty']
			template.all_qty = res[template.id]['all_qty']
			template.adj_qty = res[template.id]['adj_qty']
		return res	

	blend_id = fields.Many2one('product.blend', string='Blend')
	raw_material_categ_id = fields.Many2one('product.rm.category', string='Raw Material Category')
	product_type = fields.Selection(related='categ_id.product_type', selection=[
		('finish_good','Finish Goods'),
		('raw_material','Raw Materials'),
		('auxiliary_material','Auxiliary Materials'),
		('tools','Tools and Spares'),
		('waste','Waste or Scrap Materials'),
		('asset','Asset'),
		('others','Others'),
		], string='Product Type')
	uos_ids = fields.One2many('product.uos.list', 'product_tmpl_id', string='Unit of Sale/Purchase')
	available_qty = fields.Float(string='Current On Hand Qty', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
	opening_qty = fields.Float(string='Saldo Awal', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	in_qty = fields.Float(string='Stock Masuk', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	out_qty = fields.Float(string='Stock Keluar', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	opname_qty = fields.Float(string='Opname Qty', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	all_qty = fields.Float(string='On Hand Quantity', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	adj_qty = fields.Float(string='Penyesuaian', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	
	@api.onchange('categ_id')
	def _onchange_categ_id(self):
		if self.categ_id:
			self.product_type = self.categ_id.product_type and self.categ_id.product_type or False
	
class ProductProduct(models.Model):
	@api.multi
	def _compute_movement_quantities(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
		Location = self.env['stock.location']
		Warehouse = self.env['stock.warehouse']
		Uom = self.env['product.uom']

		states = self._context.get('states',())
		move_type = self._context.get('move_type',())

		# this will be a dictionary of the product UoM by product id
		product_uom = {}
		uom_ids = []
		for product in self:
			product_uom[product.id] = product.uom_id
			uom_ids.append(product.uom_id.id)
		# this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
		uoms_o = {}
		for uom in Uom.browse(uom_ids):
			uoms_o[uom.id] = uom

		product_ids = self.ids
		res = {}.fromkeys(product_ids, 0.0)
		
		results_all_in, results_all_out, results_in, results_out, results_out2, results_adj_in, results_adj_out = [],[],[],[],[],[],[]
		
		# Search Location Internal if it is set inside context or take it from warehouse
		location_ids = []
		if self.env.context.get('location', False):
			if isinstance(self.env.context['location'], (int, long)):
				location_ids = [self.env.context['location']]
			elif isinstance(self.env.context['location'], basestring):
				domain = [('complete_name', 'ilike', self.env.context['location'])]
				if self.env.context.get('force_company', False):
					domain += [('company_id', '=', self.env.context['force_company'])]
				location_ids = Location.search(domain).ids
			else:
				location_ids = self.env.context['location']
		else:
			if self.env.context.get('warehouse', False):
				if isinstance(self.env.context['warehouse'], (int, long)):
					wids = [self.env.context['warehouse']]
				elif isinstance(self.env.context['warehouse'], basestring):
					domain = [('name', 'ilike', self.env.context['warehouse'])]
					if self.env.context.get('force_company', False):
						domain += [('company_id', '=', self.env.context['force_company'])]
					wids = Warehouse.search(domain).ids
				else:
					wids = self.env.context['warehouse']
			else:
				wids = Warehouse.search([]).ids

			for w in Warehouse.browse(wids):
				location_ids.append(w.view_location_id.id)
				
		inventory_loss_loc_ids  = Location.search([('usage','=','inventory')]).ids # inventory loss
		procurement_loc_ids  = Location.search([('usage','=','procurement')]).ids # procurement
		stock_loc_ids = self.env.context.get('location', False) and location_ids and location_ids or Location.search([('usage','=','internal')]).ids # internal
		supp_loc_ids = Location.search([('usage','=','supplier')]).ids # supplier
		production_loc_ids = Location.search([('usage','=','production')]).ids # production
		customer_loc_ids = Location.search([('usage','=','customer')]).ids # customer
		
		where = [tuple(location_ids),tuple(location_ids),tuple(product_ids),tuple(states)]
		where_all_in = [tuple(stock_loc_ids),tuple(stock_loc_ids),tuple(product_ids),tuple(states)]
		where_all_out = [tuple(stock_loc_ids),tuple(stock_loc_ids),tuple(product_ids),tuple(states)]
		where_in = [tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(stock_loc_ids),tuple(product_ids),tuple(states)]
		where_out = [tuple(stock_loc_ids),tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(product_ids),tuple(states)]
		where_out2 = [tuple(stock_loc_ids),tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(product_ids),tuple(states)]
		where_adj_in = [tuple(inventory_loss_loc_ids),tuple(stock_loc_ids),tuple(product_ids),tuple(states)]
		where_adj_out = [tuple(stock_loc_ids),tuple(inventory_loss_loc_ids),tuple(product_ids),tuple(states)]

		date_clause, date_clause_in, date_clause_out = '', '', ''

		if from_date and to_date:
			date_clause = " and date>=%s and date<=%s "
			date_clause_in = " and date<%s "
			date_clause_out = " and date<%s "
			where.append(tuple([from_date]))
			where.append(tuple([to_date]))
			where_all_in.append(tuple([from_date]))
			where_all_out.append(tuple([from_date]))
			where_in.append(tuple([from_date]))
			where_in.append(tuple([to_date]))
			where_out.append(tuple([from_date]))
			where_out.append(tuple([to_date]))
			where_out2.append(tuple([from_date]))
			where_out2.append(tuple([to_date]))
			where_adj_in.append(tuple([from_date]))
			where_adj_in.append(tuple([to_date]))
			where_adj_out.append(tuple([from_date]))
			where_adj_out.append(tuple([to_date]))

		lot_clause = ''
		if lot_id:
			lot_clause = " and prodlot_id=%s"
			where.append(tuple([lot_id]))
			where_all_in.append(tuple([lot_id]))
			where_all_out.append(tuple([lot_id]))
			where_in.append(tuple([lot_id]))
			where_out.append(tuple([lot_id]))
			where_out2.append(tuple([lot_id]))
			where_adj_in.append(tuple([lot_id]))
			where_adj_out.append(tuple([lot_id]))
		package_clause = ''
		if package_id:
			package_clause = " and package_id=%s "
			where.append(tuple([package_id]))
			where_all_in.append(tuple([package_id]))
			where_all_out.append(tuple([package_id]))
			where_in.append(tuple([package_id]))
			where_out.append(tuple([package_id]))
			where_out2.append(tuple([package_id]))
			where_adj_in.append(tuple([package_id]))
			where_adj_out.append(tuple([package_id]))

		if 'all_in' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id NOT IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause_in or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_all_in))
			results_all_in = self.env.cr.fetchall()
		if 'all_out' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id NOT IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause_out or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_all_out))
			results_all_out = self.env.cr.fetchall()
		if 'in' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_in))
			results_in = self.env.cr.fetchall()
		if 'out' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_out))
			results_out = self.env.cr.fetchall()
		if 'out2' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_out))
			results_out2 = self.env.cr.fetchall()
		if 'adj_in' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_adj_in))
			results_adj_in = self.env.cr.fetchall()
		if 'adj_out' in move_type:
			self.env.cr.execute(
				'select sum(product_qty), product_id, product_uom '\
				'from stock_move '\
				'where location_id IN %s '\
				'and location_dest_id IN %s '\
				'and product_id IN %s '\
				'and state IN %s ' + (date_clause or '') +' '\
				+ (lot_clause or '') + (package_clause or '') +\
				'group by product_id,product_uom',tuple(where_adj_out))
			results_adj_out = self.env.cr.fetchall()
		
		# Get the missing UoM resources
		uom_ids = map(lambda x: x[2], results_all_in) + map(lambda x: x[2], results_all_out) + map(lambda x: x[2], results_in)+ map(lambda x: x[2], results_out)+ map(lambda x: x[2], results_out2)+ map(lambda x: x[2], results_adj_in)+ map(lambda x: x[2], results_adj_out)
		uom_ids = filter(lambda x: x not in uoms_o.keys(), uom_ids)
		if uom_ids:
			uoms = Uom.browse(list(set(uom_ids)))
			for o in uoms:
				uoms_o[o.id] = o
				
		# Count the incoming quantities
		for quantity, product_id, prod_uom in results_all_in:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] += res_qty
		# Count the outgoing quantities
		for quantity, product_id, prod_uom in results_all_out:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] -= res_qty

		for quantity, product_id, prod_uom in results_in:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] += res_qty
		# Count the outgoing quantities
		for quantity, product_id, prod_uom in results_out:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] += res_qty

		for quantity, product_id, prod_uom in results_out2:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] -= res_qty

		for quantity, product_id, prod_uom in results_adj_in:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] += res_qty

		for quantity, product_id, prod_uom in results_adj_out:
			res_qty = Uom.browse(prod_uom)._compute_quantity(quantity, product_uom[product_id])
			res[product_id] -= res_qty

		return res
		
	@api.multi
	@api.depends('stock_quant_ids', 'stock_move_ids')
	def _compute_quantity_mutation(self):
		res = {}

		date_first = datetime.now().strftime('%Y-01-01 00:00:00')
		date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		if self._context.get('from_date',False) and not self._context.get('to_date',False):
			from_date = self._context.get('from_date')
			to_date = date_now
			c.update({'from_date':from_date,'to_date':to_date})
		elif not self._context.get('from_date',False) and context.get('to_date',False):
			from_date = date_first
			to_date = self._context.get('to_date',False)
		elif not self._context.get('from_date',False) and not context.get('to_date',False):
			from_date = date_first
			to_date = date_now
		else:
			from_date = self._context.get('from_date',False)
			to_date = self._context.get('to_date',False)
		field_names = ['available_qty','opening_qty','in_qty','out_qty','all_qty','adj_qty']
		for product in self:
			res[product.id] = {}.fromkeys(field_names, 0.0)
		
		for f in field_names:
			ctx = {'from_date':from_date,'to_date':to_date}
			if f == 'available_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in', 'all_out') })
			if f == 'opening_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in', 'all_out') })
			if f == 'in_qty':
				ctx.update({'states': ('done',), 'move_type': ('in')})
			if f == 'out_qty':
				ctx.update({'states': ('done',), 'move_type': ('out'),})
			if f == 'all_qty':
				ctx.update({'states': ('done',), 'move_type': ('all_in','all_out','in','out2','adj_in','adj_out'),})
			if f == 'adj_qty':
				ctx.update({'states': ('done',), 'move_type': ('adj_in','adj_out'),})
			result_qty = self.with_context(ctx)._compute_movement_quantities(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), from_date, to_date)
			for product in self:
				res[product.id][f] = result_qty.get(product.id, 0.0)

		for product in self:
			product.available_qty = res[product.id]['available_qty']
			product.opening_qty = res[product.id]['opening_qty']
			product.in_qty = res[product.id]['in_qty']
			product.out_qty = res[product.id]['out_qty']
			product.all_qty = res[product.id]['all_qty']
			product.adj_qty = res[product.id]['adj_qty']
		return res
	
	_inherit = "product.product"
	# blend_id = fields.Many2one('product.blend', string='Blend')
	# raw_material_categ_id = fields.Many2one('product.rm.category', string='Raw Material Category')
	product_type = fields.Selection(related='categ_id.product_type', selection=[
		('finish_good','Finish Goods'),
		('raw_material','Raw Materials'),
		('auxiliary_material','Auxiliary Materials'),
		('tools','Tools and Spares'),
		('waste','Waste or Scrap Materials'),
		('asset','Asset'),
		('others','Others'),
		], string='Product Type')
	available_qty = fields.Float(string='Current On Hand Qty', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
	opening_qty = fields.Float(string='Saldo Awal', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	in_qty = fields.Float(string='Stock Masuk', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	out_qty = fields.Float(string='Stock Keluar', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	opname_qty = fields.Float(string='Opname Qty', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	all_qty = fields.Float(string='On Hand Quantity', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
	adj_qty = fields.Float(string='Penyesuaian', compute='_compute_quantity_mutation', digits=dp.get_precision('Product Unit of Measure'))
