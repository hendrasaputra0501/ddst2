import re
import time
from odoo.report import report_sxw
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from openerp.api import Environment

from odoo import models, fields, api, _
import cStringIO
from datetime import datetime
 
_product_type = {
	'finish_good':'Hasil Produksi',
	'raw_material':'Bahan Baku',
	'auxiliary_material':'Bahan Penolong',
	'tools':'Alat-alat',
	'waste':'Waste/Scrap',
	'asset':'Aset',
	'others':'Barang Lainnya',
}

class AttrDict(dict):
	def __init__(self, *args, **kwargs):
		super(AttrDict, self).__init__(*args, **kwargs)
		self.__dict__ = self

class beacukai_report_parser(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context=None):
		if context is None:
			context = {}
		super(beacukai_report_parser, self).__init__(cr, uid, name, context=context)
		self.env = Environment(cr, uid, context)

		report_title, shipment_type = "", ""
		if context.get('active_model',False) == 'beacukai.document.line.in':
			report_title = 'Laporan Penerimaan Barang PER DOKUMEN PABEAN'
			shipment_type = 'in'
		elif context.get('active_model',False) == 'beacukai.document.line.out':
			report_title = 'Laporan Pengeluaran Barang PER DOKUMEN PABEAN'
			shipment_type = 'out'
		self.localcontext.update({
			'time': time,
			'period_avail' : False,
			'report_title' : report_title,
			'shipment_type' : shipment_type,
			'product_type' : False,
			})
		
	def set_context(self, objects, data, ids, report_type=None):
		context_report_values = {}
		if data.get('model',False) in ('wizard.product.incoming','wizard.product.outgoing'):
			shipment_type = data['shipment_type']
			BeacukaiLine = self.env['beacukai.document.line']
			if shipment_type=='in':
				report_title = "Laporan Penerimaan"
			else:
				if data['product_type'] == 'waste':
					report_title = "Laporan Penyelesaian"
				else:
					report_title = "Laporan Pengeluaran"
		
			objects = BeacukaiLine.search([
							('registration_date','>=',data['from_date']),
							('registration_date','<=',data['to_date']),
							('shipment_type','=',data['shipment_type']),
							('product_id.product_type','=',data['product_type']),
							])
			if data.get('product_type',False):
				report_title = "%s %s"%(report_title,_product_type.get(data['product_type']))

			context_report_values.update({
				'report_title': report_title,
				'period_avail' : True,
				'shipment_type': shipment_type,
				'product_type' : data['product_type'],
				'start_date' : datetime.strptime(data['from_date'],'%Y-%m-%d').strftime('%d/%m/%Y'),
				'end_date' : datetime.strptime(data['to_date'],'%Y-%m-%d').strftime('%d/%m/%Y'),
				})
		self.localcontext.update(context_report_values)

		return super(beacukai_report_parser, self).set_context(
			objects, data, objects.ids, report_type=report_type)

_document_type = {
	'23':'BC 2.3',
	'25':'BC 2.5',
	'261':'BC 2.61',
	'262':'BC 2.62',
	'27in':'BC 2.7 Masukan',
	'27out':'BC 2.7 Keluaran',
	'30':'BC 3.0',
	'40':'BC 4.0',
	'41':'BC 4.1',
}

