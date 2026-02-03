from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    vacation_days_subtracted = fields.Boolean(
        string="Días Descontados",
        default=False,
        copy=False,
    )

    # Campos para Suspensiones
    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        domain=lambda self: [('user_id.groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])],
        tracking=True,
        help='Supervisor asignado (debe pertenecer al grupo Supervisor Tiempo Extra)'
    )
    
    is_suspension = fields.Boolean(
        string='Es Suspensión',
        compute='_compute_is_suspension',
        store=True,
        help='Indica si esta ausencia es de tipo Suspensión'
    )

    suspension_id = fields.Many2one(
        'hr.suspension',
        string='Suspensión',
        readonly=True,
        help='Registro de suspensión asociado'
    )

    # Campos para Incapacidades
    total_days_incapacity = fields.Integer(
        string='Total Días',
        tracking=True,
        help='Total de días de incapacidad (se calculará automáticamente la fecha de fin)'
    )
    
    incapacity_type = fields.Selection([
        ('riesgo_trabajo', 'Riesgo Trabajo'),
        ('enfermedad_trabajo', 'Enfermedad Trabajo'),
        ('enfermedad_general', 'Enfermedad General'),
        ('maternidad', 'Maternidad')
    ], string='Motivo Incapacidad', tracking=True)
    
    is_incapacity = fields.Boolean(
        string='Es Incapacidad',
        compute='_compute_is_incapacity',
        store=True,
        help='Indica si esta ausencia es de tipo Incapacidad'
    )

    incapacity_id = fields.Many2one(
        'hr.incapacity',
        string='Incapacidad',
        readonly=True,
        help='Registro de incapacidad asociado'
    )

    @api.depends('holiday_status_id', 'holiday_status_id.name')
    def _compute_is_suspension(self):
        """Determina si la ausencia es de tipo Suspensión"""
        for leave in self:
            leave.is_suspension = leave.holiday_status_id and leave.holiday_status_id.name == 'Suspensión'

    @api.depends('holiday_status_id', 'holiday_status_id.name')
    def _compute_is_incapacity(self):
        """Determina si la ausencia es de tipo Incapacidad"""
        for leave in self:
            leave.is_incapacity = leave.holiday_status_id and leave.holiday_status_id.name == 'Incapacidad'

    @api.onchange('is_incapacity', 'request_date_from', 'total_days_incapacity')
    def _onchange_incapacity_dates(self):
        """Calcula automáticamente la fecha de fin cuando es incapacidad"""
        if self.is_incapacity and self.request_date_from and self.total_days_incapacity:
            from datetime import timedelta
            # Calcular fecha de fin: fecha inicio + (total_días - 1)
            # -1 porque el primer día cuenta
            date_to = self.request_date_from + timedelta(days=self.total_days_incapacity - 1)
            self.request_date_to = date_to

    @api.constrains('number_of_days', 'holiday_status_id', 'employee_id', 'state')
    def _check_vacation_availibility_and_update(self):
        
        for leave in self:
            if leave.holiday_status_id.name == 'Vacaciones':
                
                expedient = self.env['employee.expedient'].search([
                    ('employee_id', '=', leave.employee_id.id),
                ], order='fecha_movimiento desc', limit=1)

                if not expedient:
                    raise ValidationError(_("No se encontró un expediente activo para el empleado %s.") % leave.employee_id.name)

                days_requested = leave.number_of_days
                
                if leave.state == 'validate' and not leave.vacation_days_subtracted:
                    days_available = expedient.dias_vacaciones_disponibles

                    if days_requested > days_available:
                        raise ValidationError(_(
                            "Error de vacaciones: El empleado %s solo tiene %.2f días disponibles y está solicitando %.2f días"
                        ) % (leave.employee_id.name, days_available, days_requested))

                    else:
                        new_used_days = expedient.dias_vacaciones_utilizados + days_requested
                        expedient.write({'dias_vacaciones_utilizados': new_used_days})
                        leave.vacation_days_subtracted = True
                        
                        self.env['mail.message'].create({
                            'model': 'employee.expedient',
                            'res_id': expedient.id,
                            'message_type': 'notification',
                            'body':_("**Descuento de Vacaciones Automático:** Se descontaron %.2f días por la solicitud de ausencias #%s. Saldo disponible anterior: %.2f días. Nuevo Saldo Utilizado: %.2f días."
                            ) % (days_requested, leave.name, days_available, new_used_days),
                            'subject': 'Vacaciones Descontadas',
                            'author_id': self.env.user.partner_id.id,
                        })

                # --- LÓGICA DE RECHAZO (Devolver Días) ---
                elif leave.state == 'refuse' and leave.vacation_days_subtracted:
                    new_used_days = expedient.dias_vacaciones_utilizados - days_requested
                    expedient.write({'dias_vacaciones_utilizados': new_used_days})
                    leave.vacation_days_subtracted = False

                    self.env['mail.message'].create({
                        'model': 'employee.expedient',
                        'res_id': expedient.id,
                        'message_type': 'notification',
                        'body':_("**Devolución de Vacaciones Automática:** Se devolvieron %.2f días por el rechazo de la solicitud de ausencias #%s. Nuevo Saldo Utilizado: %.2f días."
                        ) % (days_requested, leave.name, new_used_days),
                        'subject': 'Vacaciones Devueltas (Rechazo)',
                        'author_id': self.env.user.partner_id.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        """Crear registro de suspensión o incapacidad cuando se crea una ausencia"""
        leaves = super(HrLeave, self).create(vals_list)
        
        # Procesar cada ausencia creada
        for leave in leaves:
            # Si es una suspensión, crear el registro en hr.suspension
            if leave.is_suspension and leave.state not in ['cancel', 'refuse']:
                self._create_suspension_record(leave)
            
            # Si es una incapacidad, crear el registro en hr.incapacity
            if leave.is_incapacity and leave.state not in ['cancel', 'refuse']:
                self._create_incapacity_record(leave)
        
        return leaves

    def write(self, vals):
        """Actualizar suspensión o incapacidad cuando se modifica la ausencia"""
        res = super(HrLeave, self).write(vals)
        
        for leave in self:
            # Si es una suspensión y está aprobada, crear o actualizar el registro
            if leave.is_suspension:
                if leave.state in ['validate', 'validate1'] and not leave.suspension_id:
                    self._create_suspension_record(leave)
                elif leave.suspension_id:
                    self._update_suspension_record(leave)
            
            # Si es una incapacidad y está aprobada, crear o actualizar el registro
            if leave.is_incapacity:
                if leave.state in ['validate', 'validate1'] and not leave.incapacity_id:
                    self._create_incapacity_record(leave)
                elif leave.incapacity_id:
                    self._update_incapacity_record(leave)
        
        return res

    def _create_suspension_record(self, leave):
        """Crea un registro de suspensión asociado a esta ausencia"""
        if not leave.supervisor_id:
            raise ValidationError(
                _('Debe seleccionar un Supervisor para crear la Suspensión.')
            )
        
        suspension_vals = {
            'employee_id': leave.employee_id.id,
            'supervisor_id': leave.supervisor_id.id,
            'date_from': leave.date_from,
            'date_to': leave.date_to,
            'reason': leave.name or 'Suspensión',
            'leave_id': leave.id,
            'state': 'validate' if leave.state in ['validate', 'validate1'] else 'draft',
        }
        
        suspension = self.env['hr.suspension'].create(suspension_vals)
        leave.suspension_id = suspension.id
        return suspension

    def _update_suspension_record(self, leave):
        """Actualiza el registro de suspensión existente"""
        if leave.suspension_id:
            update_vals = {
                'date_from': leave.date_from,
                'date_to': leave.date_to,
                'reason': leave.name or 'Suspensión',
            }
            
            # Solo actualizar supervisor si se proporcionó uno
            if leave.supervisor_id:
                update_vals['supervisor_id'] = leave.supervisor_id.id
            
            # Actualizar estado según el estado de la ausencia
            if leave.state in ['validate', 'validate1']:
                update_vals['state'] = 'validate'
            elif leave.state == 'refuse':
                update_vals['state'] = 'refuse'
            elif leave.state == 'cancel':
                update_vals['state'] = 'cancel'
            
            leave.suspension_id.write(update_vals)

    def _create_incapacity_record(self, leave):
        """Crea un registro de incapacidad asociado a esta ausencia"""
        if not leave.total_days_incapacity:
            raise ValidationError(
                _('Debe especificar el Total de Días para crear la Incapacidad.')
            )
        
        if not leave.incapacity_type:
            raise ValidationError(
                _('Debe seleccionar el Motivo de Incapacidad.')
            )
        
        incapacity_vals = {
            'employee_id': leave.employee_id.id,
            'date_from': leave.date_from,
            'date_to': leave.date_to,
            'total_days': leave.total_days_incapacity,
            'incapacity_type': leave.incapacity_type,
            'comments': leave.name or '',
            'leave_id': leave.id,
            'state': 'validate' if leave.state in ['validate', 'validate1'] else 'draft',
        }
        
        incapacity = self.env['hr.incapacity'].create(incapacity_vals)
        leave.incapacity_id = incapacity.id
        return incapacity

    def _update_incapacity_record(self, leave):
        """Actualiza el registro de incapacidad existente"""
        if leave.incapacity_id:
            update_vals = {
                'date_from': leave.date_from,
                'date_to': leave.date_to,
                'total_days': leave.total_days_incapacity or 0,
                'comments': leave.name or '',
            }
            
            # Solo actualizar motivo si se proporcionó uno
            if leave.incapacity_type:
                update_vals['incapacity_type'] = leave.incapacity_type
            
            # Actualizar estado según el estado de la ausencia
            if leave.state in ['validate', 'validate1']:
                update_vals['state'] = 'validate'
            elif leave.state == 'refuse':
                update_vals['state'] = 'refuse'
            elif leave.state == 'cancel':
                update_vals['state'] = 'cancel'
            
            leave.incapacity_id.write(update_vals)
