# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeResguardoAssignWizard(models.TransientModel):
    _name = 'employee.resguardo.assign.wizard'
    _description = 'Asistente para Asignar Resguardo al Empleado'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)
    fecha_entrega = fields.Date(string='Fecha de Entrega', required=True, default=fields.Date.today)
    responsable_rh_id = fields.Many2one('res.users', string='Responsable RH', default=lambda self: self.env.user, required=True)
    notas = fields.Text(string='Notas')

    line_ids = fields.One2many('employee.resguardo.assign.wizard.line', 'wizard_id', string='Objetos a Asignar')

    @api.constrains('line_ids')
    def _check_lines_not_empty(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError(_('Debe agregar al menos un objeto para crear el resguardo.'))

    def action_confirm_assign(self):
        self.ensure_one()

        if not self.line_ids:
            raise ValidationError(_('Debe agregar al menos un objeto para crear el resguardo.'))

        resguardo = self.env['employee.resguardo'].create({
            'employee_id': self.employee_id.id,
            'fecha_entrega': self.fecha_entrega,
            'responsable_rh_id': self.responsable_rh_id.id,
            'notas': self.notas,
            'line_ids': [
                (0, 0, {
                    'asset_id': line.asset_id.id,
                    'quantity_object': line.quantity_object,
                    # 'funcionando_al_entregar': line.funcionando_al_entregar,
                    'observaciones': line.observaciones,
                })
                for line in self.line_ids
            ],
        })

        self.employee_id.write({'has_resguardo': 'si'})

        return {
            'name': _('Resguardo'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.resguardo',
            'res_id': resguardo.id,
            'view_mode': 'form',
            'target': 'current',
        }


class EmployeeResguardoAssignWizardLine(models.TransientModel):
    _name = 'employee.resguardo.assign.wizard.line'
    _description = 'Linea de Asignacion de Resguardo'

    wizard_id = fields.Many2one('employee.resguardo.assign.wizard', required=True, ondelete='cascade')
    asset_id = fields.Many2one('employee.resguardo.asset', string='Objeto', required=True)
    quantity_object = fields.Integer(string='Cantidad', required=True, default=1)
    tipo_resguardo = fields.Selection(related='asset_id.tipo_resguardo', string='Tipo', readonly=True)
    # funcionando_al_entregar = fields.Boolean(string='Funcionando al Entregar', default=True)
    observaciones = fields.Text(string='Observaciones')

    @api.constrains('quantity_object')
    def _check_quantity_object_positive(self):
        for record in self:
            if record.quantity_object < 1:
                raise ValidationError(_('La cantidad debe ser mayor a 0.'))

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        return
