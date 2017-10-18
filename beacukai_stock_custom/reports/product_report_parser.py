import re
import time
from odoo.report import report_sxw
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from openerp.api import Environment

from odoo import models, fields, api, _
import cStringIO
from datetime import datetime

class AttrDict(dict):
	def __init__(self, *args, **kwargs):
		super(AttrDict, self).__init__(*args, **kwargs)
		self.__dict__ = self
 
class product_report_parser(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context=None):
		if context is None:
			context = {}
		super(product_report_parser, self).__init__(cr, uid, name, context=context)
		self.env = Environment(cr, uid, context)
		
		self.localcontext.update({
			'time': time,
		})

	@api.model
	def _get_mutation(self, products, context=None):
		# product_obj = self.env['product.product']
		ctx = {
			'states': context.get('states',[]),
			'move_type': context.get('move_type',[]),
			'from_date' : context.get('from_date',False),
			'to_date' : context.get('to_date',False),
		}
		return products.with_context(ctx)._product_mutation()

	def set_context(self, objects, data, ids, report_type=None):
		product_obj = self.env['product.product']
		# product_ids = product_obj.search(self.cr, self.uid, [('product_type','=',data['product_type'])])
		objects = product_obj.browse(ids)

		states = ['done']
		product_opening = self._get_mutation(objects, {'from_date':data['from_date'],'to_date':data['to_date'],\
								'move_type':['all_in', 'all_out'],'states':states})
		product_incoming = self._get_mutation(objects, {'from_date':data['from_date'],'to_date':data['to_date'],\
								'move_type':['in'],'states':states})
		product_outgoing = self._get_mutation(objects, {'from_date':data['from_date'],'to_date':data['to_date'],\
								'move_type':['out'],'states':states})
		product_adjustment = self._get_mutation(objects, {'from_date':data['from_date'],'to_date':data['to_date'],\
								'move_type':['adj_in','adj_out'],'states':states})
		product_closing = self._get_mutation(objects, {'from_date':data['from_date'],'to_date':data['to_date'],\
								'move_type':['all_in','all_out','in','out2','adj_in','adj_out'],'states':states})

		self.localcontext.update({
			'opening': product_opening,
			'incoming': product_incoming,
			'outgoing': product_outgoing,
			'adjustment': product_adjustment,
			'closing': product_closing,
			'start_date' : data['from_date'],
			'end_date' : data['to_date'],
		})

		return super(product_report_parser, self).set_context(
			objects, data, ids, report_type=report_type)


class product_report_xlsx(ReportXlsx):
	def __init__(self, name, table, rml=False, parser=False, header=True,
				 store=False):
		super(product_report_xlsx, self).__init__(name, table, rml, parser, header, store)

		# main sheet which will contains report
		self.sheet = None

		# columns of the report
		self.columns = {
				0: {'header': _('Kode Barang'), 'field': 'code', 'width': 8},
				1: {'header': _('Deskripsi'), 'field': 'name', 'width': 12},
				2: {'header': _('Satuan'), 'field': 'uom', 'width': 8},
				3: {'header': _('Saldo Awal'), 'field': 'opening', 'type': 'amount', 'width': 15},
				4: {'header': _('Pemasukan'), 'field': 'incoming', 'type': 'amount', 'width': 15},
				5: {'header': _('Pengeluaran'), 'field': 'outgoing', 'type': 'amount', 'width': 15},
				6: {'header': _('Penyesuaian'), 'field': 'adjustment', 'type': 'amount', 'width': 15},
				7: {'header': _('Saldo Buku'), 'field': 'closing', 'type': 'amount', 'width': 15},
				8: {'header': _('Stock Opname'), 'field': 'opname', 'type': 'amount', 'width': 15},
				9: {'header': _('Selisih'), 'field': 'selisih', 'type': 'amount', 'width': 15},
			}

		# row_pos must be incremented at each writing lines
		self.row_pos = 0

	def _get_report_name(self):
		return _('Laporan Pertanggungjawaban Barang')

	# def generate_xls_report(self, parser, xls_style, data, objects, wb):
	def generate_xlsx_report(self, workbook, data, objects):
		report_name = self._get_report_name()
		self.sheet = workbook.add_worksheet(report_name and len(report_name)>=31 and report_name[:31] or  report_name)
		ws = self.sheet
		parser = AttrDict(self.parser_instance.localcontext)
		ws.set_landscape()  # Landscape
		
		row_pos = self.row_pos
		# Title
		title_cell_style = workbook.add_format({'bold': True, 'font_size':11})
		ws.merge_range(row_pos, 0, row_pos, 9, report_name, title_cell_style)
		row_pos += 1
		title2 = "Kawasan Berikat %s"%parser.company.partner_id.name
		ws.merge_range(row_pos, 0, row_pos, 9, title2, title_cell_style)
		row_pos += 1
		# write empty row
		ws.write(row_pos, 0, "")
		row_pos += 1
		# Header Table
		header_column_style = workbook.add_format({
			#font
			'font_size':8,
			'bold':True,
			#Align
			'align':'center',
			#patter
			'pattern':1,
			'fg_color':'#C0C0C0',
			#border
			'border':1,
			'border_color':'black',
			})
		for col_pos, column in self.columns.iteritems():
			ws.set_column(col_pos, col_pos, column['width'])
			ws.write(row_pos, col_pos, column['header'],
							 header_column_style)
		row_pos += 1
		ws.freeze_panes(row_pos,0)
		
		# cell styles for products lines
		ll_cell_style = workbook.add_format({
			'font_size':8,
			#Align
			'valign':'top',
			'text_wrap':True,
			#border
			'border':1,
			'border_color':'black',
			})
		ll_cell_style_decimal = workbook.add_format({
			'font_size':8,
			#Align
			'align':'right',
			'valign':'top',
			'text_wrap':True,
			#border
			'border':1,
			'border_color':'black',
			#number
			'num_format':'#,##0.00'
			})
		
		cnt = 0
		for product in objects:
			cnt += 1
			# only export with the transaction qty
			trans_qty = []
			for col_pos, column in self.columns.iteritems():
				if column['field'] in ['opening','incoming','outgoing','adjustment','closing']:
					trans_qty.append(parser[column['field']].get(product.id,0.0))
			if not any(trans_qty):
				continue
			for col_pos, column in self.columns.iteritems():
				value = None
				if column['field']=='code':
					value = product.code or ''
				if column['field']=='name':
					value = product.name or ''
				if column['field']=='uom':
					value = product.uom_id and product.uom_id.name or ''
				if column['field'] in ['opening','incoming','outgoing','adjustment','closing']:
					value = parser[column['field']].get(product.id,0.0)
				if column['field'] in ['opname','selisih']:
					value = 0.0
				value = (value is not None) and value or False
				cell_type = column.get('type', 'string')
				if cell_type == 'string':
					ws.write_string(row_pos, col_pos, value or '', ll_cell_style)
				elif cell_type == 'amount':
					ws.write_number(row_pos, col_pos, float(value), ll_cell_style_decimal)
			row_pos += 1
		
		# print setup
		ws.print_area(0, 0, row_pos, 9) #print area of selected cell
		# ws.set_margins(3, 3, 3, 3) 
		ws.repeat_rows(0,3) #repeat header
		ws.set_paper(9)  # set A4 as page format
		pages_horz = 1 # wide
		pages_vert = 0 # as long as necessary
		ws.fit_to_pages(pages_horz, pages_vert)
		
		pass

product_report_xlsx('report.product.mutation_report_xlsx','product.product', parser=product_report_parser, header=False)