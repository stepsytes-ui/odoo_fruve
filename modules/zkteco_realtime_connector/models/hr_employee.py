
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    biometric_id = fields.Char(string='Numero de empleado')
    last_absence_alert_at = fields.Datetime(
        string='Ultima alerta de 4ta falta',
        copy=False,
        help='Fecha/hora del ultimo correo de alerta por faltas para evitar notificaciones repetidas.'
    )
    
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

    @api.onchange('company_id')
    def _onchange_company_id_set_timezone(self):
        for employee in self:
            if employee.company_id and employee.company_id.timezone:
                employee.tz = employee.company_id.timezone

    @api.onchange('turno_id')
    def _onchange_turno_id_set_resource_calendar(self):
        for employee in self:
            employee.resource_calendar_id = employee.turno_id.resource_calendar_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tz'):
                company_id = vals.get('company_id') or self.env.company.id
                company = self.env['res.company'].browse(company_id)
                if company.timezone:
                    vals['tz'] = company.timezone

            turno_id = vals.get('turno_id')
            if turno_id and not vals.get('resource_calendar_id'):
                turno = self.env['shift.management'].browse(turno_id)
                if turno.resource_calendar_id:
                    vals['resource_calendar_id'] = turno.resource_calendar_id.id
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)

        if 'company_id' in vals and 'tz' not in vals:
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else False
            vals['tz'] = company.timezone if company and company.timezone else False

        if 'turno_id' in vals and 'resource_calendar_id' not in vals:
            turno = self.env['shift.management'].browse(vals.get('turno_id')) if vals.get('turno_id') else False
            vals['resource_calendar_id'] = turno.resource_calendar_id.id if turno else False
        return super().write(vals)

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

    def action_open_attendance_history_report(self):
        """
        Abre el wizard de reporte de asistencia con el empleado actual y
        un rango automático desde su primera hasta su última asistencia.
        """
        self.ensure_one()

        attendance_domain = [
            ('employee_id', '=', self.id),
            ('check_in', '!=', False),
        ]
        first_attendance = self.env['hr.attendance'].search(
            attendance_domain,
            order='check_in asc',
            limit=1,
        )
        last_attendance = self.env['hr.attendance'].search(
            attendance_domain,
            order='check_in desc',
            limit=1,
        )

        if not first_attendance or not last_attendance:
            raise UserError(
                _('El empleado seleccionado no tiene asistencias registradas.')
            )

        action = self.env.ref('zkteco_realtime_connector.attendance_report_wizard_action').read()[0]
        action['context'] = {
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_open_from_employee': True,
            'default_period_mode': 'range',
            'default_date_from': fields.Datetime.to_datetime(first_attendance.check_in).date(),
            'default_date_to': fields.Datetime.to_datetime(last_attendance.check_in).date(),
            'default_employee_id': self.id,
            'default_show_archived': not self.active,
        }
        return action