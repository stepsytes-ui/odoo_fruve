# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
import pytz


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
        'res.users',
        string='Supervisor',
        domain=lambda self: [('groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])],
        tracking=True,
        help='Supervisor asignado (debe pertenecer al grupo Supervisor Tiempo Extra)'
    )
    
    date_from = fields.Date(
        string='Fecha Inicio',
        required=True,
        tracking=True
    )
    
    total_days = fields.Integer(
        string='Días Totales',
        default=1,
        required=True,
        tracking=True,
        help='Cantidad de días de la suspensión (considerando días laborables)'
    )
    
    date_to = fields.Date(
        string='Fecha Fin',
        compute='_compute_date_to',
        store=True,
        tracking=True,
        help='Fecha de fin calculada automáticamente'
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

    @api.depends('date_from', 'total_days', 'employee_id')
    def _compute_date_to(self):
        """Calcula la fecha de fin considerando días laborables, descansos y festivos"""
        for suspension in self:
            if suspension.date_from and suspension.total_days and suspension.employee_id:
                # Obtener el calendario laboral del empleado
                calendar = suspension.employee_id.resource_calendar_id
                
                if not calendar:
                    # Si no hay calendario configurado, usar cálculo simple
                    suspension.date_to = suspension.date_from + timedelta(days=suspension.total_days - 1)
                else:
                    try:
                        # Calcular la fecha final agregando días laborables
                        # Iterar día a día desde date_from hasta contar total_days días laborables
                        current_date = suspension.date_from
                        days_counted = 0
                        
                        while days_counted < suspension.total_days:
                            # Convertir a datetime con timezone para verificar si es día laboral
                            tz = pytz.timezone(calendar.tz or 'UTC')
                            check_datetime = tz.localize(datetime.combine(current_date, datetime.min.time()))
                            
                            is_working_day = False
                            
                            # Intentar obtener intervalos de trabajo
                            try:
                                intervals = calendar._get_working_intervals_data(
                                    check_datetime,
                                    check_datetime + timedelta(hours=24),
                                    resource=suspension.employee_id.resource_id
                                )
                                
                                # Verificar si hay horas de trabajo registradas
                                if intervals:
                                    for resource_id, interval_list in intervals.items():
                                        if interval_list:  # Si hay intervalos, es un día laboral
                                            is_working_day = True
                                            break
                            except:
                                # Intentar método alternativo
                                try:
                                    day_data = calendar._get_work_hours_data(
                                        check_datetime,
                                        resources=suspension.employee_id.resource_id
                                    )
                                    if day_data:
                                        work_hours = day_data.get(suspension.employee_id.resource_id.id, 0) if suspension.employee_id.resource_id else 0
                                        if work_hours > 0:
                                            is_working_day = True
                                except:
                                    # Si no hay calendario info, asumimos que es laboral
                                    is_working_day = True
                            
                            # Contar el día si es laboral
                            if is_working_day:
                                days_counted += 1
                                if days_counted >= suspension.total_days:
                                    break
                            
                            current_date += timedelta(days=1)
                        
                        suspension.date_to = current_date
                    except Exception:
                        # Último fallback: cálculo simple sin considerar calendario
                        suspension.date_to = suspension.date_from + timedelta(days=suspension.total_days - 1)
            else:
                suspension.date_to = None

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        """Calcula la duración en días de la suspensión"""
        for suspension in self:
            if suspension.date_from and suspension.date_to:
                delta = suspension.date_to - suspension.date_from
                suspension.duration_days = delta.days + 1  # +1 para incluir el día inicial
            else:
                suspension.duration_days = 0.0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Valida que la fecha de fin sea posterior a la fecha de inicio"""
        for suspension in self:
            if suspension.date_from and suspension.date_to:
                if suspension.date_to < suspension.date_from:
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
                ('date_from', '<=', suspension.date_to),
                ('date_to', '>=', suspension.date_from),
            ]
            
            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _('Ya existe una suspensión para %s en el período del %s al %s.') % (
                        suspension.employee_id.name,
                        overlapping.date_from,
                        overlapping.date_to
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Generar el folio automáticamente al crear una suspensión"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.suspension') or _('Nueva')
        return super(HrSuspension, self).create(vals_list)

    def action_confirm(self):
        """Confirma la suspensión"""
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Aprueba la suspensión y crea el registro en hr.leave"""
        self.write({'state': 'validate'})
        # Crear el registro en hr.leave
        for suspension in self:
            suspension._create_leave_record()

    def action_refuse(self):
        """Rechaza la suspensión"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela la suspensión"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Regresa la suspensión a borrador"""
        self.write({'state': 'draft'})

    def _create_leave_record(self):
        """Crea un registro de ausencia (hr.leave) de tipo Suspensión"""
        self.ensure_one()
        
        # Evitar crear múltiples registros
        if self.leave_id:
            return self.leave_id
        
        # Obtener o crear el tipo de ausencia 'Suspensión'
        holiday_status = self.env['hr.leave.type'].search([
            ('name', '=', 'Suspensión')
        ], limit=1)
        
        if not holiday_status:
            raise ValidationError(
                _('No se encontró el tipo de ausencia "Suspensión". Por favor cree uno en Recursos Humanos > Configuración > Tipo de Ausencia.')
            )
        
        # Convertir fechas a datetime naive (hora 00:00:00)
        # Odoo espera datetimes sin timezone para los campos
        date_from = datetime.combine(self.date_from, datetime.min.time())
        date_to = datetime.combine(self.date_to, datetime.min.time())
        
        # Crear el registro de ausencia con un contexto que evita crear una nueva suspensión
        leave_vals = {
            'employee_id': self.employee_id.id,
            'holiday_status_id': holiday_status.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'name': self.reason or ('Suspensión - ' + self.name),
            'supervisor_id': self.supervisor_id.id if self.supervisor_id else False,
            'suspension_id': self.id,  # Vincular el leave con esta suspensión
        }
        
        try:
            # Usar contexto para evitar crear una nueva suspensión desde el leave
            # y permitir la validación automática
            leave = self.env['hr.leave'].with_context(
                skip_suspension_creation=True,
                leave_skip_state_check=True
            ).sudo().create(leave_vals)
            
            # Validar el leave automáticamente con el contexto preservado
            leave.with_context(skip_suspension_creation=True).sudo().action_validate()
            
            self.leave_id = leave.id
            return leave
        except Exception as e:
            raise ValidationError(
                _('Error al crear la ausencia: %s') % str(e)
            )

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
