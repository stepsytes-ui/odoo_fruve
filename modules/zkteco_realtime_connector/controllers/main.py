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
            response_command += "\nREBOOT"

            return f"OK\r\n{response_command}\r\n"
