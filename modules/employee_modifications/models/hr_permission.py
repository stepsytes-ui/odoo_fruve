# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HrPermission(models.Model):
    _name = 'hr.permission'
    _description = 'Permisos de Empleado'
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
    
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        tracking=True,
        help='Supervisor asignado (del grupo Supervisor Tiempo Extra)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    date_from = fields.Datetime(
        string='Fecha Inicio',
        required=True,
        tracking=True,
        default=fields.Datetime.now
    )
    
    date_to = fields.Datetime(
        string='Fecha Fin',
        required=True,
        tracking=True
    )
    
    duration_days = fields.Float(
        string='Duración (Días)',
        compute='_compute_duration',
        store=True,
        help='Duración en días del permiso'
    )
    
    permission_type = fields.Char(
        string='Tipo de Permiso',
        tracking=True,
        help='Tipo de permiso (extraído del nombre del tipo de ausencia)'
    )
    
    reason = fields.Text(
        string='Motivo del Permiso',
        tracking=True
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Relacionada',
        readonly=True,
        help='Ausencia de tipo Permiso que creó este registro'
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
        """Calcula la duración del permiso en días"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError(_('La fecha de fin no puede ser anterior a la fecha de inicio.'))
                
                delta = record.date_to - record.date_from
                record.duration_days = delta.total_seconds() / 86400  # 86400 segundos = 1 día
            else:
                record.duration_days = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el número de referencia automáticamente"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.permission') or _('Nueva')
        
        return super(HrPermission, self).create(vals_list)

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
        """Confirma el permiso"""
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Valida el permiso"""
        self.write({'state': 'validate'})

    def action_refuse(self):
        """Rechaza el permiso"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela el permiso"""
        self.write({'state': 'cancel'})
