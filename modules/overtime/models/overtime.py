from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone

class Overtime(models.Model):
    _name = 'overtime'
    _description = 'Solicitud de Tiempo Extra'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default=lambda self: _('Nuevo'))
    create_date = fields.Datetime(string='Fecha Creación', readonly=True )
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True,default=lambda self: self.env.user.employee_id.id)
    supervisor_id = fields.Many2one('res.users',string='Supervisor que solicita',default=lambda self: self.env.user.id,readonly=True)
    requested_date = fields.Date(string='Fecha Solicitada', required=True)
    department_id = fields.Many2one('hr.department',string='Departamento',store=True)
    area_id = fields.Many2one('hr.area',string='Área',required=True,domain="[('department_id', '=', department_id)]" )
    justification = fields.Text(string='Explicación del Tiempo Extra', required=True)
    employee_line_ids = fields.One2many('overtime.employee.line', 'overtime_id',string=' ')
    time_from = fields.Float(string='Desde')
    time_to = fields.Float(string='Hasta')
    hours_taken = fields.Float(string='Horas Totales')
    activity = fields.Text(string='Actividad')
    biometric_id = fields.Char(string='Numero de empleado',related='employee_id.biometric_id', store=True)
    attendance_log = fields.Text(string='Registro de checadas del día', compute='_compute_attendance_log', store=False, readonly=True)
    authorized_by_id = fields.Many2one('res.users', string='Autorizado por', readonly=True)
    rejection_reason = fields.Text(string='Motivo de Rechazo', readonly=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], 
        string='Estado', 
        default='draft', 
        tracking=True
    )

    @api.model
    def get_overtime_dashboard_stats(self, start_date, end_date):
        """
        Calcula las estadísticas del dashboard de tiempo extra
        """
        domain = [
            ('requested_date', '>=', start_date),
            ('requested_date', '<=', end_date),
            ('state', '=', 'approved'),
        ]
        
        overtimes = self.search(domain)
        
        # Calcular estadísticas
        total_employees = len(overtimes.mapped('employee_id'))
        total_hours = sum(overtimes.mapped('hours_taken')) or 0
        
        # Calcular el costo total (salario diario * horas / 8)
        total_pay = 0
        for overtime in overtimes:
            if overtime.employee_id.daily_rate and overtime.hours_taken:
                hourly_rate = overtime.employee_id.daily_rate / 8
                total_pay += hourly_rate * overtime.hours_taken
        
        return {
            'total_employees': total_employees,
            'total_hours': total_hours,
            'total_play': total_pay,
        }

    @api.model
    def get_overtime_table_data(self, start_date, end_date):
        """
        Retorna los datos para la tabla dinámica del dashboard
        Columnas: employee_number, daily_rate, employee_name, days_worked, hours_taken, total_cost
        """
        domain = [
            ('requested_date', '>=', start_date),
            ('requested_date', '<=', end_date),
            ('state', '=', 'approved'),
        ]
        
        overtimes = self.search(domain, order='employee_id')
        
        # Agrupar por empleado para calcular días y horas trabajadas
        employees_data = {}
        
        for overtime in overtimes:
            emp_id = overtime.employee_id.id
            emp_name = overtime.employee_id.name
            emp_biometric = overtime.employee_id.biometric_id or 'N/A'
            emp_daily_rate = overtime.employee_id.daily_rate or 0.0
            
            if emp_id not in employees_data:
                employees_data[emp_id] = {
                    'employee_number': emp_biometric,
                    'employee_name': emp_name,
                    'daily_rate': emp_daily_rate,
                    'days_worked': set(),  # Usar set para días únicos
                    'total_hours': 0.0,
                }
            
            # Agregar el día (agrupar por fecha de solicitud)
            employees_data[emp_id]['days_worked'].add(str(overtime.requested_date))
            # Sumar horas
            employees_data[emp_id]['total_hours'] += overtime.hours_taken or 0.0
        
        # Construir la lista final con cálculos
        table_data = []
        for emp_id, data in employees_data.items():
            days_count = len(data['days_worked'])
            total_hours = data['total_hours']
            daily_rate = data['daily_rate']
            
            # Cálculo del total: (salario_diario / 8) * 2 * horas_extras
            # Usamos /8 para mantener compatibilidad con el sistema antiguo
            # donde la hora ordinaria = daily_rate / 8 y la hora extra se paga al doble.
            total_cost = (daily_rate / 8) * 2 * total_hours if daily_rate > 0 else 0.0
            
            table_data.append({
                'employee_number': data['employee_number'],
                'daily_rate': daily_rate,
                'employee_name': data['employee_name'],
                'days_worked': days_count,
                'hours_taken': total_hours,
                'total': total_cost,
            })
        
        return table_data

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Asignar folio solo cuando el estado es pending
            if vals.get('state') == 'pending':
                # Asegurarse de que la secuencia existe
                sequence = self.env['ir.sequence'].search([('code', '=', 'overtime')], limit=1)
                if not sequence:
                    # Crear la secuencia si no existe
                    sequence = self.env['ir.sequence'].create({
                        'name': 'Solicitud de Tiempo Extra',
                        'code': 'overtime',
                        'prefix': 'OT/%(y)s/%(month)s/',
                        'padding': 4,
                    })
                vals['name'] = sequence.next_by_code('overtime') or _('Nuevo')
        return super().create(vals_list)

    def _assign_folio_if_pending(self):
        """Método para asignar folio cuando el registro está en estado pending"""
        for record in self:
            if record.state == 'pending' and (not record.name or record.name == _('Nuevo')):
                # Asegurarse de que la secuencia existe
                sequence = self.env['ir.sequence'].search([('code', '=', 'overtime')], limit=1)
                if not sequence:
                    # Crear la secuencia si no existe
                    sequence = self.env['ir.sequence'].create({
                        'name': 'Solicitud de Tiempo Extra',
                        'code': 'overtime',
                        'prefix': 'OT/%(y)s/%(month)s/',
                        'padding': 4,
                    })
                record.name = sequence.next_by_code('overtime') or _('Nuevo')

    def write(self, vals):
        result = super().write(vals)
        # Asignar folio después del write si el estado cambió a pending
        if vals.get('state') == 'pending':
            self._assign_folio_if_pending()
        return result

    def action_submit_and_split(self):
        self.ensure_one()
        new_requests = self.env['overtime']

        if not self.employee_line_ids:
            raise ValidationError("Debe agregar al menos un empleado para la solicitud de tiempo extra.")

        # Iterar sobre cada línea de empleado para crear un registro principal individual
        for line in self.employee_line_ids:
            new_vals = {
                'supervisor_id': self.supervisor_id.id,
                'department_id': self.department_id.id,
                'area_id': self.area_id.id,
                'requested_date': self.requested_date,
                'justification': self.justification,
                'state': 'pending',
                'employee_id': line.employee_id.id,
                'time_from': line.time_from,
                'time_to': line.time_to,
                'hours_taken': line.hours_taken,
                'activity': line.activity,
            }

            new_request = new_requests.create(new_vals)
            new_requests |= new_request

        # Asegurar que todos los registros tengan folio asignado
        new_requests._assign_folio_if_pending()

        # Eliminar la solicitud original (la que tiene las líneas)
        self.unlink()

        return {
            'name': _('Solicitudes de Tiempo Extra Creadas'),
            'res_model': 'overtime',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_requests.ids)],
            'target': 'main',
            'type': 'ir.actions.act_window',
        }

    def action_approve(self):
        self.ensure_one()
        self.authorized_by_id = self.env.user.id
        self.state = 'approved'

    def action_reject(self):
        self.ensure_one()
        return {
            'name': 'Motivo de Rechazo',
            'type': 'ir.actions.act_window',
            'res_model': 'overtime.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_overtime_id': self.id}
        }
    
    @api.depends('employee_id', 'requested_date')
    def _compute_attendance_log(self):
        Attendance = self.env['hr.attendance']
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        user_tz = timezone(tz_name)

        for record in self:
            record.attendance_log = False

            if record.employee_id and record.requested_date:
                date_start = fields.Datetime.to_datetime(record.requested_date)
                date_end = date_start + timedelta(days=2)

                attendances = Attendance.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('check_in', '>=', date_start),
                    ('check_in', '<', date_end),
                ], order='check_in asc')

                log_lines=[]
                if attendances:
                    for att in attendances:
                        if att.check_in:
                            check_in_time = fields.Datetime.context_timestamp(att, timestamp=att.check_in)
                            formatted_time = check_in_time.strftime('%d-%m-%Y %H:%M:%S')
                            log_lines.append(formatted_time)
                    
                    record.attendance_log = '\n'.join(log_lines)
                else:
                    record.attendance_log = "No se han registrado checadas del empleado"
