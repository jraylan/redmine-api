from datetime import datetime, date
from flask import Flask, request
import os
import json
import psycopg2
import models

def create_app(allowed_hosts, log, test_config=None):
    app = Flask(__name__, instance_relative_config=True)


    DB_CONNECTION_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', 5432),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', '.postmy'),
        'dbname': os.environ.get('DB_NAME', 'redmine')
    }
    
    def dbconnection(view):
        def wrapper(*args, **kwargs):
            connection = psycopg2.connect(**DB_CONNECTION_CONFIG)
            cursor = connection.cursor()
            kwargs['cursor'] = cursor
            try:
                result = view(*args, **kwargs)
                connection.commit()
                return result
            except Exception as e:
                connection.rollback()
                return {"error": str(e)}
            finally:
                cursor.close()
                connection.close()
                
        return wrapper


    def login_required(view):
        def wrapped_view(*args, **kwargs):
            authorization = request.headers.get('Authorization')
            if authorization is None:
                return {'error': 'Unauthorized'}, 401
            else:
                try:
                    auth_type, params = authorization.split()
                    if auth_type != 'Basic':
                        return {'error': 'Unauthorized'}, 401
                    login, password = params.decode('base64').split(':')
                    query, params = models.User.login_query(login, password)
                    cursor = kwargs['cursor']
                    cursor.begin()
                    cursor.execute(query, params)
                    user = cursor.fetchone()
                    cursor.commit()
                    if user is None:
                        return {'error': 'Unauthorized'}, 401
                    else:
                        kwargs['user'] = models.User.from_query(user)
                        return view(*args, **kwargs)
                except:
                    return {'error': 'Unauthorized'}, 401

            return view(*args, **kwargs)

    @app.route('/issues', methods=['GET'])
    @dbconnection
    @login_required
    def list_issues(*args, **kwargs):
        if '*' not in allowed_hosts and request.remote_addr not in allowed_hosts:
            print(request.remote_addr, allowed_hosts)
            return {'error': 'Unauthorized'}, 401
        
        query, params = models.Issue.filter_query(
            {
                **request.args
            }
        )
        try:
            with psycopg2.connection(DB_CONNECTION_CONFIG).cursor() as cursor:
                cursor.begin()
                cursor.execute(query, params)
                issues = cursor.fetchall()
                cursor.commit()
                return json.dumps([models.Issue.from_query(issue).to_dict() for issue in issues])
        except Exception as e:
            return json.dumps({"error": str(e)})

    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7171))
    allowed_hosts = os.environ.get('ALLOWED_HOSTS', '127.0.0.1').split(',')
    ip = os.environ.get('HOST', '0.0.0.0')

    with open('api.log', 'at') as log:
        create_app(allowed_hosts, log).run(host=ip, port=port)
