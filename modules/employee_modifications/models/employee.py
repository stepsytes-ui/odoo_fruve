
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError
import logging
from datetime import date

from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


def numero_a_letras(numero):
    """
    Convierte un número a su representación en letras (español mexicano)
    """
    unidades = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
    decenas = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
    especiales = ['ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISEIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE']
    veintitantos = ['VEINTE', 'VEINTIUNO', 'VEINTIDOS', 'VEINTITRES', 'VEINTICUATRO', 'VEINTICINCO', 'VEINTISEIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE']
    centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']

    def convertir_centenas(n):
        if n == 0:
            return ''
        elif n == 100:
            return 'CIEN'
        elif n < 10:
            return unidades[n]
        elif n == 10:
            return decenas[1]
        elif 11 <= n <= 19:
            return especiales[n - 11]
        elif 20 <= n <= 29:
            return veintitantos[n - 20]
        elif n < 100:
            d = n // 10
            u = n % 10
            if u == 0:
                return decenas[d]
            else:
                return decenas[d] + ' Y ' + unidades[u]
        else:
            c = n // 100
            resto = n % 100
            if resto == 0:
                return centenas[c]
            else:
                return centenas[c] + ' ' + convertir_centenas(resto)

    def convertir_miles(n):
        if n == 0:
            return 'CERO'
        elif n == 1000:
            return 'MIL'
        elif n < 1000:
            return convertir_centenas(n)
        else:
            m = n // 1000
            resto = n % 1000
            miles_str = 'MIL' if m == 1 else convertir_centenas(m) + ' MIL'
            if resto == 0:
                return miles_str
            else:
                return miles_str + ' ' + convertir_centenas(resto)

    def convertir_millones(n):
        if n < 1000000:
            return convertir_miles(n)
        else:
            mill = n // 1000000
            resto = n % 1000000
            mill_str = 'UN MILLON' if mill == 1 else convertir_miles(mill) + ' MILLONES'
            if resto == 0:
                return mill_str
            else:
                return mill_str + ' ' + convertir_miles(resto)

    entero = int(numero)
    decimal = int(round((numero - entero) * 100))
    
    return convertir_millones(entero).strip()


