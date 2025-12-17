
from odoo import api, fields, models
import pytz

class ShiftManagement(models.Model):
    _name = 'shift.management'
    _description = 'Gestión de Turnos de Empleados'
    _rec_name = 'turno_name'

    turno_name = fields.Char(string='Nombre del Turno')
    hora_entrada = fields.Datetime(string='Hora de Entrada')
    hora_salida = fields.Datetime(string='Hora de Salida')

    work_monday = fields.Boolean(string='Lunes', default=True)
    work_tuesday = fields.Boolean(string='Martes', default=True)
    work_wednesday = fields.Boolean(string='Miércoles', default=True)
    work_thursday = fields.Boolean(string='Jueves', default=True)
    work_friday = fields.Boolean(string='Viernes', default=True)
    work_saturday = fields.Boolean(string='Sábado', default=False)
    work_sunday = fields.Boolean(string='Domingo', default=False)


    # Campo relacionado para ver qué empleados usan este turno
    employee_ids = fields.One2many(
        comodel_name='hr.employee',
        inverse_name='turno_id',
        string='Empleados Asignados'
    )
    
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        default=lambda self: self.env.company,
        required=True
    )

    hora_entrada_str = fields.Char(
        string='Hora de Entrada:',
        compute='_compute_hora_str',
        store=False 
    )
    
    hora_salida_str = fields.Char(
        string='Hora de Salida:',
        compute='_compute_hora_str',  
        store=False
    )


    # MÉTODO CALCULADO
    @api.depends('hora_entrada', 'hora_salida')

    def _compute_hora_str(self):
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        
        TIME_FORMAT = "%H:%M"
 
        
        for record in self:

            def format_utc_to_local_time(datetime_utc):
                if not datetime_utc:
                    return False
                
                datetime_local = pytz.utc.localize(datetime_utc).astimezone(local_tz)
                
                return datetime_local.strftime(TIME_FORMAT)

            record.hora_entrada_str = format_utc_to_local_time(record.hora_entrada)
            record.hora_salida_str = format_utc_to_local_time(record.hora_salida)
