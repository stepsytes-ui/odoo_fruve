# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class EmployeeWarning(models.Model):
    _name = 'employee.warning'
    _description = 'Amonestaciones de Empleados'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'warning_date desc'
    _check_company_auto = True

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
        check_company=True,
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
        """Enviar correo de notificación y crear actividad para el usuario designado"""
        if not self.notification_user_id:
            _logger.warning(f"[AMONESTACIONES] No hay usuario a notificar para la amonestación {self.name}")
            return
        
        # Verificar que el usuario tenga email
        if not self.notification_user_id.partner_id or not self.notification_user_id.partner_id.email:
            _logger.warning(f"[AMONESTACIONES] El usuario {self.notification_user_id.name} no tiene email configurado")
            return
        
        try:
            # Construir la URL del registro
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            warning_url = f"{base_url}/web#id={self.id}&view_type=form&model=employee.warning"
            
            # Construir el asunto y cuerpo del correo
            subject = _(" Amonestación Pendiente de Aprobación - %s") % self.name
            
            body = _("""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #007bff; border-bottom: 3px solid #007bff; padding-bottom: 10px;">
                         Amonestación Pendiente de Aprobación
                    </h2>
                    
                    <p>Estimado/a <strong>%s</strong>,</p>
                    
                    <p>Se ha enviado una nueva amonestación que requiere su aprobación o rechazo:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; border-radius: 4px;">
                        <p style="margin: 5px 0;"><strong>Folio:</strong> %s</p>
                        <p style="margin: 5px 0;"><strong>Empleado:</strong> %s (%s)</p>
                        <p style="margin: 5px 0;"><strong>Departamento:</strong> %s</p>
                        <p style="margin: 5px 0;"><strong>Supervisor:</strong> %s</p>
                        <p style="margin: 5px 0;"><strong>Fecha:</strong> %s</p>
                        <p style="margin: 5px 0;"><strong>Motivo:</strong> %s</p>
                    </div>
                    
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="%s" 
                           style="display: inline-block; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  background-color: #007bff; 
                                  color: white; 
                                  border-radius: 5px; 
                                  font-weight: bold;">
                            Ver Amonestación para Aprobar/Rechazar →
                        </a>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; border-radius: 4px;">
                        <p style="margin: 0; color: #856404; font-size: 13px;">
                            <strong>Nota:</strong> Esta amonestación está en estado <strong>Solicitud Enviada</strong> 
                            y espera su revisión para ser aprobada o rechazada.
                        </p>
                    </div>
                    
                    <p style="color: #777; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px;">
                        Este es un correo automático. Por favor, no responda directamente a este correo.
                    </p>
                </div>
            """) % (
                self.notification_user_id.name,
                self.name,
                self.employee_name,
                self.biometric_id or 'N/A',
                self.department_id.name if self.department_id else 'N/A',
                self.supervisor_id.name,
                self.warning_date.strftime('%d/%m/%Y') if self.warning_date else 'N/A',
                self.causa[:100] + '...' if len(self.causa) > 100 else self.causa,
                warning_url
            )
            
            # Enviar el correo
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body,
                'recipient_ids': [(4, self.notification_user_id.partner_id.id)],
                'email_from': self.env['ir.config_parameter'].sudo().get_param('mail.catchall.domain') or 'noreply@fruvemex.com',
                'auto_delete': True,
            })
            mail.send()
            _logger.info(f"[AMONESTACIONES] Correo enviado a {self.notification_user_id.name} para la amonestación {self.name}")
            
            # Crear actividad para el usuario notificado
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([('name', 'in', ['To Do', 'Para hacer'])], limit=1)
            
            if activity_type:
                warning_model_id = self.env['ir.model']._get('employee.warning').id
                
                self.env['mail.activity'].sudo().create({
                    'res_id': self.id,
                    'res_model_id': warning_model_id,
                    'activity_type_id': activity_type.id,
                    'summary': _("Revisar: Amonestación Pendiente"),
                    'note': _("La amonestación **%s** del empleado **%s** requiere aprobación o rechazo.") % (self.name, self.employee_name),
                    'date_deadline': fields.Date.today(),
                    'user_id': self.notification_user_id.id,
                })
                _logger.info(f"[AMONESTACIONES] Actividad creada para {self.notification_user_id.name}")
            
        except Exception as e:
            _logger.error(f"[AMONESTACIONES] Error al enviar notificación para la amonestación {self.name}: {e}", exc_info=True)

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
