from collections import OrderedDict
from datetime import datetime


class Model(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.values():
            if hasattr(self, k):
                setattr(self, k, v)

                
    @classmethod
    def from_query(cls, query):
        return cls(**query)

    def to_json(self):
        return OrderedDict([
            (k,v) for k,v in self.__dict__.items() if not k.startswith('_') and isinstance(v, (str, int, float, datetime, bool, type(None)))
        ])

    @property
    def insert_query(self):
        fields = self.fields
        query = f'''
            INSERT INTO {self.table_name}
                ({''.join(fields.keys())}))
            VALUES
                ({','.join(['%s' for _ in fields])})
        '''.strip()
        return query, tuple(fields.values())

    @property
    def update_query(self):
        fields = self.update_fields
        query = f'''
            UPDATE {self.table_name}
            SET {','.join([f'{k}=%s' for k in fields])}
            WHERE id=%s
        '''.strip()
        return query, tuple(fields.values()) + (self.id,)

    @property
    def delete_query(self):
        return f'DELETE FROM {self.table_name} WHERE id=%s', (self.id,)

    @classmethod
    def filter(cls, **kwargs):
        query = OrderedDict({})
        for k,v in kwargs.items():
            if hasattr(cls, k):
                query[k] = v                
        return f'''
            SELECT * FROM {cls.table_name}
            WHERE {','.join([f'{k}=%s' for k in kwargs])}
        ''', tuple(kwargs.values())


class Issue(Model):
    id: int = None
    tracker_id: int = None
    project_id: int = None
    subject = None
    description = None
    category_id: int = None
    status_id: int = None
    assigned_to_id: int = None
    priority_id: int = None
    author_id: int = None
    created_on: datetime = None
    updated_on: datetime = None
    root_id: int = None

    @property
    def insert_fields(self) -> OrderedDict:
        fields = OrderedDict({
            'id': None,
            'tracker_id': self.tracker_id,
            'project_id': self.project_id,
            'subject': self.subject,
            'description': self.description,
            'category_id': self.category_id,
            'status_id': self.status_id,
            'assigned_to_id': self.assigned_to_id,
            'priority_id': self.priority_id,
            'author_id': self.author_id,
            'created_on': self.created_on,
            'updated_on': self.updated_on,
            'root_id': self.root_id,
        })
        return fields
    
    @property
    def update_fields(self) -> OrderedDict:
        fields = self.insert_fields
        del fields[id]
        return fields

    @classmethod
    @property
    def table_name(cls):
        return "issues"


class Checklist(Model):
    id:int = None
    is_done: bool = None
    subject:str = None
    position:int = None
    issue_id:int = None
    created_at:datetime = None        
    updated_at:datetime = None        
    is_section:bool = None

    @classmethod
    @property
    def table_name(cls):
        return "checklist"

    @property
    def insert_fields(self) -> OrderedDict:
        fields = OrderedDict({
            'id': None,
            'is_done': self.is_done,
            'subject': self.subject,
            'position': self.position,
            'issue_id': self.issue_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_section': self.is_section
        })        
        return fields
    
    @property
    def update_fields(self) -> OrderedDict:
        fields = self.insert_fields
        del fields[id]
        return fields


class User(Model):
    id:int = None
    login:str = None
    firstName:str = None
    lastName:str = None

    @classmethod
    @property
    def table_name(cls):
        return "users"

    @classmethod
    def login_query(cls, login, password):
        return f'''
        SELECT
            id, login,
            firstName, lastName
        FROM
            {cls.table_name}
        WHERE
            login = %s
            password = encode(digest(encode(digest(%s, 'sha1'), 'hex')||salt, 'sha1'), 'hex');
        ''', (login, password)