class HrEmployeeExtension(models.Model):
    _inherit = 'hr.employee'

    antiguedad = fields.Char(
        string='Antiguedad',
        compute='_compute_antiguedad',
    )

    biometric_id_numeric = fields.Integer(
        string='Numero de Empleado (Numerico)',
        compute='_compute_biometric_id_numeric',
        store=True,
        index=True,
    )

    fecha_ingreso_manual = fields.Date(
        string='Fecha de Ingreso',
        help="Campo para ingresar la fecha de ingreso del empleado si deja vacio tomara la fecha actual por default"
    )
    
    expedient_ids = fields.One2many(
        'employee.expedient', 
        'employee_id', 
        string='Historial de Movimientos'
    )

    disciplinary_record_ids = fields.One2many(
        'employee.disciplinary.record',
        'employee_id',
        string='Actas Disciplinarias'
    )

    warning_ids = fields.One2many(
        'employee.warning',
        'employee_id',
        string='Amonestaciones'
    )

    custom_overtime_ids = fields.One2many(
        'overtime',
        'employee_id',
        string='Solicitudes Tiempo Extra'
    )

    documents_ids = fields.One2many(
        'employee.documents',
        'employee_id',
        string='Archivos y Documentos'
    )

    suspension_ids = fields.One2many(
        'hr.suspension',
        'employee_id',
        string='Suspensiones'
    )

    suspension_count = fields.Integer(
        string='Número de Suspensiones',
        compute='_compute_suspension_count',
        help='Cantidad de suspensiones del empleado'
    )

    incapacity_ids = fields.One2many(
        'hr.incapacity',
        'employee_id',
        string='Incapacidades'
    )

    incapacity_count = fields.Integer(
        string='Número de Incapacidades',
        compute='_compute_incapacity_count',
        help='Cantidad de incapacidades del empleado'
    )

    permission_ids = fields.One2many(
        'hr.permission',
        'employee_id',
        string='Permisos'
    )

    permission_count = fields.Integer(
        string='Número de Permisos',
        compute='_compute_permission_count',
        help='Cantidad de permisos del empleado'
    )

    vacation_ids = fields.One2many(
        'hr.vacation',
        'employee_id',
        string='Vacaciones'
    )

    vacation_count = fields.Integer(
        string='Número de Vacaciones',
        compute='_compute_vacation_count',
        help='Cantidad de solicitudes de vacaciones del empleado'
    )

    has_resguardo = fields.Selection(
        [
            ('no', 'No'),
            ('si', 'Si'),
        ],
        string='Cuenta con Resguardo',
        required=True,
        tracking=True,
        help='Indica si el empleado cuenta con equipo o herramienta en resguardo.',
    )

    resguardo_ids = fields.One2many(
        'employee.resguardo',
        'employee_id',
        string='Resguardos',
    )

    resguardo_count = fields.Integer(
        string='Numero de Resguardos',
        compute='_compute_resguardo_count',
    )

    active_resguardo_count = fields.Integer(
        string='Resguardos Activos',
        compute='_compute_resguardo_count',
    )
    
    # Campo para RFC (Odoo 18 no usa address_home_id, se maneja directamente)
    rfc = fields.Char(
        string='RFC',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia',
        tracking=True,
        help='Registro Federal de Contribuyentes del empleado'
    )

    finiquitado = fields.Boolean(
        string='Finiquitado',
        default=False,
        tracking=True,
        help='Marca si el empleado ha sido finiquitado después de su baja'
    )

    # Redefinir current_leave_id para permitir acceso a supervisores y guardias
    current_leave_id = fields.Many2one(
        'hr.leave.type',
        compute='_compute_current_leave',
        string="Current Time Off Type",
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )

    # Redefinir activity_ids para permitir acceso a supervisores y guardias
    activity_ids = fields.One2many(
        'mail.activity',
        'res_id',
        string='Activities',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )

    # Redefinir campos relacionados con actividades para permitir acceso
    activity_state = fields.Selection(
        selection=[
            ('overdue', 'Overdue'),
            ('today', 'Today'),
            ('planned', 'Planned')
        ],
        compute='_compute_activity_state',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )
    
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )
    
    activity_summary = fields.Char(
        string='Activity Summary',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )
    
    activity_exception_decoration = fields.Selection(
        selection=[
            ('warning', 'Warning'),
            ('danger', 'Danger')
        ],
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )
    
    activity_exception_icon = fields.Char(
        string='Activity Exception Icon',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )
    
    activity_type_icon = fields.Char(
        string='Activity Type Icon',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )

    # Redefinir category_ids y employee_properties para permitir acceso
    category_ids = fields.Many2many(
        'hr.employee.category',
        'employee_category_rel',
        'employee_id',
        'category_id',
        string='Tags',
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )

    employee_properties = fields.Properties(
        'Properties',
        definition='company_id.employee_properties_definition',
        precompute=False,
        groups='hr.group_hr_user,employee_modifications.group_supervisor,employee_modifications.group_guardia'
    )

    @api.depends(
        'fecha_ingreso_manual',
        'expedient_ids',
        'expedient_ids.fecha_movimiento',
        'expedient_ids.tipo_registro',
        'expedient_ids.history_ids',
        'expedient_ids.history_ids.fecha',
        'expedient_ids.history_ids.tipo_movimiento',
        'active',
        'employee_status',
        'departure_date',
    )
    def _compute_antiguedad(self):
        for employee in self:
            fecha_ingreso = employee.get_fecha_ingreso() if employee.id else employee.fecha_ingreso_manual
            if not fecha_ingreso:
                employee.antiguedad = 'N/A'
                continue

            hoy = date.today()
            fecha_corte = hoy

            if employee.employee_status == 'inactive' or not employee.active:
                bajas_historial = employee.expedient_ids.mapped('history_ids').filtered(
                    lambda line: line.tipo_movimiento == 'baja' and line.fecha
                )

                if bajas_historial:
                    fecha_corte = max(bajas_historial.mapped('fecha'))
                elif employee.departure_date:
                    fecha_corte = employee.departure_date
                elif employee.write_date:
                    fecha_corte = fields.Datetime.to_datetime(employee.write_date).date()

            if fecha_corte < fecha_ingreso:
                fecha_corte = fecha_ingreso

            diff = relativedelta(fecha_corte, fecha_ingreso)
            employee.antiguedad = f"{diff.years} anos, {diff.months} meses y {diff.days} dias"

    @api.depends('biometric_id')
    def _compute_biometric_id_numeric(self):
        max_numeric_fallback = 2147483647
        for employee in self:
            biometric_value = (employee.biometric_id or '').strip()
            employee.biometric_id_numeric = (
                int(biometric_value)
                if biometric_value.isdigit()
                else max_numeric_fallback
            )

    @api.depends('suspension_ids')
    def _compute_suspension_count(self):
        """Calcula el número de suspensiones del empleado"""
        for employee in self:
            employee.suspension_count = len(employee.suspension_ids)

    @api.depends('incapacity_ids')
    def _compute_incapacity_count(self):
        """Calcula el número de incapacidades del empleado"""
        for employee in self:
            employee.incapacity_count = len(employee.incapacity_ids)

    @api.depends('permission_ids')
    def _compute_permission_count(self):
        """Calcula el número de permisos del empleado"""
        for employee in self:
            employee.permission_count = len(employee.permission_ids)

    @api.depends('vacation_ids')
    def _compute_vacation_count(self):
        """Calcula el número de vacaciones del empleado"""
        for employee in self:
            employee.vacation_count = len(employee.vacation_ids)

    @api.depends('resguardo_ids', 'resguardo_ids.state')
    def _compute_resguardo_count(self):
        for employee in self:
            employee.resguardo_count = len(employee.resguardo_ids)
            employee.active_resguardo_count = len(
                employee.resguardo_ids.filtered(lambda r: r.state in ['active', 'partial'])
            )

    @api.onchange('has_resguardo')
    def _onchange_has_resguardo(self):
        self.ensure_one()
        if self.has_resguardo != 'si':
            return

        # En onchange Odoo usa un registro virtual; _origin es el registro real en BD.
        employee = self._origin if self._origin and self._origin.id else self

        if not employee.id:
            return {
                'warning': {
                    'title': _('Guardar empleado primero'),
                    'message': _('Guarde el empleado para poder abrir el asistente de asignacion de resguardo.'),
                }
            }

        # Si el empleado ya existe, persistir el cambio inmediatamente y continuar flujo.
        if employee.has_resguardo != 'si':
            employee.write({'has_resguardo': 'si'})

        has_open_resguardo = bool(employee.resguardo_ids.filtered(lambda r: r.state in ['active', 'partial', 'draft']))
        if not has_open_resguardo:
            return employee.action_open_resguardo_assign_wizard()

    @api.constrains('has_resguardo', 'resguardo_ids', 'resguardo_ids.state')
    def _check_has_resguardo_consistency(self):
        for employee in self:
            has_pending = bool(employee.resguardo_ids.filtered(lambda r: r.state in ['active', 'partial']))
            if employee.has_resguardo == 'no' and has_pending:
                raise ValidationError(
                    'No puede marcar "Cuenta con Resguardo" en "No" mientras existan resguardos activos o parciales.'
                )

    @api.constrains('daily_rate')
    def _check_daily_rate_required_value(self):
        for employee in self:
            if employee.daily_rate is False or employee.daily_rate <= 0:
                raise ValidationError(
                    'El campo "Salario Diario" debe capturarse con un valor mayor a 0.'
                )

    def write(self, vals):
        """Override para archivar el empleado cuando se marca como finiquitado"""
        _logger.info(f"🔵 write() llamado con vals: {vals}")
        
        # Verificar si el usuario es supervisor o guardia
        is_supervisor = self.env.user.has_group('employee_modifications.group_supervisor')
        is_guardia = self.env.user.has_group('employee_modifications.group_guardia')
        is_hr = self.env.user.has_group('hr.group_hr_user')
        
        # Si es supervisor o guardia (pero no RRHH), bloquear la edición
        if (is_supervisor or is_guardia) and not is_hr:
            raise AccessError('No tiene permisos para modificar información de empleados. Solo el personal de RRHH puede realizar cambios.')
        
        # Si se marca como finiquitado, verificar si el empleado está inactivo
        if vals.get('finiquitado') == True:
            for employee in self:
                _logger.info(f"🔵 Procesando empleado {employee.name}, employee_status: {employee.employee_status}")
                # Verificar el estado actual del empleado (antes de escribir)
                if employee.employee_status == 'inactive':
                    vals['active'] = False
                    _logger.info(f"✅ Empleado {employee.name} será finiquitado y archivado (active=False agregado a vals)")
                else:
                    _logger.warning(f"⚠️ Empleado {employee.name} NO es inactivo, estado actual: {employee.employee_status}")
        
        result = super().write(vals)
        _logger.info(f"🔵 write() completado, resultado: {result}")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override para crear expediente inicial y verificar permisos"""
        # Verificar si el usuario es supervisor o guardia
        is_supervisor = self.env.user.has_group('employee_modifications.group_supervisor')
        is_guardia = self.env.user.has_group('employee_modifications.group_guardia')
        is_hr = self.env.user.has_group('hr.group_hr_user')
        
        # Si es supervisor o guardia (pero no RRHH), bloquear la creación
        if (is_supervisor or is_guardia) and not is_hr:
            raise AccessError('No tiene permisos para crear empleados. Solo el personal de RRHH puede realizar esta acción.')
        
        employees = super().create(vals_list)
        for employee, vals in zip(employees, vals_list):
            fecha_alta = vals.get('fecha_ingreso_manual') or fields.Date.today()
            self.env['employee.expedient'].create({
                    'employee_id': employee.id,
                    'tipo_registro': 'alta',
                    'fecha_movimiento': fecha_alta,
                    'recontratable': 'n/a',
                    'company_id': employee.company_id.id,
                })
        return employees
    
    def unlink(self):
        """Override para verificar permisos antes de eliminar"""
        # Verificar si el usuario es supervisor o guardia
        is_supervisor = self.env.user.has_group('employee_modifications.group_supervisor')
        is_guardia = self.env.user.has_group('employee_modifications.group_guardia')
        is_hr = self.env.user.has_group('hr.group_hr_user')
        
        # Si es supervisor o guardia (pero no RRHH), bloquear la eliminación
        if (is_supervisor or is_guardia) and not is_hr:
            raise AccessError('No tiene permisos para eliminar empleados. Solo el personal de RRHH puede realizar esta acción.')
        
        return super().unlink()
    
    def action_open_expedient_baja_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de baja para el empleado %s", self.name)

        pending_resguardos = self.env['employee.resguardo'].search([
            ('employee_id', '=', self.id),
            ('state', 'in', ['active', 'partial']),
        ])
        if pending_resguardos:
            pending_items = pending_resguardos.mapped('line_ids').filtered(lambda l: not l.devuelto)
            pending_names = ', '.join(pending_items.mapped('asset_id.nombre')[:10])
            if pending_names:
                raise ValidationError(
                    _('No se puede registrar la baja. El empleado tiene resguardos activos pendientes de devolucion: %s')
                    % pending_names
                )
            raise ValidationError(
                _('No se puede registrar la baja. El empleado tiene resguardos activos pendientes de devolucion.')
            )

        return {
            'name': "Registro de Baja de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.baja.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_baja_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
    
    def action_open_expedient_reingreso_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de reingreso para el empleado %s", self.name)
        return {
            'name': "Registro de Reingreso de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.reingreso.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_reingreso_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
    
    def action_view_expedient(self):
        self.ensure_one()
        expedient = self.env['employee.expedient'].search([
            ('employee_id', '=', self.id)
        ], limit=1)
        
        if not expedient:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No se encontró expediente para este empleado.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'name': f"Expediente de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient',
            'view_mode': 'form',
            'res_id': expedient.id,
            'target': 'current',
        }
    
    def action_view_warnings(self):
        """Método para abrir la vista de amonestaciones del empleado"""
        self.ensure_one()
        return {
            'name': f"Amonestaciones de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.warning',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'default_biometric_id': self.biometric_id,
            },
            'target': 'current',
        }
    
    def action_view_overtime(self):
        """Método para abrir la vista de tiempo extra del empleado"""
        self.ensure_one()
        return {
            'name': f"Tiempo Extra de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'overtime',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }
    
    def action_view_documents(self):
        """Método para abrir los archivos y documentos del empleado"""
        self.ensure_one()
        # Buscar o crear el registro de documentos para este empleado
        document = self.env['employee.documents'].search([
            ('employee_id', '=', self.id)
        ], limit=1)
        
        if not document:
            # Crear automáticamente el registro si no existe
            document = self.env['employee.documents'].create({
                'employee_id': self.id,
            })
        
        return {
            'name': f"Archivos de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.documents',
            'view_mode': 'form',
            'res_id': document.id,
            'target': 'current',
        }
    
    def action_view_suspensions(self):
        """Método para abrir la vista de suspensiones del empleado"""
        self.ensure_one()
        return {
            'name': f"Suspensiones de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.suspension',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }
    
    def action_view_incapacities(self):
        """Método para abrir la vista de incapacidades del empleado"""
        self.ensure_one()
        return {
            'name': f"Incapacidades de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.incapacity',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }

    def action_view_permissions(self):
        """Método para abrir la vista de permisos del empleado"""
        self.ensure_one()
        return {
            'name': f"Permisos de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.permission',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }

    def action_view_vacations(self):
        """Método para abrir la vista de vacaciones del empleado"""
        self.ensure_one()
        return {
            'name': f"Vacaciones de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.vacation',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }

    def action_view_resguardos(self):
        """Abre el historial de resguardos del empleado"""
        self.ensure_one()
        return {
            'name': f"Resguardos de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.resguardo',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'default_responsable_rh_id': self.env.user.id,
            },
            'target': 'current',
        }

    def action_open_resguardo_assign_wizard(self):
        self.ensure_one()
        return {
            'name': 'Asignar Resguardo',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.resguardo.assign.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_resguardo_assign_wizard_form').id,
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_responsable_rh_id': self.env.user.id,
            },
        }

    def action_print_carta_laboral(self):
        """Genera la carta laboral en PDF (servidor) para un resultado consistente."""
        self.ensure_one()
        report = self.env.ref('employee_modifications.report_carta_laboral')
        return report.report_action(self)

    def get_fecha_ingreso(self):
        """Obtiene la fecha de ingreso del empleado"""
        self.ensure_one()
        # Primero intentar del campo manual
        if self.fecha_ingreso_manual:
            return self.fecha_ingreso_manual
        # Si no, buscar en el expediente de alta
        expediente_alta = self.env['employee.expedient'].search([
            ('employee_id', '=', self.id),
            ('tipo_registro', '=', 'alta')
        ], order='fecha_movimiento asc', limit=1)
        
        if expediente_alta:
            return expediente_alta.fecha_movimiento
        
        return fields.Date.today()

    def get_salario_mensual(self):
        """Calcula el salario mensual (daily_rate * 30.1 = promedio días por mes)"""
        self.ensure_one()
        if hasattr(self, 'daily_rate') and self.daily_rate:
            return self.daily_rate * 30.1
        return 0.00

    def get_salario_mensual_letras(self):
        """Obtiene el salario mensual en letras"""
        self.ensure_one()
        salario = self.get_salario_mensual()
        entero = int(salario)
        centavos = int(round((salario - entero) * 100))
        
        letras_entero = numero_a_letras(salario)
        return f"{letras_entero} PESOS Y {centavos:02d}/100 M.N."

    def get_salario_mensual_formatted(self):
        """Obtiene el salario mensual formateado con comas para miles"""
        self.ensure_one()
        salario = self.get_salario_mensual()
        # Formatear manualmente para evitar dependencias de locale
        amount_str = f"{salario:.2f}"
        parts = amount_str.split('.')
        integer = parts[0]
        decimal = parts[1] if len(parts) > 1 else '00'
        # Insertar comas cada 3 dígitos en la parte entera
        integer_reversed = integer[::-1]
        formatted_integer = ''
        for i, char in enumerate(integer_reversed):
            if i > 0 and i % 3 == 0:
                formatted_integer += ','
            formatted_integer += char
        formatted_integer = formatted_integer[::-1]
        return f"{formatted_integer}.{decimal}"

    def get_horario_trabajo(self):
        """Obtiene el horario de trabajo del empleado"""
        self.ensure_one()
        if hasattr(self, 'turno_id') and self.turno_id:
            return self.turno_id.horario_carta_laboral or self.turno_id.turno_name or 'N/A'
        return 'N/A'

    def get_company_location(self):
        """Obtiene la ubicación basada en el nombre de la empresa"""
        self.ensure_one()
        company_name = self.company_id.name if self.company_id else ''
        
        if 'MEXICALI' in company_name.upper():
            return 'MEXICALI, BAJA CALIFORNIA'
        elif 'IRAPUATO' in company_name.upper():
            return 'IRAPUATO, GUANAJUATO'
        elif 'CULIACAN' in company_name.upper():
            return 'CULIACAN, SINALOA'
        elif 'ROSARITO' in company_name.upper():
            return 'ROSARITO, BAJA CALIFORNIA'
        else:
            return 'MEXICALI, BAJA CALIFORNIA'  # Default

    def get_fecha_ingreso_formatted(self):
        """Obtiene la fecha de ingreso formateada en español"""
        self.ensure_one()
        fecha = self.get_fecha_ingreso()
        
        meses = {
            1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
            5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
            9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
        }
        
        dia = fecha.strftime('%d')
        mes = meses[fecha.month]
        anio = fecha.strftime('%Y')
        
        return f"{dia}/{mes}/{anio}"