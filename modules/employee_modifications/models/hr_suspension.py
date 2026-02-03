# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class HrSuspension(models.Model):
    _name = 'hr.suspension'
    _description = 'Suspensión de Empleado'
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
    
    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        domain=lambda self: [('user_id.groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])],
        required=True,
        tracking=True,
        help='Supervisor asignado (debe pertenecer al grupo Supervisor Tiempo Extra)'
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
        help='Duración en días de la suspensión'
    )
    
    reason = fields.Text(
        string='Motivo de la Suspensión',
        required=True,
        tracking=True
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Relacionada',
        readonly=True,
        help='Ausencia de tipo Suspensión que creó este registro'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmada'),
        ('validate', 'Aprobada'),
        ('refuse', 'Rechazada'),
        ('cancel', 'Cancelada')
    ], string='Estado', default='draft', tracking=True, required=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    notes = fields.Html(
        string='Notas Adicionales',
        tracking=True
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generar el folio automáticamente al crear una suspensión"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.suspension') or _('Nueva')
        return super(HrSuspension, self).create(vals_list)

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        """Calcula la duración en días de la suspensión"""
        for suspension in self:
            if suspension.date_from and suspension.date_to:
                delta = suspension.date_to - suspension.date_from
                suspension.duration_days = delta.days + (delta.seconds / 86400.0)
            else:
                suspension.duration_days = 0.0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Valida que la fecha de fin sea posterior a la fecha de inicio"""
        for suspension in self:
            if suspension.date_from and suspension.date_to:
                if suspension.date_to <= suspension.date_from:
                    raise ValidationError(
                        _('La fecha de fin debe ser posterior a la fecha de inicio.')
                    )

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_overlapping_suspensions(self):
        """Valida que no existan suspensiones superpuestas para el mismo empleado"""
        for suspension in self:
            if suspension.state in ['cancel', 'refuse']:
                continue
                
            domain = [
                ('employee_id', '=', suspension.employee_id.id),
                ('id', '!=', suspension.id),
                ('state', 'not in', ['cancel', 'refuse']),
                ('date_from', '<', suspension.date_to),
                ('date_to', '>', suspension.date_from),
            ]
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _('Ya existe una suspensión para %s en el período del %s al %s.') % (
                        suspension.employee_id.name,
                        overlapping.date_from.strftime('%Y-%m-%d %H:%M'),
                        overlapping.date_to.strftime('%Y-%m-%d %H:%M')
                    )
                )

    def action_confirm(self):
        """Confirma la suspensión"""
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Aprueba la suspensión"""
        self.write({'state': 'validate'})

    def action_refuse(self):
        """Rechaza la suspensión"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela la suspensión"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Regresa la suspensión a borrador"""
        self.write({'state': 'draft'})

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permitir búsqueda por número de empleado (biometric_id) en campos Many2one
        """
        if domain is None:
            domain = []
        
        if name:
            # Buscar por folio, biometric_id o nombre del empleado
            domain = ['|', '|', 
                      ('name', operator, name),
                      ('biometric_id', operator, name),
                      ('employee_name', operator, name)]
        
        return self._search(domain, limit=limit, order=order)
