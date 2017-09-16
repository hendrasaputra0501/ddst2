import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.osv.expression import get_unaccent_wrapper

import odoo.addons.decimal_precision as dp

class Partner(models.Model):
	_inherit = "res.partner"

	partner_code = fields.Char('Partner Code', default='/')
	default_currency_id = fields.Many2one('res.currency','Default Currency')
	
	@api.multi
	def name_get(self):
		res = []
		for record in self:
			name = record.name
			if record.partner_code:
				name = "[%s] %s"%(record.partner_code, name)
			if record.parent_id and not record.is_company:
				name = "%s, %s" % (record.parent_name, name)
			if self._context.get('show_address'):
				name = name + "\n" + self._display_address(without_company=True)
				name = name.replace('\n\n','\n')
				name = name.replace('\n\n','\n')
			if self._context.get('show_email') and record.email:
				name = "%s <%s>" % (name, record.email)
			res.append((record.id, name))
		return res

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		if args is None:
			args = []
		if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
			self.check_access_rights('read')
			where_query = self._where_calc(args)
			self._apply_ir_rules(where_query, 'read')
			from_clause, where_clause, where_clause_params = where_query.get_sql()
			where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

			# search on the name of the contacts and of its company
			search_name = name
			if operator in ('ilike', 'like'):
				search_name = '%%%s%%' % name
			if operator in ('=ilike', '=like'):
				operator = operator[1:]

			unaccent = get_unaccent_wrapper(self.env.cr)

			query = """SELECT id
						 FROM res_partner
					  {where} ({email} {operator} {percent}
						   OR {display_name} {operator} {percent}
						   OR {reference} {operator} {percent})
						   -- don't panic, trust postgres bitmap
					 ORDER BY {display_name} {operator} {percent} desc,
							  {display_name}
					""".format(where=where_str,
							   operator=operator,
							   email=unaccent('email'),
							   display_name=unaccent('display_name'),
							   reference=unaccent('ref'),
							   percent=unaccent('%s'))

			where_clause_params += [search_name]*4
			if limit:
				query += ' limit %s'
				where_clause_params.append(limit)
			self.env.cr.execute(query, where_clause_params)
			partner_ids = map(lambda x: x[0], self.env.cr.fetchall())

			if partner_ids:
				return self.browse(partner_ids).name_get()
			else:
				return []
		return super(Partner, self).name_search(name, args, operator=operator, limit=limit)

	@api.model
	def create(self, vals):
		if ('partner_code' not in vals) or (vals.get('partner_code')=='/'):
			seq_obj_name =  self._inherit
			if vals.get('customer',False)==True and vals.get('supplier',False)==False:
				partner_type = '.customer'
			elif vals.get('customer',False)==False and vals.get('supplier',False)==True:
				partner_type = '.supplier'
			else:
				partner_type = '.other'
			
			vals['partner_code'] = self.env['ir.sequence'].next_by_code(seq_obj_name+partner_type)
		res = super(Partner, self).create(vals)
		return res