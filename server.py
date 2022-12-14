from base64 import b64decode
from flask import Flask, request
import models
import os
import psycopg2
import traceback

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
        def wrapped_view(*args, **kwargs):
            connection = psycopg2.connect(**DB_CONNECTION_CONFIG)
            cursor = connection.cursor()
            kwargs['cursor'] = cursor
            try:
                cursor.execute("BEGIN")
                result = view(*args, **kwargs)
                cursor.execute("COMMIT")
            except Exception as e:
                traceback.print_exc()
                connection.rollback()
                return {"error": str(e)}
            else:
                connection.commit()
                return result
            finally:
                cursor.close()
                connection.close()

        wrapped_view.__name__ = view.__name__
        return wrapped_view


    def login_required(view):
        def wrapped_view(*args, **kwargs):
            if '*' not in allowed_hosts and request.remote_addr not in allowed_hosts:
                print(request.remote_addr, allowed_hosts)
                return {'error': 'Unauthorized'}, 401
            authorization = request.headers.get('Authorization')
            if authorization is None:
                return {'error': 'Unauthorized'}, 401
            else:
                try:
                    auth_type, params = authorization.split()
                    if auth_type != 'Basic':
                        return {'error': 'Unauthorized'}, 401
                    login, password = b64decode(params).decode('utf-8').split(':')
                    query, params = models.User.login_query(login, password)
                    cursor = kwargs['cursor']
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    if not rows or len(rows) != 1:
                        return {'error': 'Unauthorized'}, 401
                    else:
                        kwargs['user'] = models.User.from_dict(
                            dict(zip(columns, rows[0]))
                        )
                        return view(*args, **kwargs)
                except:
                    traceback.print_exc()
                    return {'error': 'Unauthorized'}, 401
        wrapped_view.__name__ = view.__name__
        return wrapped_view

    @app.route('/issues', methods=['GET'])
    @dbconnection
    @login_required
    def list_issues(*args, **kwargs):
        query, params = models.Issue.filter(**request.args)
        cursor = kwargs['cursor']
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns=[desc[0] for desc in cursor.description]

            result = []
            for row in rows:
                issue = models.Issue.from_dict(
                        dict(zip(columns, row))
                    ).to_json()
                cursor.execute(*models.Checklist.filter(issue_id=issue['id']))
                cl_rows = cursor.fetchall()
                cl_columns = [desc[0] for desc in cursor.description]
                issue['checklist'] = [
                    models.ChecklistItem.from_dict(
                        dict(zip(cl_columns, cl_row))
                    ).to_json()
                    for cl_row in cl_rows
                ]
                result.append(issue)
            return result
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}


    @app.route('/issues', methods=['POST'])
    @dbconnection
    @login_required
    def create_issues(*args, **kwargs):
        try:
            data = request.get_json(force=True)
            
            checklists = data.pop('checklists', [])

            issue = models.Issue.from_dict(
                data
            )
            issue.author_id = kwargs['user'].id
            cursor = kwargs['cursor']
            cursor.execute(*issue.insert_query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            issue.update_from_dict(dict(zip(columns, rows[0])))
            
            response = issue.to_json()
            checklists_pos = []
            checklists_json = []
            for pos,chkls in enumerate(checklists):
                chkls['issue_id'] = issue.id
                if chkls.get('position') and isinstance(chkls.get('position'), int):
                    pos = chkls.pop('position')
                if pos in checklists_pos:
                    pos = max(checklists_pos) + 1
                checklists_pos.append(pos)
                chkls['position'] = pos
                checklist = models.Checklist.from_dict(chkls)
                cursor.execute(*checklist.insert_query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                checklist.update_from_dict(dict(zip(columns, rows[0])))
                checklists_json.append(checklist.to_json())
            
            if checklists_json:
                response['checklists'] = checklists_json
            return response

        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}
    return app



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7171))
    allowed_hosts = os.environ.get('ALLOWED_HOSTS', '127.0.0.1').split(',')
    ip = os.environ.get('HOST', '0.0.0.0')

    with open('api.log', 'at') as log:
        create_app(allowed_hosts, log).run(host=ip, port=port)
