
from odoo import models, fields, api
import logging

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
    
    # Campo para RFC (Odoo 18 no usa address_home_id, se maneja directamente)
    rfc = fields.Char(
        string='RFC',
        groups='hr.group_hr_user',
        tracking=True,
        help='Registro Federal de Contribuyentes del empleado'
    )

    finiquitado = fields.Boolean(
        string='Finiquitado',
        default=False,
        tracking=True,
        help='Marca si el empleado ha sido finiquitado después de su baja'
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

    def write(self, vals):
        """Override para archivar el empleado cuando se marca como finiquitado"""
        _logger.info(f"🔵 write() llamado con vals: {vals}")
        
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
    
    def action_open_expedient_baja_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de baja para el empleado %s", self.name)
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
        """Calcula el salario mensual (daily_rate * 7 * 4 = salario semanal * 4 semanas)"""
        self.ensure_one()
        if hasattr(self, 'daily_rate') and self.daily_rate:
            return self.daily_rate * 28
        return 0.00

    def get_salario_mensual_letras(self):
        """Obtiene el salario mensual en letras"""
        self.ensure_one()
        salario = self.get_salario_mensual()
        entero = int(salario)
        centavos = int(round((salario - entero) * 100))
        
        letras_entero = numero_a_letras(salario)
        return f"{letras_entero} PESOS Y {centavos:02d}/100 M.N."

    def get_horario_trabajo(self):
        """Obtiene el horario de trabajo del empleado"""
        self.ensure_one()
        if hasattr(self, 'turno_id') and self.turno_id:
            return self.turno_id.turno_name or 'N/A'
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