from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class beacukai_confirm(models.TransientModel):
	"""
	This wizard will confirm the all the selected draft invoices
	"""

	_name = "beacukai.confirm"
	_description = "Confirm the selected BCs"

	@api.multi
	def beacukai_confirm(self, cr, uid, ids, context=None):
		context = self._context
		data_bc = self.env['beacukai.document'].browse(context['active_ids'])
		for record in data_bc:
			if record.state not in ['draft']:
				raise ValidationError(_('Warning!'), _("Selected BC(s) cannot be confirmed as they are not in 'Draft' state."))

		self.env['beacukai.document'].action_done(context['active_ids'])
		return {'type': 'ir.actions.act_window_close'}

beacukai_confirm()

class beacukai_cancel(models.TransientModel):
	"""
	This wizard will confirm the all the selected draft invoices
	"""

	_name = "beacukai.cancel"
	_description = "Cancel the selected BCs"

	@api.multi
	def beacukai_cancel(self, cr, uid, ids, context=None):
		context = self._context
		data_bc = self.env['beacukai.document'].browse(context['active_ids'])

		for record in data_bc:
			if record.state not in ('draft','validated'):
				raise ValidationError(_('Warning!'), _("Selected BC(s) cannot be confirmed as they are not in 'Draft' or 'Valid BC' state."))
		
		self.env['beacukai.document'].action_cancel(context['active_ids'])
		return {'type': 'ir.actions.act_window_close'}

beacukai_cancel()

class beacukai_draft(models.TransientModel):
	"""
	This wizard will confirm the all the selected draft invoices
	"""

	_name = "beacukai.draft"
	_description = "Set to Draft the selected BCs"

	@api.multi
	def beacukai_set_draft(self, cr, uid, ids, context=None):
		context = self._context
		data_bc = self.env['beacukai.document'].browse(context['active_ids'])

		for record in data_bc:
			if record.state not in ('cancelled'):
				raise ValidationError(_('Warning!'), _("Selected BC(s) cannot be confirmed as they are not in 'Cancelled' state."))
		
		self.env['beacukai.document'].action_set_draft(context['active_ids'])
		return {'type': 'ir.actions.act_window_close'}

beacukai_draft()