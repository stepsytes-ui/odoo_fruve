from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    vacation_days_subtracted = fields.Boolean(
        string="Días Descontados",
        default=False,
        copy=False,
    )

    # Campo Supervisor (para todos los tipos de ausencia)
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        domain=lambda self: [('groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])],
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

    # Campos para Permisos
    is_permission = fields.Boolean(
        string='Es Permiso',
        compute='_compute_is_permission',
        store=True,
        help='Indica si esta ausencia es de tipo Permiso'
    )

    permission_id = fields.Many2one(
        'hr.permission',
        string='Permiso',
        readonly=True,
        help='Registro de permiso asociado'
    )

    # Campos para Vacaciones
    is_vacation = fields.Boolean(
        string='Es Vacación',
        compute='_compute_is_vacation',
        store=True,
        help='Indica si esta ausencia es de tipo Vacaciones'
    )

    vacation_modality = fields.Selection(
        [
            ('gozadas', 'Gozadas'),
            ('pagadas', 'Pagadas'),
            ('ambos', 'Ambos'),
        ],
        string='Modalidad',
        default='gozadas',
        tracking=True,
        help='Modalidad de la solicitud de vacaciones'
    )

    vacation_id = fields.Many2one(
        'hr.vacation',
        string='Vacación',
        readonly=True,
        help='Registro de vacación asociado'
    )

    vacation_days_available = fields.Float(
        string='Días de Vacaciones Disponibles',
        compute='_compute_vacation_info',
        store=False,
        help='Días de vacaciones disponibles del empleado'
    )

    employee_antiguedad = fields.Char(
        string='Antigüedad del Empleado',
        compute='_compute_vacation_info',
        store=False,
        help='Antigüedad del empleado en la empresa'
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

    @api.depends('holiday_status_id', 'holiday_status_id.name')
    def _compute_is_permission(self):
        """Determina si la ausencia es de tipo Permiso (cualquiera que contenga 'Permiso')"""
        for leave in self:
            leave.is_permission = (
                leave.holiday_status_id and 
                'Permiso' in leave.holiday_status_id.name
            )

    @api.depends('holiday_status_id', 'holiday_status_id.name')
    def _compute_is_vacation(self):
        """Determina si la ausencia es de tipo Vacaciones"""
        for leave in self:
            leave.is_vacation = leave.holiday_status_id and leave.holiday_status_id.name == 'Vacaciones'

    @api.depends('employee_id', 'is_vacation')
    def _compute_vacation_info(self):
        """Calcula los días disponibles y antigüedad del empleado"""
        for leave in self:
            if leave.employee_id and leave.is_vacation:
                # Buscar el expediente del empleado
                expedient = self.env['employee.expedient'].search([
                    ('employee_id', '=', leave.employee_id.id)
                ], order='fecha_movimiento desc', limit=1)
                
                if expedient:
                    leave.vacation_days_available = expedient.dias_vacaciones_disponibles
                    leave.employee_antiguedad = expedient.antiguedad or 'N/A'
                else:
                    leave.vacation_days_available = 0.0
                    leave.employee_antiguedad = 'Sin expediente'
            else:
                leave.vacation_days_available = 0.0
                leave.employee_antiguedad = ''

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
            # Si es una suspensión, crear el registro en hr.suspension (a menos que se  cree desde una suspensión ya existente)
            if leave.is_suspension and leave.state not in ['cancel', 'refuse'] and not self.env.context.get('skip_suspension_creation'):
                self._create_suspension_record(leave)
            
            # Si es una incapacidad, crear el registro en hr.incapacity
            if leave.is_incapacity and leave.state not in ['cancel', 'refuse']:
                self._create_incapacity_record(leave)
            
            # Si es un permiso, crear el registro en hr.permission
            if leave.is_permission and leave.state not in ['cancel', 'refuse']:
                self._create_permission_record(leave)
            
            # Si es una vacación, crear el registro en hr.vacation
            if leave.is_vacation and leave.state not in ['cancel', 'refuse']:
                self._create_vacation_record(leave)
        
        return leaves

    def write(self, vals):
        """Actualizar suspensión o incapacidad cuando se modifica la ausencia"""
        res = super(HrLeave, self).write(vals)
        
        for leave in self:
            # Si es una suspensión y está aprobada, crear o actualizar el registro
            if leave.is_suspension:
                if leave.state in ['validate', 'validate1'] and not leave.suspension_id and not self.env.context.get('skip_suspension_creation'):
                    self._create_suspension_record(leave)
                elif leave.suspension_id:
                    self._update_suspension_record(leave)
            
            # Si es una incapacidad y está aprobada, crear o actualizar el registro
            if leave.is_incapacity:
                if leave.state in ['validate', 'validate1'] and not leave.incapacity_id:
                    self._create_incapacity_record(leave)
                elif leave.incapacity_id:
                    self._update_incapacity_record(leave)
            
            # Si es un permiso y está aprobado, crear o actualizar el registro
            if leave.is_permission:
                if leave.state in ['validate', 'validate1'] and not leave.permission_id:
                    self._create_permission_record(leave)
                elif leave.permission_id:
                    self._update_permission_record(leave)
            
            # Si es una vacación y está aprobada, crear o actualizar el registro
            if leave.is_vacation:
                if leave.state in ['validate', 'validate1'] and not leave.vacation_id:
                    self._create_vacation_record(leave)
                elif leave.vacation_id:
                    self._update_vacation_record(leave)
        
        return res

    def _create_suspension_record(self, leave):
        """Crea un registro de suspensión asociado a esta ausencia"""
        
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
        
        # Agregar supervisor si está disponible
        if leave.supervisor_id:
            incapacity_vals['supervisor_id'] = leave.supervisor_id.id
        
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
            
            # Actualizar supervisor si está disponible
            if leave.supervisor_id:
                update_vals['supervisor_id'] = leave.supervisor_id.id
            
            # Actualizar estado según el estado de la ausencia
            if leave.state in ['validate', 'validate1']:
                update_vals['state'] = 'validate'
            elif leave.state == 'refuse':
                update_vals['state'] = 'refuse'
            elif leave.state == 'cancel':
                update_vals['state'] = 'cancel'
            
            leave.incapacity_id.write(update_vals)

    def _create_permission_record(self, leave):
        """Crea un registro de permiso asociado a esta ausencia"""
        # Extraer el tipo de permiso del nombre del tipo de ausencia
        permission_type = leave.holiday_status_id.name if leave.holiday_status_id else 'Permiso'
        
        permission_vals = {
            'employee_id': leave.employee_id.id,
            'date_from': leave.date_from,
            'date_to': leave.date_to,
            'permission_type': permission_type,
            'reason': leave.name or 'Permiso solicitado',
            'leave_id': leave.id,
            'state': 'validate' if leave.state in ['validate', 'validate1'] else 'draft',
        }
        
        # Agregar supervisor si está disponible
        if leave.supervisor_id:
            permission_vals['supervisor_id'] = leave.supervisor_id.id
        
        permission = self.env['hr.permission'].create(permission_vals)
        leave.permission_id = permission.id
        return permission

    def _update_permission_record(self, leave):
        """Actualiza el registro de permiso existente"""
        if leave.permission_id:
            # Extraer el tipo de permiso del nombre del tipo de ausencia
            permission_type = leave.holiday_status_id.name if leave.holiday_status_id else 'Permiso'
            
            update_vals = {
                'date_from': leave.date_from,
                'date_to': leave.date_to,
                'permission_type': permission_type,
                'reason': leave.name or 'Permiso solicitado',
            }
            
            # Actualizar supervisor si está disponible
            if leave.supervisor_id:
                update_vals['supervisor_id'] = leave.supervisor_id.id
            
            # Actualizar estado según el estado de la ausencia
            if leave.state in ['validate', 'validate1']:
                update_vals['state'] = 'validate'
            elif leave.state == 'refuse':
                update_vals['state'] = 'refuse'
            elif leave.state == 'cancel':
                update_vals['state'] = 'cancel'
            
            leave.permission_id.write(update_vals)

    def _create_vacation_record(self, leave):
        """Crea un registro de vacación asociado a esta ausencia"""
        # Obtener información del expediente
        expedient = self.env['employee.expedient'].search([
            ('employee_id', '=', leave.employee_id.id)
        ], order='fecha_movimiento desc', limit=1)
        
        vacation_vals = {
            'employee_id': leave.employee_id.id,
            'date_from': leave.date_from,
            'date_to': leave.date_to,
            'description': leave.name or 'Solicitud de vacaciones',
            'leave_id': leave.id,
            'vacation_modality': leave.vacation_modality,
            'state': 'validate' if leave.state in ['validate', 'validate1'] else 'draft',
        }
        
        # Agregar información del expediente si existe
        if expedient:
            vacation_vals['vacation_days_available'] = expedient.dias_vacaciones_disponibles
            vacation_vals['employee_antiguedad'] = expedient.antiguedad
        
        # Agregar supervisor si está disponible
        if leave.supervisor_id:
            vacation_vals['supervisor_id'] = leave.supervisor_id.id
        
        vacation = self.env['hr.vacation'].create(vacation_vals)
        leave.vacation_id = vacation.id
        return vacation

    def _update_vacation_record(self, leave):
        """Actualiza el registro de vacación existente"""
        if leave.vacation_id:
            # Obtener información actualizada del expediente
            expedient = self.env['employee.expedient'].search([
                ('employee_id', '=', leave.employee_id.id)
            ], order='fecha_movimiento desc', limit=1)
            
            update_vals = {
                'date_from': leave.date_from,
                'date_to': leave.date_to,
                'description': leave.name or 'Solicitud de vacaciones',
                'vacation_modality': leave.vacation_modality,
            }
            
            # Actualizar información del expediente si existe
            if expedient:
                update_vals['vacation_days_available'] = expedient.dias_vacaciones_disponibles
                update_vals['employee_antiguedad'] = expedient.antiguedad
            
            # Actualizar supervisor si está disponible
            if leave.supervisor_id:
                update_vals['supervisor_id'] = leave.supervisor_id.id
            
            # Actualizar estado según el estado de la ausencia
            if leave.state in ['validate', 'validate1']:
                update_vals['state'] = 'validate'
            elif leave.state == 'refuse':
                update_vals['state'] = 'refuse'
            elif leave.state == 'cancel':
                update_vals['state'] = 'cancel'
            
            leave.vacation_id.write(update_vals)
