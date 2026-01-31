
from odoo import models, fields, api


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    biometric_id = fields.Char(string='Numero de empleado')
    
    biometric_id_numeric = fields.Integer(
        string='No. Empleado (ordenamiento)',
        compute='_compute_biometric_id_numeric',
        store=True,
        help='Campo numérico derivado de biometric_id para ordenamiento'
    )
    
    employee_status = fields.Selection([
        ('active', 'Activo'),
        ('inactive', 'Inactivo')
    ], string='Estado del Empleado', default='active', required=True, readonly=True)

    turno_id = fields.Many2one(
        comodel_name='shift.management',
        string='Turno Asignado',
        help='Selecciona el turno definido en la gestión de turnos.'
    )

    @api.depends('biometric_id')
    def _compute_biometric_id_numeric(self):
        """Convierte biometric_id a valor numérico para ordenamiento"""
        for employee in self:
            if employee.biometric_id and employee.biometric_id.isdigit():
                employee.biometric_id_numeric = int(employee.biometric_id)
            else:
                employee.biometric_id_numeric = 0

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Permite buscar empleados por nombre o biometric_id en formularios
        """
        args = args or []
        
        if not name:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)
        
        if name.isdigit():
            domain = [
                '|',
                ('biometric_id', 'ilike', name),
                ('name', operator, name)
            ]
        else:
            domain = [
                '|',
                ('name', operator, name),
                ('biometric_id', operator, name)
            ]
        
        employee_ids = self._search(args + domain, limit=limit)
        return [(emp_id, self.browse(emp_id).display_name) for emp_id in employee_ids]
    
    @api.model
    def _search_read_employee_by_identifier(self, identifier):
        """
        Sobrescribimos para que el Quiosco reconozca el biometric_id
        """
        # Intentar buscar por biometric_id
        employee = self.search([('biometric_id', '=', identifier)], limit=1)
        
        # Si no lo encuentra, usar la lógica estándar (barcode o PIN)
        if not employee:
            employee = self.search(['|', ('barcode', '=', identifier), ('pin', '=', identifier)], limit=1)
        
        if employee:
            # Retornamos lo que el componente OWL espera
            return employee.read(['id', 'name', 'attendance_state', 'pin'])[0]
        return False