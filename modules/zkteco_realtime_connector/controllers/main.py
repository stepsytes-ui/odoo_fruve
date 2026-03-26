# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ZkTecoWebhook(http.Controller):

    @http.route('/iclock/cdata', type='http', auth='none', methods=['POST', 'GET'], csrf=False)
    def handle_zk_notification(self, **post):
        if request.httprequest.method == 'POST':
            
            raw_data = request.httprequest.get_data(as_text=True)
            _logger.info("ZKTeco POST Data Body: %s", raw_data)

            try:
                SUPERUSER_ID = request.env.ref('base.user_admin').id
                Env = request.env(user=SUPERUSER_ID)
            except Exception:
                Env = request.env(user=1) 
            # -------------------------------------------------------------------
            
            if raw_data:
                log_lines = raw_data.strip().split('\n')
                
                for line in log_lines:
                    if not line or line.startswith('OPLOG'):
                        continue
                        
                    parts = line.split() 
                    
                    if len(parts) >= 4:
                        user_id = parts[0]
                        if len(parts) >= 3:
                            check_date = parts[1]
                            check_time = parts[2]
                        elif len(parts) == 2: 
                            check_date = parts[1].split(' ')[0]
                            check_time = parts[1].split(' ')[1]
                        else:
                             _logger.error("Line format error: Not enough parts in log line: %s", line)
                             continue


                        check_time_str = f"{check_date} {check_time}"
                        
                        try:
                            log_record = Env['zkteco.attendance.log'].create({
                                'device_id': post.get('SN'),
                                'user_id': user_id,
                                'timestamp': check_time_str, 
                                'raw_data': line,
                            })
                            
                            log_record.process_logs()
                            _logger.info("Log created successfully for User ID: %s at %s", user_id, check_time_str)
                        except Exception as e:
                            _logger.error("Error saving/processing log for %s: %s", user_id, str(e))
                            
                return 'OK'
            
            _logger.warning("POST received, but the request body was empty. This might be a final ADMS signal.")
            return 'OK'
        
        elif request.httprequest.method == 'GET':
            _logger.info("ZKTeco Handshake received: %s", post)

            response_command = "GET ATTLOG" 

            return f"OK\r\n{response_command}\r\n"


class AttendanceReportController(http.Controller):

    @http.route('/attendance/report/preview/<int:wizard_id>', auth='user', type='http', methods=['GET'], csrf=False)
    def preview_attendance_report(self, wizard_id, **kwargs):
        """Renderiza una vista previa HTML del reporte de asistencia sin crear archivos."""
        wizard = request.env['attendance.report.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()
        try:
            html_content = wizard._build_preview_html()
        except Exception as e:
            _logger.exception("Error generando vista previa del reporte %s", wizard_id)
            error_html = (
                '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Error</title>'
                '<style>body{font-family:Arial,sans-serif;padding:40px;color:#c00}</style></head>'
                f'<body><h2>Error al generar la vista previa</h2><pre>{str(e)}</pre></body></html>'
            )
            return request.make_response(
                error_html,
                headers=[('Content-Type', 'text/html; charset=utf-8')],
            )
        return request.make_response(
            html_content,
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )

    @http.route('/attendance/report/download/<int:wizard_id>', auth='user', type='http', methods=['GET'], csrf=False)
    def download_attendance_report(self, wizard_id, **kwargs):
        """Descarga el Excel del reporte de asistencia directamente sin crear archivos adjuntos."""
        wizard = request.env['attendance.report.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()
        try:
            file_bytes, filename = wizard._generate_excel_file()
        except Exception as e:
            _logger.exception("Error generando Excel del reporte %s", wizard_id)
            return request.make_response(
                str(e),
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
            )
        return request.make_response(
            file_bytes,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', str(len(file_bytes))),
            ],
        )