class beacukai_report_xlsx(ReportXlsx):
	def __init__(self, name, table, rml=False, parser=False, header=True,
				 store=False):
		super(beacukai_report_xlsx, self).__init__(name, table, rml, parser, header, store)

		# main sheet which will contains report
		self.sheet = None

		# columns of the report
		self.columns = {
				0: {'header': _('No.'), 'field': 'sequence', 'type':'amount', 'width': 4},
				1: {'header': _('Jenis Dokumen'), 'field': 'document_type', 'width': 10},
				2: {'header': _('Nomor'), 'field': 'registration_no', 'width': 12},
				3: {'header': _('Tanggal'), 'field': 'registration_date', 'width': 8},
				4: {'header': _('Nomor'), 'field': 'picking_no', 'width': 12},
				5: {'header': _('Tanggal'), 'field': 'picking_date', 'width': 8},
				6: {'header': _('Partner'), 'field': 'partner', 'width': 30},
				7: {'header': _('Kode Barang'), 'field': 'product_code', 'width': 15},
				8: {'header': _('Nama Barang'), 'field': 'product_name', 'width': 30},
				9: {'header': _('Sat'), 'field': 'partner', 'width': 8},
				10: {'header': _('Jumlah'), 'field': 'product_qty', 'type': 'amount', 'width': 15},
				11: {'header': _('Currency'), 'field': 'currency', 'width': 7},
				12: {'header': _('Harga Pemberian'), 'field': 'amount', 'type': 'amount', 'width': 15},
			}

		# row_pos must be incremented at each writing lines
		self.row_pos = 0
	
	# document_type = _document_type.copy()
	def generate_xlsx_report(self, workbook, data, objects):
		parser = AttrDict(self.parser_instance.localcontext)
		report_name = parser.report_title
		self.sheet = workbook.add_worksheet(report_name and len(report_name)>=31 and report_name[:31] or  report_name)
		ws = self.sheet
		ws.set_landscape()  # Landscape
		
		row_pos = self.row_pos

		# Title
		# Title
		title_cell_style = workbook.add_format({'bold': True, 'font_size':11})
		ws.merge_range(row_pos, 0, row_pos, 11, report_name, title_cell_style)
		row_pos += 1
		title2 = "Kawasan Berikat %s"%parser.company.partner_id.name
		ws.merge_range(row_pos, 0, row_pos, 11, title2, title_cell_style)
		row_pos += 1

		if parser.period_avail:
			title3 = "Periode %s s.d %s"%(parser.start_date, parser.end_date)
			ws.merge_range(row_pos, 0, row_pos, 11, title3, title_cell_style)
			row_pos += 1
		
		# write empty row
		for col_pos, column in self.columns.iteritems():
			ws.set_column(col_pos, col_pos, column['width'])
			ws.write(row_pos, col_pos, "")
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
		ws.merge_range(row_pos, 0, row_pos+1, 0, "No.", header_column_style)
		ws.merge_range(row_pos, 1, row_pos+1, 1, "Jenis\nDokumen", header_column_style)
		ws.merge_range(row_pos, 2, row_pos, 3, "Dokumen Pabean", header_column_style)
		ws.write(row_pos+1, 2, "Nomor", header_column_style)
		ws.write(row_pos+1, 3, "Tanggal", header_column_style)
		ws.merge_range(row_pos, 4, row_pos, 5, parser.shipment_type=='in' and "Bukti Penerimaan Barang" or "Bukti / Dokumen Pengeluaran", header_column_style)
		ws.write(row_pos+1, 4, "Nomor", header_column_style)
		ws.write(row_pos+1, 5, "Tanggal", header_column_style)
		ws.merge_range(row_pos, 6, row_pos+1, 6, (parser.shipment_type=='in' and 'Supplier' or (parser.shipment_type=='out' and 'Customer' or 'Invalid Partner')), header_column_style)
		ws.merge_range(row_pos, 7, row_pos+1, 7, "Kode\nBarang", header_column_style)
		ws.merge_range(row_pos, 8, row_pos+1, 8, "Nama Barang", header_column_style)
		ws.merge_range(row_pos, 9, row_pos+1, 9, "Sat", header_column_style)
		ws.merge_range(row_pos, 10, row_pos+1, 10, "Jumlah", header_column_style)
		ws.merge_range(row_pos, 11, row_pos+1, 12, "Nilai Barang", header_column_style)
		
		row_pos+=2
		ws.freeze_panes(row_pos,0)
		
		# cell styles for detail lines
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
		ll_cell_style_datetime = workbook.add_format({
			'font_size':8,
			#Align
			'align':'right',
			'valign':'top',
			'text_wrap':True,
			#border
			'border':1,
			'border_color':'black',
			#number
			'num_format':'dd/mm/yy'
			})
		cnt = 0
		
		for line in objects:
			cnt += 1
			
			ws.write_number(row_pos, 0, cnt, ll_cell_style)
			ws.write_string(row_pos, 1, _document_type.get(line.document_type,False) and _document_type[line.document_type] or '', ll_cell_style)
			ws.write_string(row_pos, 2, line.registration_no or '', ll_cell_style)
			if line.registration_date!=False:
				ws.write_datetime(row_pos, 3, datetime.strptime(line.registration_date, '%Y-%m-%d'), ll_cell_style_datetime)
			else:
				ws.write_string(row_pos, 3, '', ll_cell_style)

			ws.write_string(row_pos, 4, line.picking_no or '', ll_cell_style)
			if line.picking_date!=False:
				ws.write_datetime(row_pos, 5, datetime.strptime(line.picking_date, '%Y-%m-%d'), ll_cell_style_datetime)
			else:
				ws.write_string(row_pos, 5, '', ll_cell_style)
			
			ws.write_string(row_pos, 6, (line.shipment_type=='in' and (line.source_partner_id and line.source_partner_id.name or '') or (line.dest_partner_id and line.dest_partner_id.name or '')) or '', ll_cell_style)
			ws.write_string(row_pos, 7, line.product_id and line.product_id.default_code or '', ll_cell_style)
			ws.write_string(row_pos, 8, line.product_id and line.product_id.name or '', ll_cell_style)
			ws.write_string(row_pos, 9, line.product_uom and line.product_uom.name or '', ll_cell_style)
			ws.write_number(row_pos, 10, line.product_qty or 0.0, ll_cell_style_decimal)
			ws.write_string(row_pos, 11, line.currency_id and line.currency_id.name or '', ll_cell_style)
			ws.write_number(row_pos, 12, line.price_subtotal or 0.0, ll_cell_style_decimal)
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

beacukai_report_xlsx('report.beacukai.incoming_doc_xlsx','beacukai.document.line', parser=beacukai_report_parser, header=False)
beacukai_report_xlsx('report.beacukai.outgoing_doc_xlsx','beacukai.document.line', parser=beacukai_report_parser, header=False)
