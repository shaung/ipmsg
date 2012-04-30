# -*- coding: utf-8 -*-

import os, os.path, json
from ConfigParser import SafeConfigParser

categories = ['common', 'log', 'other', ]

class Validator:
    def __init__(self, msg='', **kws):
        self.msg = msg
        self.setfunc(**kws)

    def setfunc(self, **kws):
        pass

    def __call__(self, getter=(lambda x:x), *args):
        args = [getter(x) for x in args]
        return self.func(*args), args

    @classmethod
    def make(cls, func, msg=''):
        self = cls(msg)
        self.func = func
        if msg:
            self.msg = msg
        return self

class LengthValidator(Validator):
    def setfunc(self, min=None, max=None):
        self.msg = self.msg or 'Length must in the range of {min}-{max} characters.'
        def func(*args):
            value = args[0]
            if (min and len(value) < min) or (max and len(value) > max):
                return self.msg.format(min=min, max=max)
            return ''
        self.func = func

class MyConfigParser(SafeConfigParser):
    def _srepr(self, obj):
        if type(obj) in (list, tuple, dict):
            orig = json.dumps(obj)
            return eval("u'''%s'''" % orig).encode('utf-8')
        else:
            return obj

    def _escape_str(self, text):
        return text.replace('\n', '\\n').replace('"', '\\"').replace('%', '%%')

    def _safe(self, item):
        rslt = item
        if type(item) in (list, tuple, set):
            rslt = self._safe_list(item)
        elif type(item) in (dict, ):
            rslt = self._safe_dict(item)
        elif type(item) in (str, unicode):
            rslt = self._escape_str(item)
        else:
            rslt = item
        return rslt

    def _safe_dict(self, d):
        rslt = {}
        for k, v in d.items():
            rslt[self._safe(k)] = self._safe(v)
        return rslt

    def _safe_list(self, li):
        rslt = [self._safe(item) for item in li]
        return rslt

    def set(self, section, option, value):
        SafeConfigParser.set(self, section, option, str(self._srepr(self._safe(value))))

    def get_as_type(self, section, option, tp=str):
        if tp is str:
            rslt = SafeConfigParser.get(self, section, option).replace('\\n', '\n')
        elif tp is bool:
            rslt = SafeConfigParser.getboolean(self, section, option)
        elif tp in (list, tuple, set, dict):
            rslt = [x for x in eval(SafeConfigParser.get(self, section, option))]
        elif tp in (dict, ):
            # TODO: dictionary parsing
            rslt = {}
        elif tp is int:
            rslt = SafeConfigParser.getint(self, section, option)
        else:
            rslt = SafeConfigParser.get(self, section, option)

        return rslt

class Settings:
    def __init__(self):
        self.path = ''
        self.parser = MyConfigParser()
        for cname in categories:
            self.parser.add_section(cname)

        self.fields = {
            'common': [
                ('user_name', ''),
                ('group_name', ''),
                ('group_list', []),
                ('use_status_as_group', False),
                ('stat_msg', [0, '']),
                ('enable_auto_reply', False),
                ('auto_reply_msg', ''),
                ('status_list', [(0, '^_^', ''),]),
            ],
            'log': [
                ('enable_log', True),
                ('log_encrypted_msg', True),
                ('log_use_utf8', True),
                ('log_logon_name', True),
                ('log_ip_address', True),
                ('log_file_path', os.path.expanduser('~/.ipmsg/ipmsg.log')),
            ],
            'message': [
                ('send_timeout', 10),
                ('quote_char', '>'),
                ('do_readmsg_chk', False),
            ],
            'other': [
                ('always_use_utf8', False),
                ('password', ''),
                ('include_list', []),
                ('block_list', []),
            ],
        }

        self.values = {}
        for cname, fields in self.fields.items():
            for name, default in fields:
                self.values[name] = default

        self.validators = []
        len_val = LengthValidator(msg='Length should not over {max}', max=100)
        self.validators.append((len_val, ('user_name',)))
        self.validators.append((len_val, ('group_name',)))
        self.validators.append((len_val, ('stat_msg',)))

    def add_fields(self, category, *fields):
        if category not in categories:
            categories.append(category)
            self.parser.add_section(category)
            self.fields[category] = []
        for field in fields:
            self.fields[category].append(field)
            name, default = field
            self.values[name] = default

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def from_file(self, fpath):
        pass

    def from_dict(self, d):
        pass

    def load(self, fpath):
        self.parser.read(fpath)
        self.path = fpath
        for cname in categories:
            for name, default in self.fields[cname]:
                self.values[name] = self.parser.get_as_type(cname, name, type(default))

    def save(self, fpath=None):
        for cname in categories:
            for name, default in self.fields[cname]:
                self.parser.set(cname, name, self.values[name])

        if not fpath:
            fpath = self.path
        with open(fpath, 'wb') as f:
            self.parser.write(f)

    def get_error(self, *fields):
        def getter(name):
            return self.values[name]

        if len(fields) > 0:
            val_list = [(val, args) for (val, args) in self.validators if [f for f in fields if f in args]]
        else:
            val_list = self.validators
        for (val, args) in val_list:
            rslt = val(getter, *args)
            if rslt[0]:
                return args, rslt
        return ''

settings = Settings()

def load_settings(fpath):
    # TODO: error handling
    if os.path.exists(fpath):
        settings.load(fpath)
    else:
        settings.save(fpath)

