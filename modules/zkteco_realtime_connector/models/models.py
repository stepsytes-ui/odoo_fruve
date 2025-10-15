# -*- coding: utf-8 -*-

import pytz
import logging
from datetime import datetime
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

FIXED_DEVICE_TIMEZONE_NAME = 'America/Tijuana'

class ZkTecoAttendanceLog(models.Model):
    _name = 'zkteco.attendance.log'
    _description = 'Raw Attendance Logs from ZKTeco Device'
    _order = 'timestamp desc'

    device_id = fields.Char(string='Device ID')
    user_id = fields.Char(string='User ID (Biometric)')
    timestamp = fields.Datetime(string='Timestamp')
    state = fields.Selection([
        ('new', 'New'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ], string='Status', default='new', required=True, copy=False)
    raw_data = fields.Text(string='Raw Data')
    
    hr_attendance_id = fields.Many2one('hr.attendance', string='Odoo Attendance Record', readonly=True)

    def process_logs(self):
        records_to_process = self.filtered(lambda l: l.state == 'new').sudo()
        
        Attendance = self.env['hr.attendance'].sudo()
        Employee = self.env['hr.employee'].sudo()

        if not records_to_process:
            return
        # 1. PREPARACIÓN DE ZONAS HORARIAS
        UTC_TIMEZONE = pytz.utc
        try:
            # Intentamos crear el objeto de zona horaria a partir de la constante definida
            FIXED_TIMEZONE = pytz.timezone(FIXED_DEVICE_TIMEZONE_NAME)
        except pytz.UnknownTimeZoneError:
            _logger.error("Configuration Error: The defined timezone '%s' in FIXED_DEVICE_TIMEZONE_NAME is invalid. All logs set to 'error'.", FIXED_DEVICE_TIMEZONE_NAME)
            records_to_process.write({'state': 'error'})
            return
        
        for log in records_to_process:
            search_id = str(log.user_id)
            employee = Employee.search([('biometric_id', '=', search_id)], limit=1)

            if employee:
                _logger.info("ZKTeco Processor: SUCCESS! Employee found for user_id %s: %s", search_id, employee.name)
                
                try:
                    naive_datetime = fields.Datetime.from_string(log.timestamp) 
                    local_datetime = FIXED_TIMEZONE.localize(naive_datetime, is_dst=None)
                    utc_datetime = local_datetime.astimezone(UTC_TIMEZONE).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                   
                    last_attendance = employee.last_attendance_id.sudo()
                    
                    if last_attendance and not last_attendance.check_out:
                        last_attendance.write({
                            'check_out': utc_datetime,
                        })
                        attendance_record = last_attendance
                        _logger.info("CHECK-OUT processed for %s at %s", employee.name, log.timestamp)
                    else:
                        attendance_record = Attendance.create({
                            'employee_id': employee.id,
                            'check_in': utc_datetime,
                        })
                        _logger.info("CHECK-IN processed for %s at %s", employee.name, log.timestamp)
                    
                    if attendance_record:
                        log.write({
                            'state': 'processed',
                            'hr_attendance_id': attendance_record.id
                        })
                    else:
                        raise Exception("Attendance record could not be created or found.")

                except Exception as e:
                    _logger.error("Final Error processing attendance for %s: %s", employee.name, str(e))
                    log.state = 'error'

            else:
                _logger.warning("ZKTeco Processor: Employee NOT FOUND in Odoo for Biometric ID: %s. Log marked as error.", search_id)
                log.state = 'error'
