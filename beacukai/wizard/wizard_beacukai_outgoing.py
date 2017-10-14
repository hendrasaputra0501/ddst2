from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time

class wizard_product_outgoing(models.TransientModel):
	_name = "wizard.product.outgoing"
	_description = "Outgoing Products"
	
	from_date = fields.Date('Dari Tangganl', default=time.strftime('%Y-%m-01'))
	to_date = fields.Date('Sampai Tanggal', default=time.strftime('%Y-%m-%d'))
	shipment_type = fields.Selection([('in','Penerimaan Barang'),('out','Pengeluaran Barang')],'Type', default=lambda self: self._context.get('shipment_type',False))
	product_type = fields.Selection([
			('finish_good','Barang Jadi'),
			('raw_material','Bahan Baku'),
			('auxiliary_material','Bahan Penolong'),
			('tools','Alat dan Suku Cadang'),
			('waste','Barang Sampah'),
			('asset','Aset'),
			('others','Lain - lain'),
			], 'Tipe Barang', default=lambda self: self._context.get('product_type',False))
	
	@api.multi
	def action_open_window(self):
		self.ensure_one()
		data_obj = self.env['ir.model.data']
		res_model = 'beacukai.document.line.in'
		result = data_obj._get_id('beacukai', 'view_beacukai_document_line_out_tree')
		domain = [('shipment_type','=','out'),('state','=','validated')]
		view_id = data_obj.browse(result).res_id
		
		from_date = self.from_date!=False and \
			datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%Y-%m-%d 00:00:00') or False
		to_date = self.to_date and \
			datetime.strptime(self.to_date,'%Y-%m-%d').strftime('%Y-%m-%d 23:59:59') or False
		
		domain.append(('registration_date','>=', self.from_date))
		domain.append(('registration_date','<=', self.to_date))
		return {
			'name': _('Laporan Pengeluaran Barang'),
			'view_type': 'form',
			'view_mode': 'tree',
			'res_model': res_model,
			'view_id':[view_id],
			'type': 'ir.actions.act_window',
			'context': {},
			"domain":domain,
		}

	@api.multi
	def export_excel(self):
		self.ensure_one()
		datas = {
			'model': 'wizard.product.outgoing',
			'from_date' : self.from_date,
			'to_date' : self.to_date,
			'product_type':self.product_type,
			'shipment_type':self.shipment_type,
			}
		
		return {
				'type': 'ir.actions.report.xml',
				'report_name': 'beacukai.in.form.xls',
				'report_type': 'xls',
				'datas': datas,
				}
wizard_product_outgoing()