from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OvertimeEmployeeLine(models.Model):
    _name = 'overtime.employee.line'
    _description = 'Línea de Empleado en Solicitud de Tiempo Extra'

    overtime_id = fields.Many2one('overtime', string='Solicitud de Tiempo Extra', required=True, ondelete='cascade')
    biometric_id = fields.Char(string='Número de Empleado')
    employee_id = fields.Many2one('hr.employee', string='Empleado',)
    time_from = fields.Float(string='Desde', required=True)
    time_to = fields.Float(string='Hasta', required=True)
    hours_taken = fields.Float(string='Horas', compute='_compute_hours', store=True, readonly=True)
    activity = fields.Text(string='Actividad', required=True)

    @api.depends('time_from', 'time_to')
    def _compute_hours(self):
        """Calcula la diferencia entre Hora Hasta y Hora Desde."""
        for line in self:
            hours = line.time_to - line.time_from

            if hours < 0:
                hours = (24.0 - line.time_from) + line.time_to
            line.hours_taken = hours

    @api.onchange('biometric_id')
    def _onchange_biometric_id(self):
        """Busca el empleado por el biometric_id al cambiar el campo."""
        self.employee_id = False
        if self.biometric_id:
            employee = self.env['hr.employee'].search([
                ('biometric_id', '=', self.biometric_id)
            ], limit=1)
            
            if employee:
                self.employee_id = employee
            else:
                warning_msg = "No se encontró ningún empleado con el número: %s" % self.biometric_id
                return {'warning': {'title': "Error de Búsqueda", 'message': warning_msg}}
    
    @api.constrains('time_from', 'time_to')
    def _check_time_range(self):
        """Asegura que las horas estén entre 0 y 24."""
        for line in self:
            
            time_from_display = '{:02.0f}:{:02.0f}'.format(int(line.time_from), int(round((line.time_from % 1) * 60)))
            time_to_display = '{:02.0f}:{:02.0f}'.format(int(line.time_to), int(round((line.time_to % 1) * 60)))
            
            if line.time_from < 0 or line.time_from >= 24.0:
                raise ValidationError(
                    _("Error en Hora ""Desde"": El valor '%s' no es válido. La hora debe estar entre 00:00 y 23:59." % time_from_display)
                )
            
            if line.time_to <= 0 or line.time_to > 24.0:
                raise ValidationError(
                    _("Error en el campo de tiempo ""Hasta"": El valor '%s' no es válido. La hora debe estar entre 00:01 y 24:00." % time_to_display)
                )
