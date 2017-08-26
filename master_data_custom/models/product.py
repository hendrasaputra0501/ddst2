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
	
	@api.onchange('categ_id')
	def _onchange_categ_id(self):
		if self.categ_id:
			self.product_type = self.categ_id.product_type and self.categ_id.product_type or False
	
class ProductProduct(models.Model):
	# def get_product_available2(self, cr, uid, ids, context=None):
	# 	""" Finds whether product is available or not in particular warehouse.
	# 	@return: Dictionary of values
	# 	"""
	# 	if context is None:
	# 		context = {}
	# 	location_obj = self.pool.get('stock.location')
	# 	warehouse_obj = self.pool.get('stock.warehouse')
	# 	shop_obj = self.pool.get('sale.shop')
		
	# 	states = context.get('states',[])
	# 	what = context.get('what',())
	# 	if not ids:
	# 		ids = self.search(cr, uid, [])
	# 	res = {}.fromkeys(ids, 0.0)
	# 	if not ids:
	# 		return res
			
	# 	if context.get('shop', False):
	# 		warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
	# 		if warehouse_id:
	# 			context['warehouse'] = warehouse_id

	# 	if context.get('warehouse', False):
	# 		lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
	# 		if lot_id:
	# 			context['location'] = lot_id

	# 	if context.get('location', False):
	# 		if type(context['location']) == type(1):
	# 			location_ids = [context['location']]
	# 		elif type(context['location']) in (type(''), type(u'')):
	# 			location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
	# 		else:
	# 			location_ids = context['location']
	# 	else:
	# 		location_ids = []
	# 		wids = warehouse_obj.search(cr, uid, [], context=context)
	# 		if not wids:
	# 			return res
	# 		for w in warehouse_obj.browse(cr, uid, wids, context=context):
	# 			location_ids.append(w.lot_stock_id.id)

	# 	# build the list of ids of children of the location given by id
	# 	if context.get('compute_child',True):
	# 		child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
	# 		location_ids = child_location_ids or location_ids
		
	# 	# this will be a dictionary of the product UoM by product id
	# 	product2uom = {}
	# 	uom_ids = []
	# 	for product in self.read(cr, uid, ids, ['uom_id'], context=context):
	# 		product2uom[product['id']] = product['uom_id'][0]
	# 		uom_ids.append(product['uom_id'][0])
	# 	# this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
	# 	uoms_o = {}
	# 	for uom in self.pool.get('product.uom').browse(cr, uid, uom_ids, context=context):
	# 		uoms_o[uom.id] = uom

	# 	results_all_in = []
	# 	results_all_out = []
	# 	results_in = []
	# 	results_out = []
	# 	results_out2 = []
	# 	results_adj_in = []
	# 	results_adj_out = []
		
	# 	from_date = context.get('from_date',False)
	# 	to_date = context.get('to_date',False)
		
	# 	date_str = False
	# 	date_str_in = False
	# 	date_str_out = False
		
	# 	inventory_loss_loc_ids  = self.pool.get('stock.location').search(cr,uid,[('usage','=','inventory')])
	# 	procurement_loc_ids  = self.pool.get('stock.location').search(cr,uid,[('usage','=','procurement')])
	# 	stock_loc_ids = context.get('location', False) and location_ids and location_ids or self.pool.get('stock.location').search(cr,uid,[('usage','=','internal')])
	# 	supp_loc_ids = self.pool.get('stock.location').search(cr,uid,[('usage','=','supplier')])
	# 	production_loc_ids = self.pool.get('stock.location').search(cr,uid,[('usage','=','production')])
	# 	customer_loc_ids = self.pool.get('stock.location').search(cr,uid,[('usage','=','customer')])

	# 	where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
	# 	where_all_in = [tuple(stock_loc_ids),tuple(stock_loc_ids),tuple(ids),tuple(states)]
	# 	where_all_out = [tuple(stock_loc_ids),tuple(stock_loc_ids),tuple(ids),tuple(states)]
	# 	where_in = [tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(stock_loc_ids),tuple(ids),tuple(states)]
	# 	where_out = [tuple(stock_loc_ids),tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(ids),tuple(states)]
	# 	where_out2 = [tuple(stock_loc_ids),tuple(supp_loc_ids+production_loc_ids+customer_loc_ids+procurement_loc_ids),tuple(ids),tuple(states)]
	# 	where_adj_in = [tuple(inventory_loss_loc_ids),tuple(stock_loc_ids),tuple(ids),tuple(states)]	
	# 	where_adj_out = [tuple(stock_loc_ids),tuple(inventory_loss_loc_ids),tuple(ids),tuple(states)]	

	# 	if from_date and to_date:
	# 		date_str = "date>=%s and date<=%s"
	# 		date_str_in = "date<%s"
	# 		date_str_out = "date<%s"
	# 		where.append(tuple([from_date]))
	# 		where.append(tuple([to_date]))
	# 		where_all_in.append(tuple([from_date]))
	# 		where_all_out.append(tuple([from_date]))
	# 		where_in.append(tuple([from_date]))
	# 		where_in.append(tuple([to_date]))
	# 		where_out.append(tuple([from_date]))
	# 		where_out.append(tuple([to_date]))
	# 		where_out2.append(tuple([from_date]))
	# 		where_out2.append(tuple([to_date]))
	# 		where_adj_in.append(tuple([from_date]))
	# 		where_adj_in.append(tuple([to_date]))
	# 		where_adj_out.append(tuple([from_date]))
	# 		where_adj_out.append(tuple([to_date]))
		
	# 	if 'all_in' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id NOT IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state IN %s ' + (date_str_in and 'and '+date_str_in+' ' or '') +' '\
	# 			'group by product_id,product_uom',tuple(where_all_in))
	# 		results_all_in = cr.fetchall()
	# 	if 'all_out' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id NOT IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state in %s ' + (date_str_out and 'and '+date_str_out+' ' or '') + ' '\
	# 			'group by product_id,product_uom',tuple(where_all_out))
	# 		results_all_out = cr.fetchall()
	# 	if 'in' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
	# 			'group by product_id,product_uom',tuple(where_in))
	# 		results_in = cr.fetchall()
	# 	if 'out' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
	# 			'group by product_id,product_uom',tuple(where_out))
	# 		results_out = cr.fetchall()
	# 	if 'out2' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
	# 			'group by product_id,product_uom',tuple(where_out))
	# 		results_out2 = cr.fetchall()
	# 	if 'adj_in' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
	# 			'group by product_id,product_uom',tuple(where_adj_in))
	# 		results_adj_in = cr.fetchall()
	# 	if 'adj_out' in what:
	# 		cr.execute(
	# 			'select sum(product_qty), product_id, product_uom '\
	# 			'from stock_move '\
	# 			'where location_id IN %s '\
	# 			'and location_dest_id IN %s '\
	# 			'and product_id IN %s '\
	# 			'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
	# 			'group by product_id,product_uom',tuple(where_adj_out))
	# 		results_adj_out = cr.fetchall()
		
	# 	# Get the missing UoM resources
	# 	uom_obj = self.pool.get('product.uom')
	# 	uoms = map(lambda x: x[2], results_all_in) + map(lambda x: x[2], results_all_out) + map(lambda x: x[2], results_in)+ map(lambda x: x[2], results_out)+ map(lambda x: x[2], results_out2)+ map(lambda x: x[2], results_adj_in)+ map(lambda x: x[2], results_adj_out)
	# 	if context.get('uom', False):
	# 		uoms += [context['uom']]
	# 	uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
	# 	if uoms:
	# 		uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
	# 		for o in uoms:
	# 			uoms_o[o.id] = o
				
	# 	#TOCHECK: before change uom of product, stock move line are in old uom.
	# 	context.update({'raise-exception': False})
	# 	# Count the incoming quantities
	# 	for quantity, product_id, prod_uom in results_all_in:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				 uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] += quantity
	# 	# Count the outgoing quantities
	# 	for quantity, product_id, prod_uom in results_all_out:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] -= quantity

	# 	for quantity, product_id, prod_uom in results_in:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				 uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] += quantity
	# 	# Count the outgoing quantities
	# 	for quantity, product_id, prod_uom in results_out:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] += quantity

	# 	for quantity, product_id, prod_uom in results_out2:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] -= quantity

	# 	for quantity, product_id, prod_uom in results_adj_in:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] += quantity

	# 	for quantity, product_id, prod_uom in results_adj_out:
	# 		quantity = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], quantity,
	# 				uoms_o[context.get('uom', False) or product2uom[product_id]], context=context)
	# 		res[product_id] -= quantity

	# 	return res

	# @api.multi
	# def _product_movement_quantities(self):
	# 	date_first = datetime.now().strftime('%Y-01-01 00:00:00')
	# 	date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	# 	if self._context.get('from_date',False) and not self._context.get('to_date',False):
	# 		from_date = self._context.get('from_date')
	# 		to_date = date_now
	# 		c.update({'from_date':from_date,'to_date':to_date})
	# 	elif not self._context.get('from_date',False) and context.get('to_date',False):
	# 		from_date = date_first
	# 		to_date = self._context.get('to_date',False)
	# 	elif not self._context.get('from_date',False) and not context.get('to_date',False):
	# 		from_date = date_first
	# 		to_date = date_now
	# 	else:
	# 		from_date = self._context.get('from_date',False)
	# 		to_date = self._context.get('to_date',False)
	# 	res = self._compute_movement_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), from_date, to_date)
 #        for product in self:
 #            product.available_qty = res[product.id]['available_qty']
 #            product.opening_qty = res[product.id]['opening_qty']
 #            product.in_qty = res[product.id]['in_qty']
 #            product.out_qty = res[product.id]['out_qty']
 #            product.all_qty = res[product.id]['all_qty']
 #            product.adj_qty = res[product.id]['adj_qty']

	# @api.multi
	# def _compute_movement_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
	# 	if self._context is None:
	# 		context = {}

	# 	location_obj = self.env['stock.location']
	# 	warehouse_obj = self.env['stock.warehouse']
	# 	shop_obj = self.env['sale.shop']
		
	# 	for id in self:
	# 		res[id] = {}.fromkeys(field_names, 0.0)
		
	# 	for f in field_names:
	# 		c = context.copy()
	# 		c.update({'from_date':from_date,'to_date':to_date})
	# 		if f == 'available_qty':
	# 			c.update({'states': ('done',), 'what': ('all_in', 'all_out') })
	# 		if f == 'opening_qty':
	# 			c.update({'states': ('done',), 'what': ('all_in', 'all_out') })
	# 		if f == 'in_qty':
	# 			c.update({'states': ('done',), 'what': ('in')})
	# 		if f == 'out_qty':
	# 			c.update({'states': ('done',), 'what': ('out'),})
	# 		if f == 'all_qty':
	# 			c.update({'states': ('done',), 'what': ('all_in','all_out','in','out2','adj_in','adj_out'),})
	# 		if f == 'adj_qty':
	# 			c.update({'states': ('done',), 'what': ('adj_in','adj_out'),})	
	# 		stock = self.get_product_available2(cr, uid, ids, context=c)
	# 		for id in ids:
	# 			res[id][f] = stock.get(id, 0.0)
	# 	return res

	_inherit = "product.product"
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
	# available_qty = fields.Float(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Current On Hand Qty',)
	# opening_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Saldo Awal',)
	# in_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Stock Masuk',)
	# out_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Stock Keluar',)
	# opname_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Opname Qty',)
	# all_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='On Hand Quantity',)
	# adj_qty = fields.function(compute='_product_movement_quantities', digits=dp.get_precision('Product Unit of Measure'),
	# 	string='Penyesuaian',)