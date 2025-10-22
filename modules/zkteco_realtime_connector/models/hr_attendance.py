from odoo import fields, models, api, _
from datetime import datetime, timedelta
import pytz

class HrAttendance(models.Model):

    _inherit = 'hr.attendance'

    punctuality_status = fields.Selection([
        ('on_time','A Tiempo'),
        ('late','Retardo'),
        ('LunchS','Salida de Planta'),
        ('LunchE','Regreso a Planta'),
        ('end','Fin de turno'),
        ('n/a','No aplica'),
    ], string='Estatus de Puntualidad', default='n/a')

    check_in_time_only = fields.Char(
            string='Hora de Checada',
            compute='_compute_check_in_time_only',
            store=False # No se almacena en la base de datos
        )

    def _compute_check_in_time_only(self):
        # Obtener la zona horaria del usuario logueado para mostrar la hora correcta
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        
        for record in self:
            if record.check_in:
                # 1. Localizar el datetime UTC (check_in) a la zona horaria del usuario
                utc_datetime = pytz.utc.localize(record.check_in)
                local_datetime = utc_datetime.astimezone(local_tz)
                
                # 2. Formatear para mostrar solo la hora (HH:MM)
                record.check_in_time_only = local_datetime.strftime("%H:%M:%S")
            else:
                    record.check_in_time_only = False