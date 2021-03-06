from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time

class wizard_product_mutation(models.TransientModel):
	_inherit = "wizard.product.mutation"
		
	@api.multi
	def action_open_window(self):
		self.ensure_one()
		
		data_obj = self.env['ir.model.data']
		res_model = 'product.product'
		result = data_obj._get_id('master_data_custom', 'view_product_tree2_mutation')
		domain = [('product_type','=',self.product_type),('type','<>','service')]
		view_id = data_obj.browse(result).res_id
		
		from_date = self.from_date!=False and \
			datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%Y-%m-%d 00:00:00') or False
		to_date = self.to_date and \
			datetime.strptime(self.to_date,'%Y-%m-%d').strftime('%Y-%m-%d 23:59:59') or False
		
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

	@api.multi
	def export_excel(self):
		self.ensure_one()
		datas = {
			'model': 'wizard.product.mutation',
			'from_date' : self.from_date,
			'to_date' : self.to_date,
			'product_type':self.product_type,
		}

		# if self.product_type=='finish_good':
		# 	report_name = 'blend.mutation.report.xls'
		# elif self.product_type=='raw_material':
		# 	report_name = 'rm.categ.mutation.report.xls'
		# else:
		# 	report_name = 'product.mutation.report.xls'
		report_name = 'product.mutation_report_xlsx'
		context = self._context

		products = self.env['product.product'].search([('product_type','=',self.product_type)])
		context = dict(self.env.context, active_ids=products.ids)
		report = self.env['ir.actions.report.xml'].with_context(context).search([('report_name', '=', report_name)], limit=1)
		if not report:
			raise UserError(_("Bad Report Reference") + _("This report is not loaded into the database: %s.") % report_name)
		return {
			'context': context,
			'datas': datas,
			'type': 'ir.actions.report.xml',
			'report_name': report.report_name,
			'report_type': report.report_type,
			'report_file': report.report_file,
			'name': report.name,
		}
wizard_product_mutation()