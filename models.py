from collections import OrderedDict
from datetime import datetime




AVAILABLE_TYPES = (
    str,
    int,
    float,
    datetime,
    bool,
    type(None)
)

SERIALIZABLE_TYPES = (
    str,
    int,
    float,
    bool,
    type(None)
)

class Model(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            if hasattr(self, k) and isinstance(v,AVAILABLE_TYPES):
                setattr(self, k, v)

    @classmethod
    def from_dict(cls, query):
        return cls(**query)

    def to_json(self):
        return OrderedDict([
            (k, str(v) if not isinstance(v, SERIALIZABLE_TYPES) else v)
            for k,v in self.__dict__.items()\
            if not k.startswith('_') and isinstance(v, AVAILABLE_TYPES)
        ])

    def update_from_dict(self, query):
        for k, v in query.items():
            if hasattr(self, k) and isinstance(v,AVAILABLE_TYPES):
                setattr(self, k, v)

    def update_fields_query(self, **kwargs):
        if not self.id:
            raise Exception('Cannot update fields on an object without an id')
        fields = {
            k: v for k, v in kwargs.items()
            if hasattr(self, k) and isinstance(v,AVAILABLE_TYPES)
        }
        query = f'''
            UPDATE {self.table_name}
            SET {','.join([f'{k}=%s' for k in fields])}
            WHERE id=%s
        '''.strip()

        return query, [*fields.values(),self.id]

    @property
    def table_name(self):
        return self.get_table_name()

    @property
    def insert_query(self):
        fields = self.insert_fields
        query = f'''
            INSERT INTO {self.table_name}
                (id, {','.join(fields.keys())})
            VALUES
                (default, {','.join(['%s' for _ in fields])})
            RETURNING *;
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
        if not query:
            return f'SELECT * FROM {cls.get_table_name()}', ()
        return f'''
            SELECT * FROM {cls.get_table_name()}
            WHERE {' AND '.join([f'{k}=%s' for k in kwargs])}
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
            'tracker_id': self.tracker_id,
            'project_id': self.project_id,
            'subject': self.subject,
            'description': self.description,
            'category_id': self.category_id,
            'status_id': self.status_id,
            'assigned_to_id': self.assigned_to_id,
            'priority_id': self.priority_id,
            'author_id': self.author_id,
            'created_on': self.created_on or datetime.now(),
            'updated_on': self.updated_on or datetime.now(),
            'lock_version': 1,
            'lft': 1,
            'rgt': 2,
            'root_id': self.root_id or self.id,
        })
        return fields

    @property
    def update_fields(self) -> OrderedDict:
        fields = self.insert_fields
        return fields

    @staticmethod
    def get_table_name():
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

    @staticmethod
    def get_table_name():
        return "checklists"

    @property
    def update_fields(self) -> OrderedDict:
        fields = OrderedDict({
            'is_done': self.is_done or False,
            'subject': self.subject,
            'position': self.position,
            'issue_id': self.issue_id,
            'created_at': self.created_at or datetime.now(),
            'updated_at': self.updated_at or datetime.now(),
            'is_section': self.is_section or False
        })
        return fields

    @property
    def insert_fields(self) -> OrderedDict:
        fields = self.update_fields
        return fields


class User(Model):
    id:int = None
    login:str = None
    firstName:str = None
    lastName:str = None

    @staticmethod
    def get_table_name():
        return "users"

    @classmethod
    def login_query(cls, login, password):
        return f'''
        SELECT
            id, login,
            firstName, lastName
        FROM
            {cls.get_table_name()}
        WHERE
            login = %s AND
             hashed_password = encode(digest(salt||encode(digest(%s, 'sha1'), 'hex'), 'sha1'), 'hex');
        ''', (login, password)

