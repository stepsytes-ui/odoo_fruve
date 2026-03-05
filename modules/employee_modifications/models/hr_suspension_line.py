# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrSuspensionLine(models.Model):
    """Línea de suspensión para suspensiones no continuas"""
    _name = 'hr.suspension.line'
    _description = 'Línea de Suspensión'
    _order = 'suspension_date asc, id asc'
    
    suspension_id = fields.Many2one(
        'hr.suspension',
        string='Suspensión',
        required=True,
        ondelete='cascade'
    )
    
    suspension_date = fields.Date(
        string='Fecha de Suspensión',
        required=True,
        help='Fecha en la que se aplicará la suspensión'
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Creada',
        readonly=True,
        help='Ausencia generada para esta línea de suspensión'
    )
    
    @api.constrains('suspension_date', 'suspension_id')
    def _check_duplicate_dates(self):
        """Valida que no haya fechas duplicadas en la misma suspensión"""
        for line in self:
            duplicates = self.search([
                ('suspension_id', '=', line.suspension_id.id),
                ('suspension_date', '=', line.suspension_date),
                ('id', '!=', line.id)
            ])
            if duplicates:
                raise ValidationError(
                    _('No se puede tener la misma fecha de suspensión duplicada en el mismo registro.')
                )
