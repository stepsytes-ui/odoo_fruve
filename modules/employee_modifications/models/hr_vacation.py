# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HrVacation(models.Model):
    _name = 'hr.vacation'
    _description = 'Vacaciones de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nueva'),
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        tracking=True,
        index=True
    )
    
    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )
    
    employee_name = fields.Char(
        string='Nombre del Empleado',
        related='employee_id.name',
        store=True,
        readonly=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )
    
    turno_id = fields.Many2one(
        'shift.management',
        string='Turno',
        related='employee_id.turno_id',
        store=True,
        readonly=True
    )
    
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        tracking=True,
        help='Supervisor asignado (del grupo Supervisor Tiempo Extra)'
    )
    
    registered_by_id = fields.Many2one(
        'res.users',
        string='Registrado Por',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    date_from = fields.Date(
        string='Fecha Inicio',
        required=True,
        tracking=True,
        default=fields.Date.today
    )
    
    date_to = fields.Date(
        string='Fecha Fin',
        required=True,
        tracking=True
    )
    
    duration_days = fields.Float(
        string='Duración (Días)',
        compute='_compute_duration',
        store=True,
        help='Duración en días de las vacaciones'
    )
    
    vacation_days_available = fields.Float(
        string='Días Disponibles',
        help='Días de vacaciones disponibles al momento de la solicitud'
    )
    
    employee_antiguedad = fields.Char(
        string='Antigüedad',
        help='Antigüedad del empleado al momento de la solicitud'
    )
    
    description = fields.Text(
        string='Descripción',
        tracking=True
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Relacionada',
        readonly=True,
        help='Ausencia de tipo Vacaciones que creó este registro'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('validate1', 'Primera Aprobación'),
        ('validate', 'Aprobado'),
        ('refuse', 'Rechazado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', tracking=True, required=True)

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        """Calcula la duración de las vacaciones en días"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(_('La fecha de fin no puede ser anterior a la fecha de inicio.'))
                
                delta = record.date_to - record.date_from
                record.duration_days = delta.days + 1  # +1 para incluir ambos días
            else:
                record.duration_days = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el número de referencia automáticamente"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.vacation') or _('Nueva')
        
        return super(HrVacation, self).create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Valida que las fechas sean coherentes"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(_('La fecha de fin debe ser posterior a la fecha de inicio.'))

    def action_draft(self):
        """Cambia el estado a borrador"""
        self.write({'state': 'draft'})

    def action_confirm(self):
        """Confirma las vacaciones"""
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Valida las vacaciones"""
        self.write({'state': 'validate'})

    def action_refuse(self):
        """Rechaza las vacaciones"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela las vacaciones"""
        self.write({'state': 'cancel'})
    
    def action_open_leave(self):
        """Abre el registro de hr.leave relacionado"""
        self.ensure_one()
        if self.leave_id:
            return {
                'name': 'Solicitud de Vacaciones',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.leave',
                'res_id': self.leave_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
