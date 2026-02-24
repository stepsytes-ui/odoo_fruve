# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class EmployeeWarning(models.Model):
    _name = 'employee.warning'
    _description = 'Amonestaciones de Empleados'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'warning_date desc'

    # Folio auto-incrementable
    name = fields.Char(
        string='Folio',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )

    # Fecha (día actual)
    warning_date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    # Usuario que registra la amonestación
    registered_by_id = fields.Many2one(
        'res.users',
        string='Registra',
        default=lambda self: self.env.user.id,
        readonly=True,
        required=True
    )

    # Empleado amonestado (con búsqueda por biometric_id)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Amonestado',
        required=True,
        tracking=True
    )

    # Número de empleado (biometric_id)
    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )

    # Nombre del empleado
    employee_name = fields.Char(
        string='Nombre',
        related='employee_id.name',
        store=True,
        readonly=True
    )

    # Departamento del empleado
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )

    # Turno del empleado
    turno_id = fields.Many2one(
        'shift.management',
        string='Turno',
        related='employee_id.turno_id',
        store=True,
        readonly=True
    )

    # Supervisor (usuarios del grupo supervisor de tiempo extra)
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        required=True,
        tracking=True,
        domain=lambda self: [('groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])]
    )

    # Causa de la amonestación
    causa = fields.Text(
        string='Causa',
        required=True,
        tracking=True
    )

    # Comentarios del supervisor
    supervisor_comments = fields.Text(
        string='Comentarios del Supervisor',
        tracking=True
    )

    # Compañía
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='employee_id.company_id',
        store=True,
        readonly=True,
        index=True,
        groups="base.group_multi_company"
    )

    # Estado de la amonestación
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('submitted', 'Solicitud Enviada'),
            ('approved', 'Aprobada'),
            ('rejected', 'Rechazada'),
        ],
        string='Estado',
        default='draft',
        required=True,
        readonly=True,
        tracking=True
    )

    # Usuario a notificar (encargado de amonestaciones)
    notification_user_id = fields.Many2one(
        'res.users',
        string='Usuario a Notificar',
        required=True,
        tracking=True,
        help='Usuario que recibirá la notificación de la amonestación pendiente'
    )

    # Comentarios de rechazo (solo si es rechazada)
    rejection_reason = fields.Text(
        string='Motivo del Rechazo',
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generar el folio automáticamente al crear una amonestación"""
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.warning') or _('Nuevo')

        return super(EmployeeWarning, self).create(vals_list)

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

    def _send_notification_email(self):
        """Enviar correo de notificación al usuario designado"""
        if not self.notification_user_id:
            return
        
        mail_template = self.env.ref('employee_modifications.email_template_warning_notification', raise_if_not_found=False)
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)

    def action_submit(self):
        """Enviar la solicitud para aprobación"""
        for warning in self:
            warning.write({'state': 'submitted'})
            warning._send_notification_email()

    def action_approve(self):
        """Aprobar la amonestación"""
        for warning in self:
            warning.write({'state': 'approved'})

    def action_reject(self):
        """Rechazar la amonestación (abre el diálogo para ingresar el motivo)"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.warning.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_warning_id': self.id}
        }

    def action_reset_to_draft(self):
        """Regresar el estado a borrador"""
        for warning in self:
            warning.write({'state': 'draft', 'rejection_reason': False})
