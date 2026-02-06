# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HrIncapacity(models.Model):
    _name = 'hr.incapacity'
    _description = 'Incapacidad de Empleado'
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
    
    total_days = fields.Integer(
        string='Total Días',
        required=True,
        tracking=True,
        help='Número total de días de incapacidad'
    )
    
    incapacity_type = fields.Selection([
        ('riesgo_trabajo', 'Riesgo Trabajo'),
        ('enfermedad_trabajo', 'Enfermedad Trabajo'),
        ('enfermedad_general', 'Enfermedad General'),
        ('maternidad', 'Maternidad')
    ], string='Motivo', required=True, tracking=True)
    
    comments = fields.Text(
        string='Comentarios',
        tracking=True
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Relacionada',
        readonly=True,
        help='Ausencia de tipo Incapacidad que creó este registro'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmada'),
        ('validate', 'Aprobada'),
        ('refuse', 'Rechazada'),
        ('cancel', 'Cancelada')
    ], string='Estado', default='draft', tracking=True, required=True)
    
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
        """Generar el folio automáticamente al crear una incapacidad"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.incapacity') or _('Nueva')
        return super(HrIncapacity, self).create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_dates_and_days(self):
        """Valida que la fecha de fin sea posterior a la fecha de inicio"""
        for incapacity in self:
            if incapacity.date_from and incapacity.date_to:
                if incapacity.date_to < incapacity.date_from:
                    raise ValidationError(
                        _('La fecha de fin debe ser posterior a la fecha de inicio.')
                    )

    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_overlapping_incapacities(self):
        """Valida que no existan incapacidades superpuestas para el mismo empleado"""
        for incapacity in self:
            if incapacity.state in ['cancel', 'refuse']:
                continue
                
            domain = [
                ('employee_id', '=', incapacity.employee_id.id),
                ('id', '!=', incapacity.id),
                ('state', 'not in', ['cancel', 'refuse']),
                ('date_from', '<=', incapacity.date_to),
                ('date_to', '>=', incapacity.date_from),
            ]
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _('Ya existe una incapacidad para %s en el período del %s al %s.') % (
                        incapacity.employee_id.name,
                        overlapping.date_from.strftime('%Y-%m-%d'),
                        overlapping.date_to.strftime('%Y-%m-%d')
                    )
                )

    def action_confirm(self):
        """Confirma la incapacidad"""
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Aprueba la incapacidad"""
        self.write({'state': 'validate'})

    def action_refuse(self):
        """Rechaza la incapacidad"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela la incapacidad"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Regresa la incapacidad a borrador"""
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
