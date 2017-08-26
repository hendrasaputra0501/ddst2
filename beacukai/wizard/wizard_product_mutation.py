from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time

class wizard_product_mutation(models.TransientModel):
	_name = "wizard.product.mutation"
	_description = "Product Mutation"
		
	from_date = fields.Date('From', default=lambda *f : time.strftime('%Y-%m-01'))
	to_date = fields.Date('To', default=lambda *t : time.strftime('%Y-%m-%d'))
	product_type = fields.Selection([
		('finish_good','Finish Goods'),
		('raw_material','Raw Materials'),
		('auxiliary_material','Auxiliary Materials'),
		('tools','Tools and Spares'),
		('waste','Waste or Scrap Materials'),
		('asset','Asset'),
		('others','Others'),
		], 'Product Type', default=lambda self: self._context.get('product_type',False))

	@api.multi
	def action_open_window(self):
		context = self._context
		wizard = self.read(['from_date', 'to_date','product_type'])
		if wizard:
			data_obj = self.env['ir.model.data']
			res_model = 'product.product'
			result = data_obj._get_id('master_data_custom', 'view_product_tree2_mutation')
			domain = [('product_type','=',wizard[0]['product_type']),('type','<>','service')]
			view_id = data_obj.browse(result).res_id
			
			from_date = wizard[0]['from_date']!=False and \
				datetime.strptime(wizard[0]['from_date'],'%Y-%m-%d').strftime('%Y-%m-%d 00:00:00') or False
			to_date = wizard[0]['to_date'] and \
				datetime.strptime(wizard[0]['to_date'],'%Y-%m-%d').strftime('%Y-%m-%d 23:59:59') or False
			
			return {
				'name': _('Laporan Pertanggungjawaban Mutasi'),
				'view_type': 'form',
				'view_mode': 'tree',
				'res_model': res_model,
				'view_id':[view_id],
				'type': 'ir.actions.act_window',
				'context': {'from_date': from_date or False,
							'to_date': to_date or False,},
				"domain":domain,
			}

wizard_product_mutation()