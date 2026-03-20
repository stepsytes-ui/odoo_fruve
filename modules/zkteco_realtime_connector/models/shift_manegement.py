from odoo import api, fields, models
import pytz

class ShiftManagement(models.Model):
    _name = 'shift.management'
    _description = 'Gestión de Turnos de Empleados'
    _rec_name = 'turno_name'
    _order = 'turno_name asc, id asc'

    turno_name = fields.Char(string='Nombre del Turno')
    hora_entrada = fields.Datetime(string='Hora de Entrada')
    hora_salida = fields.Datetime(string='Hora de Salida')

    work_monday = fields.Boolean(string='Lunes', default=True)
    special_monday = fields.Boolean(string='Especial Lunes')
    in_monday = fields.Datetime(string='Entrada Lunes')
    out_monday = fields.Datetime(string='Salida Lunes')


    work_tuesday = fields.Boolean(string='Martes', default=True)
    special_tuesday = fields.Boolean(string='Especial tuesday')
    in_tuesday = fields.Datetime(string='Entrada tuesday')
    out_tuesday = fields.Datetime(string='Salida tuesday')

    work_wednesday = fields.Boolean(string='Miércoles', default=True)
    special_wednesday = fields.Boolean(string='Especial Miércoles')
    in_wednesday = fields.Datetime(string='Entrada Miércoles')
    out_wednesday = fields.Datetime(string='Salida Miércoles')

    work_thursday = fields.Boolean(string='Jueves', default=True)
    special_thursday = fields.Boolean(string='Especial Jueves')
    in_thursday = fields.Datetime(string='Entrada Jueves')
    out_thursday = fields.Datetime(string='Salida Jueves')

    work_friday = fields.Boolean(string='Viernes', default=True)
    special_friday = fields.Boolean(string='Especial Viernes')
    in_friday = fields.Datetime(string='Entrada Viernes')
    out_friday = fields.Datetime(string='Salida Viernes')

    work_saturday = fields.Boolean(string='Sábado', default=False)
    special_saturday = fields.Boolean(string='Especial Sábado')
    in_saturday = fields.Datetime(string='Entrada Sábado')
    out_saturday = fields.Datetime(string='Salida Sábado')

    work_sunday = fields.Boolean(string='Domingo', default=False)
    special_sunday = fields.Boolean(string='Especial Domingo')
    in_sunday = fields.Datetime(string='Entrada Domingo')
    out_sunday = fields.Datetime(string='Salida Domingo')

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

    resource_calendar_id = fields.Many2one(
        comodel_name='resource.calendar',
        string='Horario Laboral',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Calendario laboral que se asignará automáticamente al empleado cuando se seleccione este turno.'
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

    horario_carta_laboral = fields.Char(
        string='Horario para Carta Laboral',
        help='Texto del horario que aparecerá en la Carta Laboral. '
             'Ejemplo: LUNES A VIERNES DE 08:00 A 17:00 Y SÁBADO DE 08:00 A 13:00'
    )

    def get_times_for_date(self, target_date):
        """
        Retorna (entrada, salida) según el día de la semana y si es especial.
        """
        self.ensure_one()
        weekday = target_date.weekday() # 0=Lunes, 6=Domingo
        
        # Mapeo de campos por día de la semana
        day_map = {
            0: ('special_monday', 'in_monday', 'out_monday'),
            1: ('special_tuesday', 'in_tuesday', 'out_tuesday'),
            2: ('special_wednesday', 'in_wednesday', 'out_wednesday'),
            3: ('special_thursday', 'in_thursday', 'out_thursday'),
            4: ('special_friday', 'in_friday', 'out_friday'),
            5: ('special_saturday', 'in_saturday', 'out_saturday'),
            6: ('special_sunday', 'in_sunday', 'out_sunday'),
        }
        
        special_bool_field, in_field, out_field = day_map[weekday]
        
        # Si el día está marcado como especial, usamos sus horas. Si no, las generales.
        if getattr(self, special_bool_field):
            return getattr(self, in_field), getattr(self, out_field)
        
        return self.hora_entrada, self.hora_salida

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
