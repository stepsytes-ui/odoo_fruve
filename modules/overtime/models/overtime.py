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


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('overtime') or _('Nuevo') 
        return super().create(vals_list)
    
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
            
        # 1. Eliminar la solicitud original (la que tiene las líneas)
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
