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
    employee_id = fields.Many2one('hr.employee', string='Empleado')
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
        Retorna los datos para la tabla dinámica del dashboard con columnas por día
        Estructura: {
            'headers': [{'date': '2026-01-16', 'day_label': 'V16'}, ...],
            'rows': [
                {
                    'employee_number': '1234',
                    'employee_name': 'Juan Perez',
                    'daily_rate': 250.00,
                    'days': {
                        '2026-01-16': {'hours': 2.5, 'amount': 125.00},
                        '2026-01-17': {'hours': 0, 'amount': 0},
                    },
                    'total_hours': 2.5,
                    'total_amount': 125.00
                }
            ]
        }
        """
        from datetime import datetime, timedelta
        
        domain = [
            ('requested_date', '>=', start_date),
            ('requested_date', '<=', end_date),
            ('state', '=', 'approved'),
        ]
        
        overtimes = self.search(domain, order='employee_id, requested_date')
        
        # Generar todas las fechas del rango
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        all_dates = []
        current = start_dt
        while current <= end_dt:
            all_dates.append(current)
            current += timedelta(days=1)
        
        # Encontrar qué días tienen al menos una entrada de tiempo extra
        dates_with_overtime = set()
        for overtime in overtimes:
            dates_with_overtime.add(overtime.requested_date)
        
        # Filtrar solo los días que tienen tiempo extra
        active_dates = [d for d in all_dates if d in dates_with_overtime]
        
        # Construir headers con formato de día (ej: "V16" para viernes 16)
        day_names = ['L', 'M', 'X', 'J', 'V', 'S', 'D']  # Lun, Mar, Mie, Jue, Vie, Sab, Dom
        headers = []
        for date in active_dates:
            day_of_week = day_names[date.weekday()]
            day_number = date.day
            headers.append({
                'date': str(date),
                'day_label': f'{day_of_week}{day_number:02d}'
            })
        
        # Agrupar por empleado y fecha
        employees_data = {}
        
        for overtime in overtimes:
            emp_id = overtime.employee_id.id
            emp_name = overtime.employee_id.name
            emp_biometric = overtime.employee_id.biometric_id or 'N/A'
            emp_daily_rate = overtime.employee_id.daily_rate or 0.0
            overtime_date = str(overtime.requested_date)
            
            if emp_id not in employees_data:
                employees_data[emp_id] = {
                    'employee_number': emp_biometric,
                    'employee_name': emp_name,
                    'daily_rate': emp_daily_rate,
                    'days': {},
                    'total_hours': 0.0,
                    'total_amount': 0.0,
                }
            
            # Si ya existe entrada para este día, sumar (en caso de múltiples registros)
            if overtime_date in employees_data[emp_id]['days']:
                employees_data[emp_id]['days'][overtime_date]['hours'] += overtime.hours_taken or 0.0
            else:
                employees_data[emp_id]['days'][overtime_date] = {
                    'hours': overtime.hours_taken or 0.0,
                }
            
            # Calcular el monto por día: (salario_diario / 8) * 2 * horas
            hours = employees_data[emp_id]['days'][overtime_date]['hours']
            amount = (emp_daily_rate / 8) * 2 * hours if emp_daily_rate > 0 else 0.0
            employees_data[emp_id]['days'][overtime_date]['amount'] = amount
        
        # Construir las filas finales
        rows = []
        for emp_id, data in employees_data.items():
            # Asegurar que todos los días activos estén presentes (incluso si es 0)
            for date in active_dates:
                date_str = str(date)
                if date_str not in data['days']:
                    data['days'][date_str] = {'hours': 0.0, 'amount': 0.0}
            
            # Calcular totales
            total_hours = sum(day_data['hours'] for day_data in data['days'].values())
            total_amount = sum(day_data['amount'] for day_data in data['days'].values())
            
            data['total_hours'] = total_hours
            data['total_amount'] = total_amount
            rows.append(data)
        
        # Calcular totales por columna (día)
        column_totals = {}
        grand_total_hours = 0.0
        grand_total_amount = 0.0
        
        for date in active_dates:
            date_str = str(date)
            column_totals[date_str] = {'hours': 0.0, 'amount': 0.0}
            
            for row in rows:
                if date_str in row['days']:
                    column_totals[date_str]['hours'] += row['days'][date_str]['hours']
                    column_totals[date_str]['amount'] += row['days'][date_str]['amount']
            
            grand_total_hours += column_totals[date_str]['hours']
            grand_total_amount += column_totals[date_str]['amount']
        
        # Ordenar filas por número de empleado (menor a mayor)
        rows_sorted = sorted(rows, key=lambda x: int(x['employee_number']) if x['employee_number'].isdigit() else 999999)
        
        return {
            'headers': headers,
            'rows': rows_sorted,
            'column_totals': column_totals,
            'grand_total_hours': grand_total_hours,
            'grand_total_amount': grand_total_amount,
        }

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
